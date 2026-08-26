# System Report

Captured on **2026-08-17** in `/home/zff/g2-reader` before model installation.

## Operating system

- Ubuntu 24.04.4 LTS (Noble Numbat)
- Kernel: `Linux 6.8.0-137-generic x86_64`
- Hypervisor: KVM

## CPU and memory

- CPU: Intel Xeon Gold 6252 @ 2.10 GHz
- Allocated logical CPUs: 5 (one thread per exposed core)
- System RAM: 127,109,932 kB (approximately 121 GiB)
- Swap: none

## GPU

- GPU: NVIDIA Tesla V100-PCIE-32GB
- VRAM: 32,768 MiB
- Driver: 580.178.04
- Maximum CUDA version reported by the driver: 13.0
- Compute capability reported by PyTorch: 7.0
- MIG: not applicable
- Initial GPU utilization and allocation: 0%, 0 MiB
- CUDA toolkit/compiler: not installed (`nvcc` unavailable)

The CUDA version displayed by `nvidia-smi` is a driver capability, not evidence of an installed CUDA toolkit. The environment uses the CUDA 12.6 runtime distributed with `torch==2.7.1+cu126`.

### `nvidia-smi`

```text
NVIDIA-SMI 580.178.04  Driver Version: 580.178.04  CUDA Version: 13.0
GPU 0: Tesla V100-PCIE-32GB, 32768 MiB, persistence on
Temperature: 22 C; power: 25 W / 250 W; utilization: 0%
No running GPU processes.
```

## Python and tools

| Tool | Result |
|---|---|
| System Python | 3.12.3 at `/usr/bin/python3` |
| Python 3.10 | not found on `PATH` |
| Python 3.11 | not found on `PATH` |
| Project Python | 3.12.3 at `g2_reader_lab/.venv/bin/python` |
| uv | 0.12.5 installed inside the project environment; absent before setup |
| Conda | not found |
| Mamba | not found |
| Docker | 29.7.2 |
| Git | 2.43.0 |
| Git LFS | not found |
| Hugging Face CLI | not found |

Python 3.12 was selected because it was the only available interpreter. A standard library `venv` was created first; `uv` was then installed inside it. If MinerU later proves incompatible with Python 3.12, a Python 3.11 environment will be installed with `uv` and this decision will be revised explicitly.

## Disk

At initial inspection, `/dev/vda1` had approximately 22 GiB free. After cloning VisDoM and installing the CUDA-enabled environment:

```text
Filesystem: /dev/vda1
Total:      60,271,181,824 bytes
Used:       43,774,103,552 bytes
Available:  13,796,147,200 bytes
```

Recorded local sizes:

- `.venv`: approximately 5.7 GB
- `external/G2_Reader`: approximately 9.8 MB
- `external/VisDoM`: approximately 3.5 GB

No large model checkpoint or additional corpus may be downloaded until its exact size is compared with current free space.

## Network access

Outbound Git access succeeded on 2026-08-17:

- GitHub G²-Reader HEAD resolved to `e4d047a756ef9136ea7f0c4dd8ba36eb1b08ec27`.
- GitHub VisDoM HEAD resolved to `2d809ac87360d54b0765e9be1cab75808d37642a`.
- Hugging Face G2-Reader dataset HEAD resolved to `57d76a6ab4872592dfe47dbf4fae6cd77bcf184b`.

## GPU smoke-test result

The first direct test used a 2048×2048 CUDA matrix multiplication:

- `torch.cuda.is_available()`: true
- device: Tesla V100-PCIE-32GB
- compute capability: 7.0
- peak allocated VRAM: 42,074,112 bytes

The repeatable test is [`gpu_smoke_test.py`](gpu_smoke_test.py). VLM and embedding smoke tests remain pending until model size and storage are resolved.

