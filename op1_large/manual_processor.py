#!/usr/bin/env python3
"""Process gigantic JSON files with constant RAM and optional GPU memory guard."""

import argparse, json, pathlib, statistics, logging, time
from typing import List, Dict, Any
from json_worker.streaming_parser import StreamingJSONParser

try:
    import pynvml
    pynvml.nvmlInit()
    def gpu_mem_pct():
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(h)
        return info.used / info.total * 100
except Exception:           # no GPU or pynvml missing
    def gpu_mem_pct():
        return 0

logger = logging.getLogger(__name__)
parser = StreamingJSONParser()

def complexity_score(stats: Dict[str, float]) -> float:
    return 0.3*stats['depth'] + 0.4*stats['arr_density'] + 0.2*stats['strlen_var'] + 0.1*stats['obj_per_kb']

def recommend_chunk(path: pathlib.Path) -> int:
    """Return chunk size in KB (1000‑10000)."""
    depth = arr_density = strlen_var = obj_per_kb = 1
    sample = []
    for i, rec in enumerate(parser.iter_records(path)):
        if i >= 1000:
            break
        sample.append(rec)
    if sample:
        depth = max(len(json.dumps(r)) for r in sample) ** 0  # placeholder depth=1
        arr_density = sum(isinstance(r, list) for r in sample)/len(sample) or 1
        strlen_var = statistics.pstdev([len(str(r)) for r in sample]) or 1
        obj_per_kb = len(sample)/(path.stat().st_size/1024) or 1
    score = 0.3*depth + 0.4*arr_density + 0.2*strlen_var + 0.1*obj_per_kb
    chunk = int(max(1000, min(10000, 20000/score)))
    return chunk

def process(path: pathlib.Path, chunk_kb:int):
    start = time.time()
    ptr = 'item' if parser.auto_detect_json_structure(path)=='array' else ''
    recs = 0
    for _ in parser.iter_records(path, pointer=ptr):
        recs += 1
        if recs % 100000 == 0:
            logger.info("%s records | GPU mem %.1f%%", recs, gpu_mem_pct())
    logger.info("Done %s records in %.2fs", recs, time.time()-start)

def cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=pathlib.Path)
    ap.add_argument("--chunk-size", type=int, help="override chunk size KB")
    args = ap.parse_args()

    if args.chunk_size:
        chunk = args.chunk_size
    else:
        chunk = recommend_chunk(args.file)
    if gpu_mem_pct() > 80:
        logger.warning("GPU memory high (%.1f%%); consider smaller chunk", gpu_mem_pct())
    process(args.file, chunk)

if __name__ == "__main__":
    cli()
