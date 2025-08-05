#!/usr/bin/env python3
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import logging, tempfile, shutil, os
from pathlib import Path
from app.json_worker.streaming_parser import StreamingJSONParser
import ijson

app = FastAPI(title="JSON-Lite OP2")
logger = logging.getLogger(__name__)

request_counter = Counter("json_requests_total", "Total JSON uploads")
process_duration = Histogram("json_process_seconds", "Time spent processing")

@app.get("/health", tags=["ops"])
def health():
    return {"status": "healthy"}

@app.get("/metrics", tags=["ops"])
def metrics():
    return StreamingResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/process/file", tags=["process"])
async def process_file(file: UploadFile = File(...)):
    request_counter.inc()
    chunk_size = 8*1024*1024  # 8 MB
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        total = 0
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            tmp.write(chunk)
            total += len(chunk)
        tmp_path = tmp.name
    try:
        parser = StreamingJSONParser()
        struct = parser.auto_detect_json_structure(tmp_path)
        pointer = 'item' if struct == 'array' else ''
        recs = 0
        for _ in parser.iter_records(tmp_path, pointer=pointer):
            recs += 1
        Path(tmp_path).unlink()
        return JSONResponse({"filename": file.filename, "bytes": total, "records": recs})
    except Exception as e:
        Path(tmp_path).unlink()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn, sys
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
