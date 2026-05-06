from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any


# NOTE: This module is intentionally small and dependency-free for "local" storage.
# It also supports optional Google Drive storage (service account), with a safe
# fallback to local if Drive isn't configured or fails.


STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower()  # local | gdrive
LOCAL_ROOT = Path(os.getenv("LOCAL_STORAGE_ROOT", "storage")).resolve()
LOCAL_ROOT.mkdir(parents=True, exist_ok=True)


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def save_bytes(namespace: str, filename: str, data: bytes) -> Dict[str, Any]:
    """Persist bytes and return storage metadata.

    Returns:
      {
        "backend": "local"|"gdrive",
        "key": "relative/path" or "drive_file_id",
        "url": "web view url" or None,
        "local_path": "/abs/path" (only for local)
      }
    """

    if STORAGE_BACKEND == "gdrive":
        try:
            return _save_gdrive(namespace, filename, data)
        except Exception:
            # fallback to local for reliability
            return _save_local(namespace, filename, data)

    return _save_local(namespace, filename, data)


def _save_local(namespace: str, filename: str, data: bytes) -> Dict[str, Any]:
    safe = filename.replace("/", "_").replace("\\", "_")
    rel = Path(namespace) / f"{_ts()}_{safe}"
    abs_path = (LOCAL_ROOT / rel).resolve()
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(data)
    return {"backend": "local", "key": str(rel), "url": None, "local_path": str(abs_path)}


def _save_gdrive(namespace: str, filename: str, data: bytes) -> Dict[str, Any]:
    """Upload bytes to Google Drive using a service account.

    Requires packages:
      pip install google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib

    Env vars:
      GOOGLE_DRIVE_FOLDER_ID=...
      GOOGLE_SERVICE_ACCOUNT_JSON=/abs/path/service_account.json
    """

    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    sa_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not folder_id or not sa_path:
        raise RuntimeError("Missing GOOGLE_DRIVE_FOLDER_ID / GOOGLE_SERVICE_ACCOUNT_JSON")

    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload

    creds = Credentials.from_service_account_file(sa_path, scopes=["https://www.googleapis.com/auth/drive"])
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    safe = filename.replace("/", "_").replace("\\", "_")
    drive_name = f"{namespace}_{_ts()}_{safe}"

    media = MediaInMemoryUpload(data, mimetype="application/octet-stream", resumable=False)
    meta = {"name": drive_name, "parents": [folder_id]}

    created = service.files().create(body=meta, media_body=media, fields="id,webViewLink").execute()
    return {"backend": "gdrive", "key": created["id"], "url": created.get("webViewLink"), "local_path": None}
