
from pathlib import Path
import json
import secrets
import re
from typing import List
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



def get_group_metadata(code: str):
    if not re.fullmatch(r"[A-Fa-f0-9]{8}", code):
        raise HTTPException(
            status_code=400,
            detail="Invalid sharing code"
        )

    code = code.upper()
    metadata_path = UPLOAD_DIR / f"{code}.json"

    if not metadata_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Sharing code not found"
        )

    try:
        metadata = json.loads(
            metadata_path.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError):
        raise HTTPException(
            status_code=500,
            detail="Could not read sharing information"
        )

    if not isinstance(metadata.get("files"), list):
        raise HTTPException(
            status_code=500,
            detail="Invalid sharing information"
        )

    return metadata


@app.get("/api/files/{code}")
def get_files(code: str):
    metadata = get_group_metadata(code)

    return {
        "code": metadata["code"],
        "files": [
            {
                "id": item["id"],
                "filename": item["original_name"],
                "size": item["size"],
            }
            for item in metadata["files"]
        ],
    }


@app.get("/api/download/{code}/{file_id}")
def download_file(code: str, file_id: str):
    metadata = get_group_metadata(code)

    item = next(
        (
            file for file in metadata["files"]
            if file["id"] == file_id
        ),
        None
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="File not found in this sharing group"
        )

    stored_filename = item.get("stored_filename", "")

    if (
        not isinstance(stored_filename, str)
        or Path(stored_filename).name != stored_filename
    ):
        raise HTTPException(
            status_code=500,
            detail="Invalid stored file information"
        )

    file_path = UPLOAD_DIR / stored_filename

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Stored file not found"
        )

    return FileResponse(
        path=file_path,
        filename=item["original_name"],
        media_type="application/octet-stream",
    )



@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(
            status_code=400,
            detail="Select at least one file"
        )

    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="You can upload at most 10 files at once"
        )

    prepared_files = []

    # Validate every file before saving anything.
    for file in files:
        filename = Path(file.filename or "").name
        extension = Path(filename).suffix.lower()

        if not filename or extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {filename or 'unknown'}"
            )

        prepared_files.append({
            "upload": file,
            "filename": filename,
            "extension": extension,
        })

    code = secrets.token_hex(4).upper()
    metadata_path = UPLOAD_DIR / f"{code}.json"

    stored_paths = []
    file_metadata = []

    try:
        # Reserve the code so concurrent uploads cannot reuse it.
        with metadata_path.open("x", encoding="utf-8") as reservation:
            reservation.write("{}")

        for index, item in enumerate(prepared_files, start=1):
            file = item["upload"]
            filename = item["filename"]
            extension = item["extension"]

            stored_filename = f"{code}_{index}{extension}"
            file_path = UPLOAD_DIR / stored_filename
            size = 0

            with file_path.open("xb") as output:
                stored_paths.append(file_path)

                while chunk := await file.read(CHUNK_SIZE):
                    size += len(chunk)

                    if size > MAX_FILE_SIZE:
                        raise HTTPException(
                            status_code=413,
                            detail=f"{filename} exceeds the 10 MB limit"
                        )

                    output.write(chunk)

            file_metadata.append({
                "id": str(index),
                "original_name": filename,
                "stored_filename": stored_filename,
                "size": size,
            })

        metadata = {
            "code": code,
            "files": file_metadata,
        }

        metadata_path.write_text(
            json.dumps(metadata),
            encoding="utf-8"
        )

        return {
            "message": "Files uploaded successfully",
            "code": code,
            "files": [
                {
                    "id": item["id"],
                    "filename": item["original_name"],
                    "size": item["size"],
                }
                for item in file_metadata
            ],
        }

    except FileExistsError:
        raise HTTPException(
            status_code=409,
            detail="Sharing code collision. Please retry."
        )

    except Exception:
        for path in stored_paths:
            path.unlink(missing_ok=True)

        metadata_path.unlink(missing_ok=True)
        raise

    finally:
        for file in files:
            await file.close()
