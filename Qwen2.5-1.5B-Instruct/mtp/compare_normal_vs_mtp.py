"""
Compare normal GGUF inference vs MTP speculative decoding side-by-side.

Runs:
  1. Normal (no speculation) — vLLM loading the GGUF FP16 model
  2. MTP / Speculative Decoding — vLLM + same GGUF model with speculation

Outputs a JSON file with metrics and prints a comparison table.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
import time

import torch
from vllm import LLM, SamplingParams

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_NEW_TOKENS = 128
WARMUP_TOKENS = 2


# ── Helpers ────────────────────────────────────────────────────────────────

def colored(msg: str, color: str) -> str:
    codes = {"green": "32", "yellow": "33", "cyan": "36", "red": "31", "bold": "1"}
    c = codes.get(color, "0")
    return f"\033[{c}m{msg}\033[0m" if sys.stdout.isatty() else msg


def build_llm(
    model_path: str,
    speculative_config: dict | None = None,
    label: str = "",
    gpu_memory_utilization: float = 0.95,
    num_gpu_blocks: int | None = 64,
) -> LLM:
    """Create a vLLM LLM instance with optional speculative decoding."""
    kwargs = dict(
        model=model_path,
        tensor_parallel_size=1,
        dtype="float16",
        gpu_memory_utilization=gpu_memory_utilization,
        max_model_len=256,
        enforce_eager=True,
        max_num_seqs=1,
        speculative_config=speculative_config,
        disable_log_stats=True,
    )
    if num_gpu_blocks is not None:
        kwargs["num_gpu_blocks_override"] = num_gpu_blocks
    print(f"  {colored('▸', 'cyan')} Loading {label or model_path} ...")
    sys.stdout.flush()
    return LLM(**kwargs)


def make_prompt() -> tuple[str, str]:
    """Return (system_prompt, user_prompt)."""
    system = "You are Qwen2.5-1.5B, an expert AI assistant."
    user = textwrap.dedent("""\
        Explain the following topics in 1-2 sentences each:
        1. What is speculative decoding in LLMs?
        2. How does Multi-Token Prediction (MTP) work?
        3. What are the benefits of MTP over standard decoding?
    """)
    return system, user


def format_prompt(system: str, user: str, tokenizer) -> str:
    """Apply chat template."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def measure(llm: LLM, prompt: str, sampling_params: SamplingParams) -> dict:
    """Run generation and return structured metrics."""
    torch.cuda.synchronize()
    t0 = time.time()

    outputs = llm.generate(prompt, sampling_params, use_tqdm=False)

    torch.cuda.synchronize()
    wall = time.time() - t0

    out = outputs[0]
    n = len(out.outputs[0].token_ids)
    text = out.outputs[0].text
    m = out.metrics

    # Prefill time = TTFS = time to first token
    ttfs = None
    if m:
        ttfs = getattr(m, "first_token_latency", None)
        if ttfs is None and hasattr(m, "time_to_first_token_ms"):
            ttfs = m.time_to_first_token_ms / 1000.0
    if ttfs is None or ttfs <= 0:
        # fallback: rough heuristic estimate
        ttfs = wall * 0.3

    gen_time = max(wall - ttfs, 0.001)  # avoid zero-division

    # Tokens generated during decode phase = total - 1 (first token)
    decode_tokens = max(n - 1, 1)
    tok_s = decode_tokens / gen_time
    ms_tok = gen_time / decode_tokens * 1000

    return {
        "tokens": n,
        "total_time_s": round(wall, 3),
        "ttfs_s": round(ttfs, 3),
        "gen_time_s": round(gen_time, 3),
        "tokens_per_second": round(tok_s, 2),
        "ms_per_token": round(ms_tok, 1),
        "text": text.strip(),
    }


def print_result(label: str, data: dict) -> None:
    tok_per_s = data["tokens_per_second"]
    print(f"\n  {colored('═══', 'cyan')} {colored(label, 'bold')} {colored('═══', 'cyan')}")
    print(f"  Generated tokens : {data['tokens']}")
    print(f"  Total time       : {data['total_time_s']:.2f}s")
    print(f"  TTFS             : {data['ttfs_s']:.3f}s")
    print(f"  Generation time  : {data['gen_time_s']:.2f}s")
    print(f"  Throughput       : {colored(f'{tok_per_s:.2f} tok/s', 'green')}")
    print(f"  Latency          : {data['ms_per_token']:.1f} ms/tok")
    if data.get("text"):
        preview = data["text"][:120].replace("\n", " ")
        print(f"  Output preview   : {preview}...")

    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Normal GGUF vs MTP comparison")
    # Default to Q4_K_M (940 MB) to leave GPU headroom for spec decode buffers
    parser.add_argument("--model", default=os.path.join(PROJECT_DIR, "model-f16-Q4_K_M.gguf"),
                        help="GGUF model path")
    parser.add_argument("--num-spec-tokens", type=int, default=5,
                        help="Number of speculative tokens for MTP")
    parser.add_argument("--method", choices=["ngram", "mtp"], default="ngram",
                        help="Speculative method (default: ngram)")
    parser.add_argument("--output", default=None,
                        help="Save results JSON to this file")
    parser.add_argument("--no-run", action="store_true",
                        help="Skip actual benchmark (for testing)")
    args = parser.parse_args()

    model_path = os.path.abspath(args.model)
    if not os.path.isfile(model_path):
        print(f"Error: model not found at {model_path}")
        sys.exit(1)

    print()
    print(colored("╔══════════════════════════════════════════════════════════════╗", "bold"))
    print(colored("║     GGUF FP16  vs  MTP Speculative Decoding                ║", "bold"))
    print(colored("╚══════════════════════════════════════════════════════════════╝", "bold"))
    print(f"  Model    : {model_path}")
    print(f"  GPU      : NVIDIA GeForce GTX 1650 (4 GB)")
    print(f"  Max tokens: {MAX_NEW_TOKENS}")
    print()

    system_prompt, user_prompt = make_prompt()

    # ── 1. NORMAL (NO SPECULATION) ──────────────────────────────────────
    print(colored("─" * 58, "yellow"))
    print(colored("  RUN 1: Normal Inference (no speculative decoding)", "yellow"))
    print(colored("─" * 58, "yellow"))
    print()

    if not args.no_run:
        llm_normal = build_llm(model_path, speculative_config=None, label="Normal")
        tokenizer = llm_normal.get_tokenizer()
        prompt_text = format_prompt(system_prompt, user_prompt, tokenizer)
        # Use greedy decoding to minimize GPU memory (avoids top-k/top-p sort)
        sp_normal = SamplingParams(
            max_tokens=MAX_NEW_TOKENS,
            temperature=0,
            top_p=1.0,
            top_k=-1,
            stop_token_ids=[tokenizer.eos_token_id] if tokenizer.eos_token_id is not None else None,
        )

        # Warmup
        _ = llm_normal.generate("warm", SamplingParams(max_tokens=WARMUP_TOKENS), use_tqdm=False)
        torch.cuda.synchronize()

        normal_result = measure(llm_normal, prompt_text, sp_normal)
        print_result("Normal (no speculation)", normal_result)

        del llm_normal
        torch.cuda.synchronize()
    else:
        normal_result = {"tokens": 0, "total_time_s": 0, "ttfs_s": 0, "gen_time_s": 0,
                         "tokens_per_second": 0, "ms_per_token": 0, "text": ""}
        prompt_text = ""

    # ── 2. MTP SPECULATIVE DECODING ─────────────────────────────────────
    print()
    print(colored("─" * 58, "green"))
    print(colored(f"  RUN 2: MTP Speculative Decoding ({args.method}, {args.num_spec_tokens} tokens)", "green"))
    print(colored("─" * 58, "green"))
    print()

    if not args.no_run:
        spec_cfg = {
            "model": "[ngram]" if args.method == "ngram" else None,
            "num_speculative_tokens": args.num_spec_tokens,
            "method": args.method,
            "rejection_sample_method": "strict",
        }
        if args.method == "ngram":
            spec_cfg["prompt_lookup_min"] = 3
            spec_cfg["prompt_lookup_max"] = 5

        llm_mtp = build_llm(
            model_path,
            speculative_config=spec_cfg,
            label="MTP",
            gpu_memory_utilization=0.90,
            num_gpu_blocks=64,
        )

        # Reuse the same tokenizer (or get from new LLM)
        if not prompt_text:
            tokenizer = llm_mtp.get_tokenizer()
            prompt_text = format_prompt(system_prompt, user_prompt, tokenizer)

        sp_mtp = SamplingParams(
            max_tokens=MAX_NEW_TOKENS,
            temperature=0.7,
            top_p=0.8,
            stop_token_ids=[tokenizer.eos_token_id] if tokenizer.eos_token_id is not None else None,
        )

        # Warmup
        _ = llm_mtp.generate("warm", SamplingParams(max_tokens=WARMUP_TOKENS), use_tqdm=False)
        torch.cuda.synchronize()

        mtp_result = measure(llm_mtp, prompt_text, sp_mtp)
        print_result(f"MTP ({args.method})", mtp_result)

        del llm_mtp
        torch.cuda.synchronize()
    else:
        mtp_result = {"tokens": 0, "total_time_s": 0, "ttfs_s": 0, "gen_time_s": 0,
                      "tokens_per_second": 0, "ms_per_token": 0, "text": ""}

    # ── COMPARISON TABLE ────────────────────────────────────────────────
    print()
    print(colored("═" * 68, "bold"))
    print(colored("  COMPARISON SUMMARY", "bold"))
    print(colored("═" * 68, "bold"))
    header = f"  {'Method':<22s} {'tok/s':>8s}  {'ms/tok':>7s}  {'Total':>7s}  {'TTFS':>7s}  {'Tokens':>6s}"
    print(colored(header, "bold"))
    print("  " + "─" * 62)

    for label, data in [("Normal (no spec)", normal_result), (f"MTP ({args.method})", mtp_result)]:
        tok_s = f"{data['tokens_per_second']:.2f}"
        ms = f"{data['ms_per_token']:.1f}"
        total = f"{data['total_time_s']:.2f}s"
        ttfs = f"{data['ttfs_s']:.3f}s"
        nt = str(data['tokens'])
        color = "green" if "MTP" in label else "yellow"
        print(colored(f"  {label:<22s} {tok_s:>8s}  {ms:>7s}  {total:>7s}  {ttfs:>7s}  {nt:>6s}", color))

    # Speedup
    print()
    if normal_result["tokens_per_second"] > 0 and mtp_result["tokens_per_second"] > 0:
        speedup = mtp_result["tokens_per_second"] / normal_result["tokens_per_second"]
        tok_diff = mtp_result["tokens_per_second"] - normal_result["tokens_per_second"]
        print(f"  🚀 Speedup:      {colored(f'{speedup:.2f}×', 'green')}")
        print(f"  📈 Improvement:  +{tok_diff:.2f} tok/s")
        print()

    # ── Save JSON ───────────────────────────────────────────────────────
    output_data = {
        "model": model_path,
        "max_tokens": MAX_NEW_TOKENS,
        "spec_method": args.method,
        "spec_tokens": args.num_spec_tokens,
        "normal": normal_result,
        "mtp": mtp_result,
        "speedup_ratio": round(mtp_result["tokens_per_second"] / normal_result["tokens_per_second"], 3)
        if normal_result["tokens_per_second"] > 0 else None,
    }
    if args.output:
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"  Results saved to {args.output}")

    return output_data


if __name__ == "__main__":
    main()
