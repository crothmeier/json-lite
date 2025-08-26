# Conversation Search Pipeline

## Features
- Imports ChatGPT and Claude conversation exports
- SQLite FTS5 full-text search across 118k+ messages
- Web UI for searching
- Automated import and backup

## Quick Start
```bash
python scripts/import_to_sqlite.py
python web/app.py
# Visit http://localhost:5000
```

## Components

- `converters/` - Format conversion tools
- `scripts/` - Import, search, backup tools
- `web/` - Flask search interface
- `deployment/` - Systemd service files