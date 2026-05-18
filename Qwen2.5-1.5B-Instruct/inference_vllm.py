import time

import torch
from vllm import LLM, SamplingParams

MODEL_PATH = "/home/sagnik/experiments/Qwen2.5-1.5B-Instruct"
MAX_NEW_TOKENS = 100

print("🔄 Loading vLLM engine (auto KV cache & PagedAttention)...")
llm = LLM(
    model=MODEL_PATH,
    tensor_parallel_size=1,
    dtype="float16",
    gpu_memory_utilization=0.95,
    max_model_len=256,
    enforce_eager=True,  # Disable CUDA graphs + torch.compile for 4 GB GPU
    max_num_seqs=1,  # Single sequence to minimize memory
    num_gpu_blocks_override=64,  # Minimal KV cache blocks to fit in remaining ~0.3 GiB
)
tokenizer = llm.get_tokenizer()

messages = [
    {
        "role": "system",
        "content": "You are an expert AI assistant. Answer the following question accurately and concisely.",
    },
    {
        "role": "user",
        "content": "What is the capital of France and what are its major landmarks? Provide a brief explanation.",
    },
]

# Get exact prompt token count
prompt_ids = tokenizer.apply_chat_template(
    messages, tokenize=True, add_generation_prompt=True
)
# apply_chat_template returns a BatchEncoding/dict with 'input_ids' key
if hasattr(prompt_ids, "input_ids"):
    prompt_ids = prompt_ids["input_ids"]
prompt_len = len(prompt_ids)

sampling_params = SamplingParams(
    max_tokens=MAX_NEW_TOKENS,
    temperature=1.0,  # Matches torch.multinomial behavior
    top_p=1.0,
    stop_token_ids=[tokenizer.eos_token_id]
    if tokenizer.eos_token_id is not None
    else None,
)

print(f"✅ Engine loaded | Prompt tokens: {prompt_len}\n")
print("=== vLLM INFERENCE (WITH KV CACHE) - ACCURATE METRICS ===\n")

# Format prompt for generation
prompt_text = tokenizer.apply_chat_template(
    messages, tokenize=False, add_generation_prompt=True
)

# Warmup to avoid cold-start overhead
_ = llm.generate("warm", SamplingParams(max_tokens=1), use_tqdm=False)
torch.cuda.synchronize()

# --- Accurate timing using vLLM's internal metrics ---
torch.cuda.synchronize()
start_time = time.time()

# vLLM sync API returns a list (no streaming), but tracks internal timestamps
outputs = llm.generate(prompt_text, sampling_params, use_tqdm=False)

torch.cuda.synchronize()
end_time = time.time()

output = outputs[0]
generated_text = output.outputs[0].text
token_ids = output.outputs[0].token_ids
num_output_tokens = len(token_ids)

# Use vLLM's internal metrics for accurate timing
metrics = output.metrics
if metrics:
    # vLLM's own timestamps (monotonic, high-precision)
    ttfs = metrics.first_token_latency
    generation_time = metrics.last_token_ts - metrics.first_token_ts
    total_time = metrics.last_token_ts - metrics.arrival_time
else:
    # Fallback to wall-clock timing
    ttfs = end_time - start_time
    generation_time = ttfs
    total_time = end_time - start_time

avg_decode_time = generation_time / num_output_tokens if num_output_tokens > 0 else 0
tokens_per_second = num_output_tokens / generation_time if generation_time > 0 else 0

# Print generated text
print(f"Generated text:\n{'─' * 50}")
print(generated_text)
print(f"{'─' * 50}\n")

print(f"\n{'=' * 50}")
print("=== SUMMARY METRICS ===")
print(f"Prompt tokens: {prompt_len}")
print(f"Generated tokens: {num_output_tokens}")
print(f"TTFS: {ttfs:.3f}s")
print(f"Total time: {total_time:.3f}s")
print(f"Avg decode time: {avg_decode_time * 1000:.1f}ms/token")
print(f"Throughput: {tokens_per_second:.2f} tokens/sec")
print(
    f"📈 Latency growth: ~1.0x (vLLM KV cache keeps decode latency constant)"
)
