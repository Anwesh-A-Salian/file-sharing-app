
from pathlib import Path
import json
import secrets
import re
from fastapi.responses import FileResponse
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI(title="File Sharing App")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
CHUNK_SIZE = 1024 * 1024          # 1 MB
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".png", ".jpg", ".jpeg"}

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)


@app.get("/", response_class=HTMLResponse)
def home():
    index_file = BASE_DIR / "templates" / "index.html"
    return index_file.read_text(encoding="utf-8")


def load_file_metadata(code: str):
    # Codes must contain exactly 8 hexadecimal characters.
    if not re.fullmatch(r"[A-Fa-f0-9]{8}", code):
        raise HTTPException(
            status_code=400,
            detail="Invalid file code"
        )

    code = code.upper()
    metadata_path = UPLOAD_DIR / f"{code}.json"

    if not metadata_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="File code not found"
        )

    try:
        metadata = json.loads(
            metadata_path.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError):
        raise HTTPException(
            status_code=500,
            detail="Could not read file metadata"
        )

    stored_filename = metadata.get("stored_filename")

    # Prevent paths from escaping the uploads directory.
    if (
        not isinstance(stored_filename, str)
        or Path(stored_filename).name != stored_filename
    ):
        raise HTTPException(
            status_code=500,
            detail="Invalid stored file metadata"
        )

    file_path = UPLOAD_DIR / stored_filename

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Stored file not found"
        )

    return metadata, file_path


@app.get("/api/files/{code}")
def get_file_info(code: str):
    metadata, _ = load_file_metadata(code)

    return {
        "code": metadata["code"],
        "filename": metadata["original_name"],
        "size": metadata["size"],
        "download_url": f"/api/download/{metadata['code']}"
    }


@app.get("/api/download/{code}")
def download_file(code: str):
    metadata, file_path = load_file_metadata(code)

    return FileResponse(
        path=file_path,
        filename=metadata["original_name"],
        media_type="application/octet-stream"
    )

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if not filename or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )

    code = secrets.token_hex(4).upper()
    stored_filename = f"{code}{extension}"
    file_path = UPLOAD_DIR / stored_filename
    metadata_path = UPLOAD_DIR / f"{code}.json"

    size = 0

    try:
        with file_path.open("xb") as output:
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)

                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds 10 MB limit"
                    )

                output.write(chunk)

        metadata = {
            "code": code,
            "original_name": filename,
            "stored_filename": stored_filename,
            "size": size
        }

        metadata_path.write_text(
            json.dumps(metadata),
            encoding="utf-8"
        )

    except FileExistsError:
        raise HTTPException(
            status_code=409,
            detail="Code collision. Please retry."
        )

    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    finally:
        await file.close()

    return {
        "message": "File uploaded successfully",
        "code": code,
        "filename": filename,
        "size": size
    }
