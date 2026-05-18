#!/usr/bin/env python3
"""
Qwen2.5-1.5B-Instruct Quantization Script using llama.cpp
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# lamma.cpp build location
LLAMA_CPP_ROOT = Path(__file__).resolve().parent.parent / "llama.cpp"
QUANTIZE_BIN = LLAMA_CPP_ROOT / "build" / "bin" / "llama-quantize"


# check the binary exist or not
def check_binary():
    """Verify the llama-quantize binary exists."""
    if not QUANTIZE_BIN.exists():
        print(f"Error: llama-quantize binary not found at {QUANTIZE_BIN}")
        print("Build llama.cpp first: cmake -B build && cmake --build build")
        sys.exit(1)


def quantize_model(
    input_path: str, output_path: str, quant_type: str, n_threads: int = 4
):
    """Run llama-quantize on a GGUF model."""
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)

    if not os.path.exists(input_path):
        print(f"Error: Input model not found: {input_path}")
        sys.exit(1)

    cmd = [
        str(QUANTIZE_BIN),
        input_path,
        output_path,
        quant_type,
        str(n_threads),
    ]

    print(f"\n{'=' * 60}")
    print(f"Quantizing: {os.path.basename(input_path)}")
    print(f"  Type   : {quant_type}")
    print(f"  Output : {os.path.basename(output_path)}")
    print(f"  Threads: {n_threads}")
    print(f"{'=' * 60}\n")

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        print(f"\nError: Quantization failed with return code {result.returncode}")
        sys.exit(1)

    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"\nOutput: {output_path} ({size_mb:.1f} MB)")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Quantize Qwen2.5-1.5B-Instruct using llama.cpp",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # INT8  only
  python Quant.py --model qwen2.5-1.5b-instruct-f16.gguf --int8

  # 4-bit  only
  python Quant.py --model qwen2.5-1.5b-instruct-f16.gguf --q4

  # Both INT8 and 4-bit
  python Quant.py --model qwen2.5-1.5b-instruct-f16.gguf --int8 --q4

  # Custom output directory and threads
  python Quant.py --model qwen2.5-1.5b-instruct-f16.gguf --int8 --q4 --output-dir ./quantized --threads 8
        """,
    )

    parser.add_argument(
        "--model",
        required=True,
        help="Path to input GGUF model (F16 or F32 recommended)",
    )
    parser.add_argument(
        "--int8",
        action="store_true",
        help="Apply INT8 quantization (Q8_0)",
    )
    parser.add_argument(
        "--q4",
        action="store_true",
        help="Apply 4-bit quantization (Q4_K_M)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: same as input model)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of threads (default: 4)",
    )

    args = parser.parse_args()

    if not args.int8 and not args.q4:
        parser.error("At least one of --int8 or --q4 is required")

    check_binary()

    model_path = args.model
    model_name = Path(model_path).stem
    output_dir = args.output_dir or str(Path(model_path).parent)
    os.makedirs(output_dir, exist_ok=True)

    results = []

    if args.int8:
        output = os.path.join(output_dir, f"{model_name}-Q8_0.gguf")
        quantize_model(model_path, output, "Q8_0", args.threads)
        results.append(output)

    if args.q4:
        output = os.path.join(output_dir, f"{model_name}-Q4_K_M.gguf")
        quantize_model(model_path, output, "Q4_K_M", args.threads)
        results.append(output)

    print(f"\n{'=' * 60}")
    print("Quantization complete!")
    for r in results:
        print(f"  -> {r}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
