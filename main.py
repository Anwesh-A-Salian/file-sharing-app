from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI(title="File Sharing App")

BASE_DIR = Path(__file__).resolve().parent

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)


@app.get("/", response_class=HTMLResponse)
def home():
    index_file = BASE_DIR / "templates" / "index.html"
    return index_file.read_text(encoding="utf-8")