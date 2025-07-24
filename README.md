# JSON‑Lite — OP‑1 (large) & OP‑2 (lite)

**TL;DR decision tree**

```
File ≥ 500 MB ?
└─ YES  → OP‑1 (manual_processor CLI)
   NO
   └─ Need API?
      └─ YES → OP‑2 (single‑container FastAPI)
         NO  → OP‑1
```

| Phase | Goal | Key features |
|-------|------|--------------|
| v0.1.x | Baseline OP‑1/OP‑2 (CPU) | streaming parser, Prom metrics |
| v0.2.x | op3_hybrid (GPU) | RAPIDS cuDF pipeline, NVML fail‑over, Redis WAL |
| v0.3.x | Multi‑GPU scaling | NCCL, warp‑optimised kernels |

## Quick‑start

### OP‑1 — CLI for huge files
```bash
cd op1_large
pip install -r requirements.txt
python manual_processor.py analyze /path/to/huge.json
```

### OP‑2 — API service
```bash
cd op2_lite
docker compose up -d
curl -F file=@sample.json http://localhost:8000/process/file
```
