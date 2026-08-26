"""Run a deterministic CUDA tensor smoke test and optionally persist JSON output."""

from __future__ import annotations

import argparse
import json
import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import torch


@dataclass(frozen=True)
class SmokeResult:
    torch_version: str
    python_version: str
    cuda_available: bool
    cuda_runtime: str | None
    device_name: str | None
    compute_capability: tuple[int, int] | None
    matrix_size: int
    latency_seconds: float | None
    peak_allocated_bytes: int | None
    checksum: float | None


def run_smoke_test(matrix_size: int = 2048, seed: int = 20260817) -> SmokeResult:
    """Multiply deterministic tensors and report latency and peak allocation."""
    if matrix_size <= 0:
        raise ValueError("matrix_size must be positive")

    if not torch.cuda.is_available():
        return SmokeResult(
            torch_version=torch.__version__,
            python_version=platform.python_version(),
            cuda_available=False,
            cuda_runtime=torch.version.cuda,
            device_name=None,
            compute_capability=None,
            matrix_size=matrix_size,
            latency_seconds=None,
            peak_allocated_bytes=None,
            checksum=None,
        )

    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    device = torch.device("cuda:0")
    torch.cuda.empty_cache()
    left = torch.randn(matrix_size, matrix_size, device=device)
    right = torch.randn(matrix_size, matrix_size, device=device)
    torch.cuda.synchronize(device)
    started = time.perf_counter()
    product = left @ right
    torch.cuda.synchronize(device)
    latency = time.perf_counter() - started

    return SmokeResult(
        torch_version=torch.__version__,
        python_version=platform.python_version(),
        cuda_available=True,
        cuda_runtime=torch.version.cuda,
        device_name=torch.cuda.get_device_name(device),
        compute_capability=torch.cuda.get_device_capability(device),
        matrix_size=matrix_size,
        latency_seconds=latency,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        checksum=float(product[0, 0].item()),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-size", type=int, default=2048)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = run_smoke_test(matrix_size=args.matrix_size)
    payload = json.dumps(asdict(result), indent=2)
    print(payload)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    return 0 if result.cuda_available else 1


if __name__ == "__main__":
    raise SystemExit(main())

