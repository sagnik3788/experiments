"""
MTP (Multi-Token Prediction) / Speculative Decoding with vLLM.

Supports four speculative methods:
  1. ngram      — built-in lookup speculation (no extra model needed).
  2. draft_model— separate draft model (GGUF or safetensors).
  3. mtp         — self-MTP via the target model itself (weight-sharing).
  4. eagle       — EAGLE / EAGLE3 head speculation.

Usage:
    # Default (ngram, 5 spec tokens)
    python mtp/inference_mtp_vllm.py

    # Specific method
    python mtp/inference_mtp_vllm.py --method mtp --num-spec-tokens 5

    # GGUF FP16 as target
    python mtp/inference_mtp_vllm.py --model ../model-f16.gguf --method ngram

    # Draft model speculation with GGUF quantized draft
    python mtp/inference_mtp_vllm.py \
        --method draft_model \
        --draft-model ../model-f16-Q4_K_M.gguf \
        --num-spec-tokens 5

    # Compare all methods
    python mtp/inference_mtp_vllm.py --compare
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from typing import Any

# ── vLLM imports ──────────────────────────────────────────────────────────
import torch
from vllm import LLM, SamplingParams

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.environ.get(
    "MTP_MODEL_PATH",
    PROJECT_DIR,  # default: safetensors directory
)
GGUF_FP16 = os.path.join(PROJECT_DIR, "model-f16.gguf")
GGUF_Q8 = os.path.join(PROJECT_DIR, "model-f16-Q8_0.gguf")
GGUF_Q4 = os.path.join(PROJECT_DIR, "model-f16-Q4_K_M.gguf")

MAX_NEW_TOKENS = 128
WARMUP_TOKENS = 4

# ═══════════════════════════════════════════════════════════════════════════
#  Speculative Decoding Configs
# ═══════════════════════════════════════════════════════════════════════════

def make_spec_config(
    method: str = "ngram",
    num_spec_tokens: int = 5,
    draft_model: str | None = None,
    prompt_lookup_max: int = 5,
    prompt_lookup_min: int = 3,
    rejection_sample: str = "strict",
) -> dict[str, Any]:
    """Build a ``speculative_config`` dict for vLLM's ``SpeculativeConfig``.

    Parameters
    ----------
    method :
        One of ``"ngram"``, ``"draft_model"``, ``"mtp"``, ``"eagle"``.
    num_spec_tokens :
        Number of tokens to speculate ahead.
    draft_model :
        Path / name of the draft model (required for ``draft_model`` and
        ``eagle`` methods; ignored for ``ngram``).
    prompt_lookup_max, prompt_lookup_min :
        N-gram window size (only used when ``method="ngram"``).
    rejection_sample :
        Rejection sampling strategy.
    """
    cfg: dict[str, Any] = {
        "num_speculative_tokens": num_spec_tokens,
        "rejection_sample_method": rejection_sample,
    }

    if method == "ngram":
        cfg["model"] = "[ngram]"
        cfg["method"] = "ngram"
        cfg["prompt_lookup_min"] = prompt_lookup_min
        cfg["prompt_lookup_max"] = prompt_lookup_max
    elif method == "draft_model":
        if draft_model is None:
            raise ValueError("--draft-model is required for draft_model method")
        cfg["model"] = draft_model
        cfg["method"] = "draft_model"
    elif method == "mtp":
        # model=None → vLLM auto-resolves to target model (self-speculation)
        cfg["model"] = None
        cfg["method"] = "mtp"
    elif method == "eagle":
        if draft_model is None:
            raise ValueError("--draft-model is required for eagle method")
        cfg["model"] = draft_model
        cfg["method"] = "eagle"
    else:
        raise ValueError(f"Unknown speculative method: {method}")

    return cfg


# ═══════════════════════════════════════════════════════════════════════════
#  Benchmark runner
# ═══════════════════════════════════════════════════════════════════════════

@dataclasses.dataclass
class BenchResult:
    label: str
    num_output_tokens: int
    total_time: float
    ttfs: float
    generation_time: float
    tokens_per_second: float
    avg_decode_ms: float
    accepted_tokens: int | None = None
    draft_tokens: int | None = None

    @property
    def short(self) -> str:
        return (
            f"{self.label:<20s} "
            f"{self.tokens_per_second:>8.2f} tok/s  "
            f"{self.avg_decode_ms:>7.1f} ms/tok  "
            f"{self.total_time:>6.2f}s total"
        )


def run_bench(
    llm: LLM,
    prompt_text: str,
    sampling_params: SamplingParams,
    label: str = "spec",
) -> BenchResult:
    """Run one inference pass and return metrics."""
    torch.cuda.synchronize()
    start = time.time()

    outputs = llm.generate(prompt_text, sampling_params, use_tqdm=False)

    torch.cuda.synchronize()
    elapsed = time.time() - start

    out = outputs[0]
    n_tokens = len(out.outputs[0].token_ids)

    metrics = out.metrics
    if metrics and metrics.first_token_latency is not None:
        ttfs = metrics.first_token_latency
        if metrics.last_token_ts is not None and metrics.first_token_ts is not None:
            gen_time = metrics.last_token_ts - metrics.first_token_ts
        else:
            gen_time = elapsed - ttfs
    else:
        ttfs = elapsed
        gen_time = elapsed

    if n_tokens > 1:
        avg_decode = gen_time / (n_tokens - 1) * 1000
    else:
        avg_decode = 0.0
    tok_s = (n_tokens - 1) / gen_time if gen_time > 0 else 0.0

    # Try to extract acceptance statistics from engine metrics
    accepted = None
    draft_total = None
    if metrics:
        accepted = getattr(metrics, "speculative_accepted_tokens", None)
        draft_total = getattr(metrics, "speculative_draft_tokens", None)

    return BenchResult(
        label=label,
        num_output_tokens=n_tokens,
        total_time=elapsed,
        ttfs=ttfs,
        generation_time=gen_time,
        tokens_per_second=tok_s,
        avg_decode_ms=avg_decode,
        accepted_tokens=accepted,
        draft_tokens=draft_total,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════

def resolve_model_path(path: str) -> str:
    """Resolve *path* to an absolute path; if it is a directory look for
    ``model.safetensors`` or ``config.json`` inside."""
    p = os.path.abspath(os.path.expanduser(path))
    if os.path.isfile(p):
        return p
    if os.path.isdir(p):
        # check it looks like a model directory
        if os.path.isfile(os.path.join(p, "config.json")):
            return p
        raise FileNotFoundError(
            f"Directory {p} exists but does not contain config.json"
        )
    # could be a HuggingFace repo id — return as-is
    return path


def build_llm(
    model_path: str,
    speculative_config: dict[str, Any] | None,
    enforce_eager: bool = True,
    gpu_memory_utilization: float = 0.95,
    max_model_len: int = 256,
    max_num_seqs: int = 1,
    num_gpu_blocks_override: int | None = 64,
) -> LLM:
    """Create a vLLM ``LLM`` instance.

    If *model_path* ends with ``.gguf``, vLLM automatically uses its
    GGUF loader — no special flags needed.
    """
    kwargs: dict[str, Any] = dict(
        model=model_path,
        tensor_parallel_size=1,
        dtype="float16" if not model_path.endswith(".gguf") else "auto",
        gpu_memory_utilization=gpu_memory_utilization,
        max_model_len=max_model_len,
        enforce_eager=enforce_eager,
        max_num_seqs=max_num_seqs,
        speculative_config=speculative_config,
        disable_log_stats=True,
    )
    if num_gpu_blocks_override is not None:
        kwargs["num_gpu_blocks_override"] = num_gpu_blocks_override

    print(f"  Model:     {model_path}")
    print(f"  Method:    {speculative_config.get('method', 'none') if speculative_config else 'none'}")
    if speculative_config:
        print(f"  Spec tokens: {speculative_config.get('num_speculative_tokens', '?')}")
    print()

    return LLM(**kwargs)


def make_prompt() -> str:
    """Return a moderately long prompt for benchmarking."""
    return """SYSTEM: You are Qwen2.5-1.5B, an expert AI assistant. Answer concisely and accurately.

USER: Explain the following topics in a few sentences each:

1. What is speculative decoding in large language models and how does it work?
2. What is Multi-Token Prediction (MTP) and how does it differ from standard next-token prediction?
3. How does vLLM implement speculative decoding?

ASSISTANT:"""


def run_single(
    model_path: str,
    method: str,
    num_spec_tokens: int,
    draft_model: str | None,
    prompt_text: str,
) -> BenchResult:
    """Build engine, warm up, benchmark one config."""
    spec_cfg = make_spec_config(
        method=method,
        num_spec_tokens=num_spec_tokens,
        draft_model=draft_model,
    )
    llm = build_llm(model_path, spec_cfg)

    tokenizer = llm.get_tokenizer()
    sampling_params = SamplingParams(
        max_tokens=MAX_NEW_TOKENS,
        temperature=0.7,
        top_p=0.8,
        stop_token_ids=[tokenizer.eos_token_id] if tokenizer.eos_token_id is not None else None,
    )

    # Warm up
    _ = llm.generate(
        "warm",
        SamplingParams(max_tokens=WARMUP_TOKENS),
        use_tqdm=False,
    )
    torch.cuda.synchronize()

    label = f"{method}({num_spec_tokens})"
    result = run_bench(llm, prompt_text, sampling_params, label=label)
    del llm
    torch.cuda.synchronize()
    return result


def run_compare(
    model_path: str,
    methods: list[str],
    num_spec_tokens: int,
    draft_model: str | None,
    prompt_text: str,
) -> list[BenchResult]:
    """Benchmark multiple speculative methods and a no-spec baseline."""
    results: list[BenchResult] = []

    # Baseline: no speculation
    print("\n── Baseline (no speculation) ──")
    llm = build_llm(model_path, speculative_config=None)
    tokenizer = llm.get_tokenizer()
    sp = SamplingParams(
        max_tokens=MAX_NEW_TOKENS,
        temperature=0.7,
        top_p=0.8,
        stop_token_ids=[tokenizer.eos_token_id] if tokenizer.eos_token_id is not None else None,
    )
    _ = llm.generate("warm", SamplingParams(max_tokens=WARMUP_TOKENS), use_tqdm=False)
    torch.cuda.synchronize()
    results.append(run_bench(llm, prompt_text, sp, label="none (baseline)"))
    del llm
    torch.cuda.synchronize()

    for method in methods:
        print(f"\n── Method: {method} ({num_spec_tokens} spec tokens) ──")
        try:
            r = run_single(model_path, method, num_spec_tokens, draft_model, prompt_text)
            results.append(r)
        except Exception as e:
            print(f"  ❌ {method} failed: {e}")
            results.append(
                BenchResult(
                    label=f"{method}(ERR)",
                    num_output_tokens=0,
                    total_time=0,
                    ttfs=0,
                    generation_time=0,
                    tokens_per_second=0,
                    avg_decode_ms=0,
                )
            )

    return results


def print_comparison(results: list[BenchResult]) -> None:
    """Pretty-print a comparison table."""
    print()
    print("═" * 80)
    print("  MTP / SPECULATIVE DECODING — COMPARISON")
    print("═" * 80)
    print(
        f"  {'Method':<22s} {'tok/s':>8s}  {'ms/tok':>7s}  "
        f"{'Total':>7s}  {'TTFS':>6s}  {'GenTok':>6s}"
    )
    print("  " + "─" * 62)
    for r in results:
        tok_s = f"{r.tokens_per_second:.2f}" if r.tokens_per_second > 0 else "ERR"
        ms = f"{r.avg_decode_ms:.1f}" if r.avg_decode_ms > 0 else "ERR"
        total = f"{r.total_time:.2f}s" if r.total_time > 0 else "ERR"
        ttfs = f"{r.ttfs:.3f}s" if r.ttfs > 0 else "ERR"
        gen = str(r.num_output_tokens)
        print(f"  {r.label:<22s} {tok_s:>8s}  {ms:>7s}  {total:>7s}  {ttfs:>6s}  {gen:>6s}")
    print()

    # Speedup vs baseline
    if len(results) >= 2:
        base = results[0].tokens_per_second
        if base > 0:
            print("  Speedup vs baseline:")
            for r in results[1:]:
                if r.tokens_per_second > 0:
                    ratio = r.tokens_per_second / base
                    print(f"    {r.label:<22s}  {ratio:.2f}×")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="MTP / Speculative Decoding with vLLM (Qwen2.5-1.5B)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--model",
        default=MODEL_PATH,
        help=f"Model path (safetensors dir or .gguf file). Default: {MODEL_PATH}",
    )
    parser.add_argument(
        "--method",
        choices=["ngram", "draft_model", "mtp", "eagle"],
        default="ngram",
        help="Speculative method (default: ngram)",
    )
    parser.add_argument(
        "--num-spec-tokens",
        type=int,
        default=5,
        help="Number of speculative tokens (default: 5)",
    )
    parser.add_argument(
        "--draft-model",
        default=None,
        help="Draft model path (required for draft_model and eagle methods)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Benchmark all methods and print comparison table",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=["ngram", "mtp", "draft_model", "eagle"],
        help="Methods to compare (default: ngram mtp draft_model eagle)",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Custom prompt text (will be tokenised as-is)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Save results as JSON to this path",
    )
    parser.add_argument(
        "--gguf-fp16",
        action="store_true",
        help="Shortcut: use ../model-f16.gguf as model",
    )
    parser.add_argument(
        "--gguf-q8",
        action="store_true",
        help="Shortcut: use ../model-f16-Q8_0.gguf as model",
    )
    parser.add_argument(
        "--gguf-q4",
        action="store_true",
        help="Shortcut: use ../model-f16-Q4_K_M.gguf as model",
    )
    args = parser.parse_args()

    # ── Resolve model path ──────────────────────────────────────────────
    if args.gguf_fp16:
        args.model = GGUF_FP16
    elif args.gguf_q8:
        args.model = GGUF_Q8
    elif args.gguf_q4:
        args.model = GGUF_Q4

    try:
        args.model = resolve_model_path(args.model)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # ── Prompt ──────────────────────────────────────────────────────────
    prompt_text = args.prompt or make_prompt()
    print(f"Prompt length: ~{len(prompt_text.split())} words")

    # ── Run ─────────────────────────────────────────────────────────────
    if args.compare:
        results = run_compare(
            model_path=args.model,
            methods=args.methods,
            num_spec_tokens=args.num_spec_tokens,
            draft_model=args.draft_model,
            prompt_text=prompt_text,
        )
        print_comparison(results)
    else:
        result = run_single(
            model_path=args.model,
            method=args.method,
            num_spec_tokens=args.num_spec_tokens,
            draft_model=args.draft_model,
            prompt_text=prompt_text,
        )
        print()
        print(f"  Generated text:")
        print(f"  {'─' * 60}")
        # Re-run just to show text (cheap since model is discarded)
        print(f"  {'─' * 60}")
        print()
        print(f"  {result.short}")

    # ── Save ────────────────────────────────────────────────────────────
    if args.output:
        data = [
            {
                "label": r.label,
                "tokens_per_second": r.tokens_per_second,
                "avg_decode_ms": r.avg_decode_ms,
                "total_time": r.total_time,
                "ttfs": r.ttfs,
                "num_output_tokens": r.num_output_tokens,
            }
            for r in (results if args.compare else [result])
        ]
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\n  Results saved to {args.output}")


if __name__ == "__main__":
    main()
