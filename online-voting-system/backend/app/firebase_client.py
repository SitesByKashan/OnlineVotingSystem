from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .config import get_settings


@lru_cache
def get_firestore_client():
    settings = get_settings()
    if not settings.firebase_credentials_path:
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            if settings.firebase_credentials_json:
                cred = credentials.Certificate(json.loads(settings.firebase_credentials_json))
            elif settings.firebase_credentials_path:
                cred = credentials.Certificate(settings.firebase_credentials_path)
            else:
                return None
            firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id})
        return firestore.client()
    except Exception:
        return None


def sync_document(collection: str, document_id: str | int, payload: dict[str, Any]) -> bool:
    client = get_firestore_client()
    if client is None:
        return False
    try:
        client.collection(collection).document(str(document_id)).set(payload, merge=True, timeout=3)
        return True
    except Exception:
        return False
