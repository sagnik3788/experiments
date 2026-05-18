#!/usr/bin/env bash
#
# Run the GGUF Normal vs MTP comparison and generate a video.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RESULTS_JSON="$SCRIPT_DIR/bench_results.json"
VIDEO_OUT="$SCRIPT_DIR/mtp_comparison.mp4"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  GGUF FP16 vs MTP — Benchmark + Video Generator            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Run benchmark ──────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 1: Running benchmark (Normal vs MTP)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Model       : model-f16-Q4_K_M.gguf"
echo "  Output JSON : $RESULTS_JSON"
echo ""

cd "$PROJECT_DIR"

python3.12 -m mtp.compare_normal_vs_mtp \
    --model "$PROJECT_DIR/model-f16-Q4_K_M.gguf" \
    --output "$RESULTS_JSON" \
    --method ngram \
    --num-spec-tokens 5

BENCH_EXIT=$?
echo ""
if [ $BENCH_EXIT -ne 0 ]; then
    echo "  ⚠ Benchmark exited with code $BENCH_EXIT"
    echo "  Using demo placeholders for video generation"
fi

# ── Step 2: Generate video ─────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 2: Generating comparison video..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -f "$RESULTS_JSON" ]; then
    python3.12 -m mtp.make_video \
        --input "$RESULTS_JSON" \
        --output "$VIDEO_OUT" \
        --fps 24
else
    echo "  ⚠ No results JSON found, generating demo video"
    python3.12 -m mtp.make_video \
        --output "$VIDEO_OUT" \
        --fps 24
fi

VIDEO_EXIT=$?

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "$VIDEO_OUT" ]; then
    SIZE_MB=$(du -h "$VIDEO_OUT" | cut -f1)
    echo ""
    echo "  ✅ DONE!"
    echo "  📊 Results : $RESULTS_JSON"
    echo "  📹 Video   : $VIDEO_OUT  ($SIZE_MB)"
    echo ""
else
    echo "  ❌ Video creation failed"
fi
