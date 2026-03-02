#include <stdio.h>

// general flow of any cuda program :- we write kernel func andin the main we decide size first then cpu mem and gpu mem allocation
// then copy cpu to gpu mem and launch kernel and copy gpu to cpu mem

// Kernel function to add two vectors
__global__ void vectorAdd(float *a, float *b, float *c, int n) {
    int idx = threadIdx.x + blockIdx.x * blockDim.x; //global thread index
    if (idx < n) {
        c[idx] = a[idx] + b[idx];
    }
}

int main() {
    int n = 1;
    size_t size = n * sizeof(float);

    // Allocate mem on the cpu
    float h_a[n], h_b[n], h_c[n];
    for (int i = 0; i < n; i++) {
        h_a[i] = i * 1.0f; // Initialize vector a
        h_b[i] = i * 2.0f; // Initialize vector b
    }

    // Allocate memory on the device - gpu
    float *d_a, *d_b, *d_c;
    cudaMalloc((void **)&d_a, size);
    cudaMalloc((void **)&d_b, size);
    cudaMalloc((void **)&d_c, size);

    // Copy data from cpu to gpu
    cudaMemcpy(d_a, h_a, size, cudaMemcpyHostToDevice);
    cudaMemcpy(d_b, h_b, size, cudaMemcpyHostToDevice);

    // Launch the kernel with 1 block of 10 threads
    int threadsPerBlock = 10;
    int blocksPerGrid = (n + threadsPerBlock - 1) / threadsPerBlock;
    vectorAdd<<<blocksPerGrid, threadsPerBlock>>>(d_a, d_b, d_c, n);

    // Copy result back gpu to cpu
   cudaMemcpy(h_c, d_c, size, cudaMemcpyDeviceToHost);

    printf("Result:\n");
    for (int i = 0; i < n; i++) {
        printf("%f + %f = %f\n", h_a[i], h_b[i], h_c[i]);
    }

    // Free mem
    cudaFree(d_a);
    cudaFree(d_b);
    cudaFree(d_c);

    return 0;
}
