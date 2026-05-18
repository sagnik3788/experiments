"""
Pre-configured speculative decoding configs for Qwen2.5-1.5B.

Each config is a dict that maps to vLLM's ``SpeculativeConfig`` fields,
passed via ``LLM(..., speculative_config={...})``.

Methods available:
  - ngram:       Built-in lookup-based speculation (no extra model).
  - draft_model: Uses a separate draft model (GGUF or safetensors).
  - mtp:         Self-MTP speculation via the target model itself.
  - eagle:       EAGLE / EAGLE3 head speculation.
"""

# ---------------------------------------------------------------------------
# N-gram speculation (no extra model required)
# ---------------------------------------------------------------------------
NGRAM_SPEC = dict(
    model="[ngram]",
    num_speculative_tokens=5,
    method="ngram",
    prompt_lookup_min=3,
    prompt_lookup_max=5,
    rejection_sample_method="strict",
)

# NOTE: With FP16 model (2.95 GB) on a 4 GB GPU, speculative decoding
# may OOM because the rejection sampler needs ~20-50 MiB extra memory.
# Use the quantized Q4_K_M model (940 MB) for speculative decoding runs.
# Q8_0 (1.57 GB) should also work.
#
# The normal (non-speculative) run works with any model.
# ---------------------------------------------------------------------------

NGRAM_AGGRESSIVE = dict(
    model="[ngram]",
    num_speculative_tokens=10,
    method="ngram",
    prompt_lookup_min=5,
    prompt_lookup_max=10,
    rejection_sample_method="probabilistic",
)

# ---------------------------------------------------------------------------
# Draft-model speculation — point `model` at a separate draft model path.
# The draft should be a smaller / faster model with the same tokenizer.
# ---------------------------------------------------------------------------
DRAFT_MODEL_SPEC = dict(
    # model="/path/to/draft.gguf",     # <-- fill in your draft model
    num_speculative_tokens=5,
    method="draft_model",
    rejection_sample_method="strict",
)

# ---------------------------------------------------------------------------
# Self-speculation via MTP method
# Uses the same model for both draft and target — vLLM shares the weights
# and runs a truncated forward pass for the draft.
# ---------------------------------------------------------------------------
MTP_SELF_SPEC = dict(
    # model=None  → auto-resolved to target model by vLLM
    num_speculative_tokens=5,
    method="mtp",
    rejection_sample_method="strict",
)

# ---------------------------------------------------------------------------
# EAGLE speculation — requires a pre-trained EAGLE head module.
# ---------------------------------------------------------------------------
EAGLE_SPEC = dict(
    # model="/path/to/eagle-head",     # <-- fill in your EAGLE head path
    num_speculative_tokens=5,
    method="eagle",
    rejection_sample_method="probabilistic",
)

# ---------------------------------------------------------------------------
# Map for convenient lookup
# ---------------------------------------------------------------------------
CONFIGS = {
    "ngram": NGRAM_SPEC,
    "ngram_aggressive": NGRAM_AGGRESSIVE,
    "draft_model": DRAFT_MODEL_SPEC,
    "mtp": MTP_SELF_SPEC,
    "eagle": EAGLE_SPEC,
}
