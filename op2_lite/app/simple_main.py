#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

import logging
import os
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from shared.streaming_parser import StreamingJSONParser
from config import config

app = FastAPI(title="JSON-Lite OP2")
logger = logging.getLogger(__name__)

request_counter = Counter("json_requests_total", "Total JSON uploads")
process_duration = Histogram("json_process_seconds", "Time spent processing")


@app.get("/health", tags=["ops"])
def health():
    return {"status": "healthy"}


@app.get("/metrics", tags=["ops"])
def metrics():
    return StreamingResponse(iter([generate_latest()]), media_type=CONTENT_TYPE_LATEST)


@app.post("/process/file", tags=["process"])
async def process_file(file: UploadFile = File(...)):
    """
    Process a JSON file upload with validation.

    Validates:
    - File extension (.json)
    - File size (within MAX_UPLOAD_SIZE)
    - Content type (application/json)
    """
    request_counter.inc()

    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in config.ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file_ext}'. Only {', '.join(config.ALLOWED_FILE_EXTENSIONS)} files are allowed"
        )

    # Validate content type (if provided)
    if file.content_type and not file.content_type.startswith('application/json'):
        logger.warning(f"Unexpected content type: {file.content_type} for file {file.filename}")
        # Don't reject, just log - some clients may not set correct content type

    chunk_size = config.CHUNK_SIZE
    tmp_path = None

    try:
        # Write uploaded file to temporary location with size validation
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp:
            tmp_path = tmp.name
            total = 0

            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break

                total += len(chunk)

                # Validate file size during upload
                if total > config.MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {config.MAX_UPLOAD_SIZE / (1024*1024):.0f}MB"
                    )

                tmp.write(chunk)

        # Process the file
        parser = StreamingJSONParser()
        struct = parser.auto_detect_json_structure(tmp_path)
        pointer = "item" if struct == "array" else ""
        recs = 0

        for _ in parser.iter_records(tmp_path, pointer=pointer):
            recs += 1

        return JSONResponse({
            "filename": file.filename,
            "bytes": total,
            "records": recs,
            "structure": struct
        })

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Always clean up temp file
        if tmp_path and Path(tmp_path).exists():
            try:
                Path(tmp_path).unlink()
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up temp file {tmp_path}: {cleanup_error}")


if __name__ == "__main__":
    import sys

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
