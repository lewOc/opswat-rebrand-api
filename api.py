from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Any, Literal, Optional
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from opswat_rebrand.pipeline import run as run_rebrand


PROJECT = Path(__file__).resolve().parent
load_dotenv(PROJECT / ".env")

os.environ.setdefault("OPSWAT_BRAND_DIR", str(PROJECT / "opswat-brand"))

JOBS_DIR = Path(os.environ.get("REBRAND_JOBS_DIR", PROJECT / "outputs" / "jobs"))
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "75"))
JOB_WORKERS = int(os.environ.get("JOB_WORKERS", "2"))
JOB_RETENTION_SECONDS = int(os.environ.get("JOB_RETENTION_SECONDS", "86400"))

ALLOWED_DEPTHS = {"tokens", "theme", "full"}
ALLOWED_DESIGN_MODES = {"product_ui"}
ALLOWED_TARGET_THEMES = {"auto", "light", "dark"}
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".next", "vendor", "_archive"}

executor = ThreadPoolExecutor(max_workers=JOB_WORKERS)
jobs_lock = Lock()
jobs: dict[str, dict[str, Any]] = {}

app = FastAPI(
    title="OPSWAT Rebrand API",
    version="0.1.0",
    description=(
        "Reusable, app-agnostic codebase redesign/rebrand service. V1 accepts any web codebase ZIP, "
        "runs the deterministic OPSWAT Product UI rebrand pass, and returns a rebranded ZIP plus report."
    ),
)


class RebrandJob(BaseModel):
    id: str
    status: Literal["queued", "running", "complete", "failed"]
    message: str
    depth: Literal["tokens", "theme", "full"]
    design_mode: Literal["product_ui"]
    target_theme: Literal["auto", "light", "dark"] = "auto"
    created_at: float
    updated_at: float
    report_url: Optional[str] = None
    download_url: Optional[str] = None
    error: Optional[str] = None


def now() -> float:
    return time.time()


def safe_name(value: str, fallback: str = "codebase") -> str:
    stem = Path(value).stem.lower()
    stem = re.sub(r"[^a-z0-9_.-]+", "-", stem).strip(".-")
    return stem[:80] or fallback


def snapshot(job_id: str) -> dict[str, Any]:
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Rebrand job not found")
        return {key: value for key, value in job.items() if key != "future"}


def update_job(job_id: str, **fields: Any) -> None:
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return
        job.update(fields)
        job["updated_at"] = now()


def prune_jobs() -> None:
    cutoff = now() - JOB_RETENTION_SECONDS
    with jobs_lock:
        expired = [
            job_id
            for job_id, job in jobs.items()
            if job.get("updated_at", job.get("created_at", 0)) < cutoff
            and job.get("status") in {"complete", "failed"}
        ]
        for job_id in expired:
            jobs.pop(job_id, None)


def ensure_within(child: Path, parent: Path) -> None:
    child_resolved = child.resolve()
    parent_resolved = parent.resolve()
    if parent_resolved != child_resolved and parent_resolved not in child_resolved.parents:
        raise HTTPException(status_code=400, detail="ZIP contains an unsafe path")


def validate_zip_member(member: zipfile.ZipInfo) -> None:
    name = member.filename
    if not name or name.startswith(("/", "\\")):
        raise HTTPException(status_code=400, detail=f"ZIP contains an unsafe absolute path: {name}")
    parts = Path(name).parts
    if any(part == ".." for part in parts):
        raise HTTPException(status_code=400, detail=f"ZIP contains path traversal: {name}")
    mode = member.external_attr >> 16
    if (mode & 0o170000) == 0o120000:
        raise HTTPException(status_code=400, detail=f"ZIP contains symlink: {name}")


def should_skip_zip_member(member: zipfile.ZipInfo) -> bool:
    parts = Path(member.filename).parts
    return member.filename.startswith("__MACOSX/") or any(part in SKIP_DIRS for part in parts)


def extract_zip_safely(zip_path: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        if not members:
            raise HTTPException(status_code=400, detail="ZIP archive is empty")
        for member in members:
            validate_zip_member(member)
            if should_skip_zip_member(member):
                continue
            target = dest / member.filename
            ensure_within(target, dest)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)

    candidates = [path for path in dest.iterdir() if not path.name.startswith("__MACOSX")]
    directories = [path for path in candidates if path.is_dir()]
    files = [path for path in candidates if path.is_file()]
    if len(directories) == 1 and not files:
        source_root = directories[0]
    else:
        source_root = dest
    ensure_within(source_root, dest)
    return source_root


def zip_directory(source: Path, output_zip: Path) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in source.rglob("*"):
            if path.is_dir():
                continue
            archive.write(path, path.relative_to(source))


def read_report(job_dir: Path) -> dict[str, Any]:
    report_path = job_dir / "output" / "REBRAND_REPORT.json"
    if not report_path.exists():
        return {}
    return json.loads(report_path.read_text(encoding="utf-8"))


def write_metadata(job_dir: Path, metadata: dict[str, Any]) -> None:
    (job_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def process_job(job_id: str, upload_path: Path, depth: str, design_mode: str, target_theme: str) -> None:
    job_dir = JOBS_DIR / job_id
    try:
        update_job(job_id, status="running", message="Extracting uploaded codebase")
        extract_dir = job_dir / "source"
        source_root = extract_zip_safely(upload_path, extract_dir)
        output_root = job_dir / "output"

        update_job(job_id, message="Applying OPSWAT deterministic rebrand pass")
        report = run_rebrand(
            str(source_root),
            str(output_root),
            depth=depth,
            target_theme=target_theme,
            verbose=False,
        )

        update_job(job_id, message="Packaging rebranded codebase")
        artifact_path = job_dir / f"{job_id}-opswat-rebrand.zip"
        zip_directory(output_root, artifact_path)

        metadata = {
            "id": job_id,
            "status": "complete",
            "depth": depth,
            "design_mode": design_mode,
            "target_theme": target_theme,
            "report": report,
            "artifact": artifact_path.name,
        }
        write_metadata(job_dir, metadata)
        update_job(
            job_id,
            status="complete",
            message="Rebrand complete",
            report_url=f"/api/rebrands/{job_id}/report",
            download_url=f"/api/rebrands/{job_id}/download",
        )
    except Exception as exc:
        write_metadata(job_dir, {"id": job_id, "status": "failed", "error": str(exc)})
        update_job(job_id, status="failed", message="Rebrand failed", error=str(exc))


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "OPSWAT Rebrand API",
        "docs": "/docs",
        "health": "/api/health",
        "boundary": "V1 rebrands app-agnostic web codebase ZIPs only. Documents/PDFs are future routes.",
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "jobs_dir": str(JOBS_DIR),
        "max_upload_mb": MAX_UPLOAD_MB,
        "workers": JOB_WORKERS,
        "brand_dir": os.environ.get("OPSWAT_BRAND_DIR"),
        "brand_dir_exists": Path(os.environ.get("OPSWAT_BRAND_DIR", "")).exists(),
        "supported_depths": sorted(ALLOWED_DEPTHS),
        "supported_design_modes": sorted(ALLOWED_DESIGN_MODES),
        "supported_target_themes": sorted(ALLOWED_TARGET_THEMES),
        "future_routes": ["documents", "pdfs", "presentations"],
    }


@app.post("/api/rebrands")
async def create_rebrand(
    file: UploadFile = File(...),
    depth: Literal["tokens", "theme", "full"] = Form("full"),
    design_mode: Literal["product_ui"] = Form("product_ui"),
    target_theme: Literal["auto", "light", "dark"] = Form("auto"),
) -> dict[str, Any]:
    prune_jobs()
    if depth not in ALLOWED_DEPTHS:
        raise HTTPException(status_code=400, detail="Unsupported depth")
    if design_mode not in ALLOWED_DESIGN_MODES:
        raise HTTPException(status_code=400, detail="Unsupported design mode")
    if target_theme not in ALLOWED_TARGET_THEMES:
        raise HTTPException(status_code=400, detail="Unsupported target theme")
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload a .zip codebase archive")

    job_id = f"{safe_name(file.filename)}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid4().hex[:8]}"
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    upload_path = job_dir / "upload.zip"

    total = 0
    with upload_path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_MB * 1024 * 1024:
                raise HTTPException(status_code=413, detail=f"Upload exceeds {MAX_UPLOAD_MB} MB limit")
            out.write(chunk)

    created = now()
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "message": "Queued",
            "depth": depth,
            "design_mode": design_mode,
            "target_theme": target_theme,
            "created_at": created,
            "updated_at": created,
            "original_filename": file.filename,
            "upload_bytes": total,
        }
        jobs[job_id]["future"] = executor.submit(process_job, job_id, upload_path, depth, design_mode, target_theme)

    return snapshot(job_id)


@app.get("/api/rebrands")
def list_rebrands() -> dict[str, Any]:
    prune_jobs()
    with jobs_lock:
        items = [
            {key: value for key, value in job.items() if key != "future"}
            for job in sorted(jobs.values(), key=lambda item: item.get("created_at", 0), reverse=True)
        ]
    return {"items": items}


@app.get("/api/rebrands/{job_id}")
def get_rebrand(job_id: str) -> dict[str, Any]:
    return snapshot(job_id)


@app.get("/api/rebrands/{job_id}/report")
def get_rebrand_report(job_id: str) -> dict[str, Any]:
    job = snapshot(job_id)
    if job["status"] != "complete":
        raise HTTPException(status_code=409, detail="Rebrand report is not ready")
    report = read_report(JOBS_DIR / job_id)
    return {"job": job, "report": report}


@app.get("/api/rebrands/{job_id}/download")
def download_rebrand(job_id: str) -> FileResponse:
    job = snapshot(job_id)
    if job["status"] != "complete":
        raise HTTPException(status_code=409, detail="Rebrand artifact is not ready")
    job_dir = JOBS_DIR / job_id
    matches = list(job_dir.glob("*-opswat-rebrand.zip"))
    if not matches:
        raise HTTPException(status_code=404, detail="Rebrand artifact not found")
    return FileResponse(matches[0], media_type="application/zip", filename=matches[0].name)


@app.get("/api/rebrands/{job_id}/workorder")
def get_rebrand_workorder(job_id: str) -> FileResponse:
    job = snapshot(job_id)
    if job["status"] != "complete":
        raise HTTPException(status_code=409, detail="Rebrand workorder is not ready")
    path = JOBS_DIR / job_id / "output" / "RESTYLE_WORKORDER.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Workorder not found for this depth")
    return FileResponse(path, media_type="text/markdown", filename="RESTYLE_WORKORDER.md")
