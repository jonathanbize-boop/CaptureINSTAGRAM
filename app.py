"""CaptureINSTAGRAM — télécharge les photos Instagram/Facebook et les convertit en WebP.

Lancement : python app.py  →  http://localhost:5000
"""

import os
import secrets
import shutil
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from core.converter import convert_directory, zip_files
from core.downloader import (DownloadError, detect_platform, download_photos,
                             normalize_source)


def _template_folder() -> str:
    """Dossier des templates, y compris une fois empaqueté par PyInstaller.

    En mode gelé (« frozen »), PyInstaller extrait les ressources dans
    `sys._MEIPASS` ; Flask doit y chercher `templates/`.
    """
    base = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent
    return str(base / "templates")


app = Flask(__name__, template_folder=_template_folder())

WORK_ROOT = Path(tempfile.gettempdir()) / "captureinstagram-jobs"
WORK_ROOT.mkdir(parents=True, exist_ok=True)
MAX_LIMIT = 200
# Durée de rétention des résultats avant purge automatique (secondes).
JOB_TTL = int(os.environ.get("JOB_TTL", 2 * 3600))
# Si défini, l'API exige ce code d'accès (protège l'instance publique).
ACCESS_CODE = os.environ.get("ACCESS_CODE", "").strip()

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _authorized() -> bool:
    if not ACCESS_CODE:
        return True
    supplied = request.headers.get("X-Access-Code") or request.args.get("code") or ""
    return secrets.compare_digest(supplied, ACCESS_CODE)


def _purge_old_jobs() -> None:
    """Supprime les jobs terminés depuis plus de JOB_TTL et leurs fichiers."""
    now = time.time()
    with _jobs_lock:
        expired = [
            job_id for job_id, job in _jobs.items()
            if job["status"] in ("done", "error") and now - job["finished_at"] > JOB_TTL
        ]
        for job_id in expired:
            del _jobs[job_id]
    for workdir in WORK_ROOT.iterdir():
        # Couvre aussi les dossiers orphelins laissés par un redémarrage.
        if workdir.name not in _jobs and now - workdir.stat().st_mtime > JOB_TTL:
            shutil.rmtree(workdir, ignore_errors=True)


def _log(job_id: str, message: str) -> None:
    with _jobs_lock:
        _jobs[job_id]["log"].append(
            f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        )


def _set(job_id: str, **fields) -> None:
    with _jobs_lock:
        _jobs[job_id].update(fields)


def _run_job(job_id: str, source: str, limit: int, quality: int,
             lossless: bool, max_size: int | None, cookies_text: str) -> None:
    workdir = WORK_ROOT / job_id
    raw_dir = workdir / "originaux"
    webp_dir = workdir / "webp"
    cookies_file = None
    try:
        workdir.mkdir(parents=True, exist_ok=True)
        if cookies_text.strip():
            cookies_file = workdir / "cookies.txt"
            cookies_file.write_text(cookies_text)

        _set(job_id, status="downloading")
        download_photos(
            source, raw_dir, limit=limit, cookies_file=cookies_file,
            on_progress=lambda msg: _log(job_id, msg),
        )

        _set(job_id, status="converting")
        converted = convert_directory(
            raw_dir, webp_dir, quality=quality, lossless=lossless,
            max_size=max_size, on_progress=lambda msg: _log(job_id, msg),
        )
        if not converted:
            raise DownloadError("Aucune image n'a pu être convertie en WebP.")

        zip_path = zip_files(converted, workdir / "photos-webp.zip")
        _log(job_id, f"Terminé : {len(converted)} image(s) WebP prête(s).")
        _set(job_id, status="done", count=len(converted),
             zip_path=str(zip_path), finished_at=time.time())
    except DownloadError as exc:
        _log(job_id, str(exc))
        _set(job_id, status="error", error=str(exc), finished_at=time.time())
    except Exception as exc:  # noqa: BLE001 — le job ne doit jamais planter en silence
        _log(job_id, f"Erreur inattendue : {exc}")
        _set(job_id, status="error", error=str(exc), finished_at=time.time())
    finally:
        # Les cookies ne restent jamais sur le disque après le job.
        if cookies_file and cookies_file.exists():
            cookies_file.unlink()
        shutil.rmtree(raw_dir, ignore_errors=True)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/config")
def config():
    return jsonify({"auth_required": bool(ACCESS_CODE)})


@app.post("/api/jobs")
def create_job():
    if not _authorized():
        return jsonify({"error": "Code d'accès invalide."}), 401
    _purge_old_jobs()
    data = request.get_json(force=True)
    source = (data.get("source") or "").strip()
    try:
        detect_platform(normalize_source(source))  # validation avant de créer le job
    except DownloadError as exc:
        return jsonify({"error": str(exc)}), 400

    limit = max(1, min(int(data.get("limit") or 50), MAX_LIMIT))
    quality = max(1, min(int(data.get("quality") or 85), 100))
    lossless = bool(data.get("lossless"))
    max_size = int(data["max_size"]) if data.get("max_size") else None
    cookies_text = data.get("cookies") or ""

    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {"status": "pending", "log": [], "count": 0,
                         "zip_path": None, "error": None, "finished_at": 0}
    threading.Thread(
        target=_run_job,
        args=(job_id, source, limit, quality, lossless, max_size, cookies_text),
        daemon=True,
    ).start()
    return jsonify({"job_id": job_id}), 202


@app.get("/api/jobs/<job_id>")
def job_status(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return jsonify({"error": "Job introuvable."}), 404
        return jsonify({
            "status": job["status"],
            "log": job["log"],
            "count": job["count"],
            "error": job["error"],
        })


@app.get("/api/jobs/<job_id>/download")
def job_download(job_id):
    if not _authorized():
        return jsonify({"error": "Code d'accès invalide."}), 401
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None or job["status"] != "done" or not job["zip_path"]:
        return jsonify({"error": "Archive non disponible."}), 404
    return send_file(job["zip_path"], as_attachment=True,
                     download_name="photos-webp.zip")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
