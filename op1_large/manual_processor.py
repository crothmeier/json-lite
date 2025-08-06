#!/usr/bin/env python3
"""Process gigantic JSON files with constant RAM and optional GPU memory guard."""

import argparse
import logging
import pathlib
import statistics
import sys
import time
from typing import Dict

from shared.streaming_parser import StreamingJSONParser

sys.path.append(str(pathlib.Path(__file__).parent.parent))
from shared.gpu_guard import GPUMemoryGuard

try:
    import pynvml

    pynvml.nvmlInit()

    def gpu_mem_pct():
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(h)
        return info.used / info.total * 100

except Exception:  # no GPU or pynvml missing

    def gpu_mem_pct():
        return 0


logger = logging.getLogger(__name__)
parser = StreamingJSONParser()
gpu_guard = GPUMemoryGuard(threshold_percent=80)


def complexity_score(stats: Dict[str, float]) -> float:
    # Normalize obj_per_kb to reduce its impact on deeply nested structures
    normalized_obj_per_kb = min(stats["obj_per_kb"], 10)
    return 0.5 * stats["depth"] + 0.2 * stats["arr_density"] + 0.2 * stats["strlen_var"] + 0.1 * normalized_obj_per_kb


def get_json_depth(obj):
    """Recursively calculate the maximum depth of a JSON object."""
    if isinstance(obj, dict):
        if not obj:
            return 0
        return 1 + max(get_json_depth(v) for v in obj.values())
    elif isinstance(obj, list):
        if not obj:
            return 0
        return 1 + max(get_json_depth(item) for item in obj)
    else:
        return 0


def recommend_chunk(path: pathlib.Path) -> int:
    """Return chunk size in KB (1000‑10000)."""
    sample = []
    for i, rec in enumerate(parser.iter_records(path)):
        sample.append(rec)
        if i >= 999:  # Stop after 1000 records (0-999)
            break

    if sample:
        stats = {
            "depth": max(get_json_depth(r) for r in sample),
            "arr_density": sum(isinstance(r, list) for r in sample) / len(sample),
            "strlen_var": statistics.pstdev([len(str(r)) for r in sample]) or 1,
            "obj_per_kb": len(sample) / (path.stat().st_size / 1024),
        }
    else:
        stats = {"depth": 1, "arr_density": 1, "strlen_var": 1, "obj_per_kb": 1}

    score = complexity_score(stats)
    chunk = int(max(1000, min(10000, 20000 / score)))
    return chunk


def process(path: pathlib.Path, chunk_kb: int):
    start = time.time()
    ptr = "item" if parser.auto_detect_json_structure(path) == "array" else ""
    recs = 0

    # Check GPU memory before processing
    use_gpu = gpu_guard.should_use_gpu()
    if use_gpu:
        logger.info("GPU processing enabled")
    else:
        logger.info("GPU processing disabled due to memory constraints")

    for _ in parser.iter_records(path, pointer=ptr):
        recs += 1
        if recs % 100000 == 0:
            logger.info("%s records | GPU mem %.1f%%", recs, gpu_mem_pct())
    logger.info("Done %s records in %.2fs", recs, time.time() - start)


def cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=pathlib.Path)
    ap.add_argument("--chunk-size", type=int, help="override chunk size KB")
    args = ap.parse_args()

    if args.chunk_size:
        chunk = args.chunk_size
    else:
        chunk = recommend_chunk(args.file)
    if not gpu_guard.should_use_gpu():
        logger.warning("GPU memory high (%.1f%%); using CPU processing", gpu_guard.get_memory_usage())
    process(args.file, chunk)


if __name__ == "__main__":
    cli()
