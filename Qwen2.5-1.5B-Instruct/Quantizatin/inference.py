#!/usr/bin/env python3
"""
Inference comparison script for Qwen2.5-1.5B quantized models.
Compares outputs from F16, Q8_0 (INT8), and Q4_K_M (INT4) versions.
Uses llama.cpp CLI for inference.
"""

import subprocess
import os

MODEL_DIR = "/home/sagnik/experiments/Qwen2.5-1.5B-Instruct"
MODELS = [
    "model-f16.gguf",
    "model-f16-Q8_0.gguf",
    "model-f16-Q4_K_M.gguf",
]

PROMPT = """SYSTEM:
You are being evaluated on reasoning, coding, mathematics, instruction following, and concise explanation.
Answer clearly and directly.

════════════════════════════════════
SECTION 1 — REASONING
════════════════════════════════════

Three developers — Alex, Blake, and Casey — each use one language:
Rust, Go, or Python.

Rules:

1. Alex does not use Python.
2. The Rust developer works with Blake.
3. Casey is not the Go developer.

Determine each person's language.

════════════════════════════════════
SECTION 2 — MATHEMATICS
════════════════════════════════════

A) Solve:
f(x) = (2x² + 3x - 5) / (x - 1)

Find:

* quotient
* remainder
* asymptote

B) A geometric sequence has:
a₁ = 81
r = 1/3

Find:

* first 5 terms
* sum to infinity

════════════════════════════════════
SECTION 3 — CODING
════════════════════════════════════

A) Python

Write a function that:

* accepts a list of integers
* returns prime numbers only
* includes type hints

B) JavaScript

Fix this code:

async function getData() {
const res = fetch('/api/data')
const data = res.json()
return data
}

════════════════════════════════════
SECTION 4 — SCIENCE
════════════════════════════════════

Explain how neural networks learn in:

1. One sentence
2. One paragraph for beginners

════════════════════════════════════
SECTION 5 — JSON OUTPUT
════════════════════════════════════

Return valid JSON representing:

* a book
* title
* author
* year
* genres (array)
* rating

════════════════════════════════════
SECTION 6 — SHORT CREATIVE TASK
════════════════════════════════════

Write a story under 120 words about:

* rain
* an abandoned station
* a forgotten message

════════════════════════════════════
SECTION 7 — SELF CHECK
════════════════════════════════════

State:

* which section was hardest
* whether your JSON is valid
* whether you followed all instructions

---"""


LLAMA_CLI = "/home/sagnik/experiments/llama.cpp/build/bin/llama-completion"
N_TOKENS = 800  # Sufficient for concise multi-section response


def run_inference(model_name: str) -> tuple[str, dict]:
    """Run inference on a model and return the generated text and metrics."""
    model_path = os.path.join(MODEL_DIR, model_name)

    cmd = [
        str(LLAMA_CLI),
        "-m", str(model_path),
        "-p", PROMPT,
        "-n", str(N_TOKENS),
        "-no-cnv",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
        cwd="/tmp"
    )

    stdout = result.stdout
    stderr = result.stderr
    output = stdout + "\n" + stderr

    # Parse metrics from output
    metrics = {}
    for line in output.split("\n"):
        line_lower = line.lower()
        if "prompt eval time" in line_lower:
            metrics["prompt_eval_time"] = line.strip()
        elif "eval time" in line_lower and "prompt" not in line_lower:
            metrics["eval_time"] = line.strip()
        elif "tokens per second" in line_lower:
            metrics["tokens_per_sec"] = line.strip()
        elif "total time" in line_lower:
            metrics["total_time"] = line.strip()

    # Response is the FIRST lines of output - before metadata lines start
    response_lines = []
    for line in stdout.split("\n"):
        line = line.strip()
        if not line:
            continue
        if any(line.startswith(p) for p in ["main:", "common:", "llama:", "load:", "print_info",
                                              "memory", "sampler", "interactive", "chat", "seed",
                                              "system_info", "generate:", "sched"]):
            break
        response_lines.append(line)

    response = "\n".join(response_lines[:200])
    return response, metrics


def main():
    print("=" * 80)
    print("Qwen2.5-1.5B — COMPREHENSIVE QUALITY EVALUATION")
    print("=" * 80)
    print()
    print(f"Prompt: Multi-section evaluation covering reasoning, math, coding, science,")
    print(f"        creative writing, analysis, JSON output, and self-reflection")
    print(f"Max tokens per response: {N_TOKENS}")
    print()

    results = {}

    for model in MODELS:
        print(f"\n{'='*80}")
        print(f"Model: {model}")
        print("=" * 80)

        try:
            response, metrics = run_inference(model)
            results[model] = {"response": response, "metrics": metrics}

            print(f"\n--- RESPONSE ---")
            print(response)
            if metrics:
                print(f"\n--- METRICS ---")
                for v in metrics.values():
                    print(f"  {v}")
        except Exception as e:
            print(f"Error: {e}")
            results[model] = {"response": "", "metrics": {}}

        print()

    # Summary table
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\n{'Model':<25} {'Size':<10} {'Type':<15} {'Eval Time':<15} {'Speed'}")
    print("-" * 80)
    for model in MODELS:
        model_path = os.path.join(MODEL_DIR, model)
        if os.path.exists(model_path):
            size_mb = os.path.getsize(model_path) / (1024 * 1024)
            if "Q8_0" in model:
                qtype = "INT8 (Q8_0)"
            elif "Q4_K_M" in model:
                qtype = "INT4 (Q4_K_M)"
            else:
                qtype = "FP16 (F16)"

            metrics = results.get(model, {}).get("metrics", {})
            eval_time = "N/A"
            speed = "N/A"
            if metrics:
                for line in metrics.values():
                    if "eval time" in line.lower():
                        parts = line.split()
                        for i, p in enumerate(parts):
                            if "ms" in p.lower():
                                try:
                                    eval_time = f"{float(parts[i-1]):.0f}ms"
                                except:
                                    pass
                    elif "tokens per second" in line.lower():
                        parts = line.split()
                        for p in parts:
                            if p.replace('.', '').isdigit():
                                speed = f"{p} tok/s"
                                break

            print(f"{model:<25} {size_mb:>7.1f} MB  {qtype:<15} {eval_time:<15} {speed}")


if __name__ == "__main__":
    main()