#include <stdio.h>

// 5.89 ms
__global__ void scalarMul(float *d_I, float *d_O, int n, float scalar) {
    // int idx = blockIdx.x * blockDim.x + threadIdx.x;

    // in grid stride loop  we dont allow each element per thread , we need to scale for large numbers of elements
    // like proper distribution --> th1 will do 0 , 8,16 .. th2 will do1,9,17.... etc --> idx += blockDim.x*gridDim.x

    for (int idx = blockIdx.x * blockDim.x + threadIdx.x;
        idx<n;
        idx += blockDim.x*gridDim.x){
            d_O[idx] = d_I[idx] * scalar;
        }
    // if (idx < n) {
    //     d_O[idx] = d_I[idx] * scalar;
    // }
}

int main() {
    //test with 1m
    int n = 100000000;
    size_t size = n * sizeof(float); // 40 bytes

    // host input array
    float *h_I = (float*) malloc(size);
    // host output array
    float *h_O = (float*) malloc(size);

    // allocate
    for(int i = 0; i<n; i++){
        h_I[i] = i;
    }

    // allocate to device
    float *d_I, *d_O;
    cudaMalloc(&d_I, size);
    cudaMalloc(&d_O, size);

    //copy
    cudaMemcpy(d_I, h_I, size, cudaMemcpyHostToDevice);

    // 262,144 threads
    int threadsPerBlock = 256;
    int blocks = 1024;

    // calc kernel time
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    // start event
    cudaEventRecord(start);
    scalarMul<<<blocks, threadsPerBlock>>>(d_I, d_O, n, 2.0f);
    cudaEventRecord(stop); // stop event

    // wait for kernel
    cudaEventSynchronize(stop);
    float milliseconds = 0;
    cudaEventElapsedTime(&milliseconds, start, stop);
    printf("Kernel execution time: %f ms\n", milliseconds); //calc

    cudaMemcpy(h_O, d_O, size, cudaMemcpyDeviceToHost);

    // printf("Result:\n");
    // for (int i = 0; i < n; i++) {
    //     printf("%f * 2 = %f\n", h_I[i], h_O[i]);
    // }


    free(h_I);
    free(h_O);

    cudaFree(d_I);
    cudaFree(d_O);

    return 0;





}
