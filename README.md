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

## ChatGPT Export Extractor

The JSON-Lite package includes a memory-efficient tool for extracting conversations from ChatGPT export files. It uses streaming JSON parsing to handle large export files (600MB+) while maintaining low memory usage (<120MB RSS).

### Installation

```bash
pip install -e .[test]
```

### CLI Usage

Extract all conversations to markdown files:
```bash
jsonlite-extract conversations.json -o output_dir --progress
```

Extract with options:
```bash
# Limit to first 10 conversations
jsonlite-extract conversations.json -o output_dir --limit 10 --progress

# Enable verbose output
jsonlite-extract conversations.json -o output_dir --verbose --progress

# Split conversations (default behavior)
jsonlite-extract conversations.json -o output_dir --split-conversations
```

### Features

- **Memory Efficient**: Streams large JSON files using ijson, keeping RSS under 120MB
- **Markdown Output**: Each conversation is saved as a formatted markdown file
- **Progress Tracking**: Optional progress display during processing
- **Configurable**: Limit number of conversations, verbose mode, and more

### Example Output

Each conversation is saved as a markdown file with the format:
```
{conversation_id}_{sanitized_title}.md
```

The markdown includes:
- Conversation title and metadata
- Chronologically ordered messages
- Clear role indicators (User/Assistant/System)
