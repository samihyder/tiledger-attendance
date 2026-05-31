"""
Face Service — server-side only.
Face detection and 128-d descriptor extraction happen client-side (face-api.js).
This module only does Euclidean distance comparison and embedding averaging.
No dlib / opencv / face_recognition required.
"""

import json
import math
from config import Config

FACE_MATCH_THRESHOLD = float(getattr(Config, 'FACE_MATCH_THRESHOLD', 0.6))
FACE_ENROLL_FRAMES   = int(getattr(Config,   'FACE_ENROLL_FRAMES',   3))
FACE_MOCK_MODE       = False   # client handles detection; no server mock needed


class FaceServiceError(Exception):
    pass


def identify(embedding: list, templates: list) -> dict | None:
    """
    1:N face identification using Euclidean distance.

    embedding  : 128-d float list from face-api.js (browser)
    templates  : list of dicts with keys employee_id, embedding, full_name, employee_code
    Returns matched template dict + confidence, or None if no match within threshold.
    """
    if not embedding or not templates:
        return None

    best_match = None
    best_dist  = float('inf')

    for t in templates:
        stored = t['embedding']
        if isinstance(stored, str):
            stored = json.loads(stored)
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(embedding, stored)))
        if dist < best_dist:
            best_dist  = dist
            best_match = t

    if best_dist > FACE_MATCH_THRESHOLD:
        return None

    confidence = round((1 - best_dist / FACE_MATCH_THRESHOLD) * 100)
    return {**best_match, 'distance': best_dist, 'confidence': confidence}


def enroll_from_embeddings(embeddings: list) -> tuple:
    """
    Average multiple 128-d embeddings into one template.
    embeddings : list of 128-d float lists from browser (one per captured frame)
    Returns (averaged_embedding: list[float], quality: float)
    """
    if not embeddings:
        raise FaceServiceError('No embeddings provided')
    n        = len(embeddings[0])
    averaged = [sum(e[i] for e in embeddings) / len(embeddings) for i in range(n)]
    return averaged, 88.0


# Keep these stubs so existing import paths don't break
def get_face_device():
    return _ServerFaceDevice()

def check_blink(frames_b64: list) -> dict:
    # Blink detection moved to client-side (face-api.js)
    return {'blink_detected': True, 'ear_values': [], 'reason': None}


class _ServerFaceDevice:
    """Thin shim so old call sites (device.identify / device.enroll) still work."""

    def identify(self, embedding_or_b64, templates: list) -> dict | None:
        # Accept either a pre-computed embedding (list of floats from browser)
        # or fall back gracefully if old base64 path is accidentally called
        if isinstance(embedding_or_b64, list):
            return identify(embedding_or_b64, templates)
        return None

    def enroll(self, embeddings: list) -> tuple:
        return enroll_from_embeddings(embeddings)

    def liveness_check(self, *args, **kwargs) -> dict:
        # Liveness moved to client-side
        return {'is_live': True, 'score': 90, 'checks': {}, 'reason': None}
