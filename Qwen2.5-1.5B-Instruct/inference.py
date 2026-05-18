import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_PATH = "/home/sagnik/experiments/Qwen2.5-1.5B-Instruct"
MAX_NEW_TOKENS = 100

print("🔄 Loading model...")
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, device_map="cuda")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

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

prompt_text = tokenizer.apply_chat_template(
    messages, tokenize=False, add_generation_prompt=True
)
input_tokens = tokenizer(prompt_text, return_tensors="pt").to(model.device)
input_ids = input_tokens["input_ids"].clone()
prompt_len = input_ids.shape[1]

print(f"✅ Model loaded | Prompt tokens: {prompt_len}\n")
print("=== RAW INFERENCE (NO KV CACHE) - PER-STEP TRACKING ===\n")

torch.cuda.synchronize()
start_time = time.time()
first_token_time = None
generated_ids = input_ids.clone()
per_token_times = []

with torch.no_grad():
    for step in range(MAX_NEW_TOKENS):
        
        torch.cuda.synchronize()
        step_start = time.time()

        # Full forward pass over growing sequence
        logits = model(generated_ids).logits[:, -1, :]  # full attention block here
        probs = torch.softmax(logits, dim=-1)
        next_token = torch.multinomial(probs, num_samples=1)

        torch.cuda.synchronize()
        step_end = time.time()
        step_duration = step_end - step_start
        per_token_times.append(step_duration)

        if first_token_time is None:
            first_token_time = step_end

        generated_ids = torch.cat([generated_ids, next_token], dim=1)

        # 📊 Print step info
        token_text = tokenizer.decode(next_token)
        seq_len = generated_ids.shape[1]
        print(
            f"Step {step + 1:2d} | Seq len: {seq_len:3d} | Time: {step_duration * 1000:6.1f}ms | Token: '{token_text}'"
        )

        if next_token.item() == tokenizer.eos_token_id:
            print("\n🛑 EOS detected, stopping generation")
            break

end_time = time.time()

text_output = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
num_input_tokens = input_ids.shape[1]
num_output_tokens = generated_ids.shape[1] - num_input_tokens
ttfs = (first_token_time - start_time) if first_token_time is not None else 0.0
total_time = end_time - start_time
generation_time = total_time - ttfs
tokens_per_second = num_output_tokens / generation_time if generation_time > 0 else 0

print(f"\n{'=' * 50}")
print("=== SUMMARY METRICS ===")
print(f"Prompt tokens: {num_input_tokens}")
print(f"Generated tokens: {num_output_tokens}")
print(f"TTFS: {ttfs:.3f}s")
print(f"Total time: {total_time:.3f}s")
print(
    f"Avg decode time: {sum(per_token_times) / len(per_token_times) * 1000:.1f}ms/token"
)
print(f"Throughput: {tokens_per_second:.2f} tokens/sec")
print(
    f"📈 Latency growth: {per_token_times[0] * 1000:.1f}ms → {per_token_times[-1] * 1000:.1f}ms ({per_token_times[-1] / per_token_times[0]:.1f}x slower)"
)
