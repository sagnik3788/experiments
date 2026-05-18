import torch
import triton.language as tl

import triton


## kernel code
@triton.jit
def add_kernel(x_ptr, y_ptr, output_ptr, n, BLOCK_SIZE: tl.constexpr):
    p_id = tl.program_id(0)
    offset = p_id * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offset < n

    x = tl.load(x_ptr + offset, mask=mask)
    y = tl.load(y_ptr + offset, mask=mask)

    out = x + y

    tl.store(output_ptr + offset, out, mask=mask)


## host code
x = torch.tensor([1, 2, 3, 4, 5], device="cuda", dtype=torch.float32)
y = torch.tensor([5, 6, 7, 8, 9], device="cuda", dtype=torch.float32)

out = torch.empty_like(x)

BLOCK_SIZE = 4
n = x.numel()

# 10 elements/ 2 blcoks --> 5 each simple :0
grid = (triton.cdiv(n, BLOCK_SIZE),)

add_kernel[grid](x, y, out, n, BLOCK_SIZE=BLOCK_SIZE)  # type: ignore

print(out)
