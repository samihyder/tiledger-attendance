"""
Face Service — server-side only.
Face detection and 128-d descriptor extraction happen client-side (face-api.js).
This module handles Euclidean distance comparison, embedding averaging, and
second-best-match ratio check to reduce false positives.
"""

import json
import math
from config import Config

FACE_MATCH_THRESHOLD  = float(getattr(Config, 'FACE_MATCH_THRESHOLD', 0.55))
FACE_ENROLL_FRAMES    = int(getattr(Config,   'FACE_ENROLL_FRAMES',   5))
FACE_MOCK_MODE        = False   # client handles detection; no server mock needed

# Lowe-style ratio: best distance must be this much smaller than second-best.
# Prevents ambiguous matches when two employees look similar.
# 0.80 means best must be at least 20% better than runner-up.
_RATIO_THRESHOLD = 0.80


class FaceServiceError(Exception):
    pass


def _euclidean(a: list, b: list) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _load_embedding(stored) -> list:
    if isinstance(stored, str):
        return json.loads(stored)
    return list(stored)


def average_embeddings(embeddings: list) -> list:
    """Average multiple 128-d embeddings into one."""
    if not embeddings:
        raise FaceServiceError('No embeddings provided')
    n = len(embeddings[0])
    return [sum(e[i] for e in embeddings) / len(embeddings) for i in range(n)]


def identify(embedding: list, templates: list) -> dict | None:
    """
    1:N face identification using Euclidean distance + second-best ratio check.

    embedding  : 128-d float list from browser (may be a single frame or
                 an average of multiple frames — prefer the latter for accuracy)
    templates  : list of dicts with keys employee_id, embedding, full_name, employee_code

    Returns matched template dict (+ confidence, distance) or None.

    Two-stage rejection:
      1. Absolute threshold: distance must be <= FACE_MATCH_THRESHOLD
      2. Ratio check: best distance / second-best distance must be < _RATIO_THRESHOLD
         (skipped when only one template exists)
    """
    if not embedding or len(embedding) != 128:
        return None
    if not templates:
        return None

    distances = []
    for t in templates:
        stored = _load_embedding(t['embedding'])
        if len(stored) != 128:
            continue
        dist = _euclidean(embedding, stored)
        distances.append((dist, t))

    if not distances:
        return None

    distances.sort(key=lambda x: x[0])
    best_dist, best_t = distances[0]

    # 1. Absolute threshold
    if best_dist > FACE_MATCH_THRESHOLD:
        return None

    # 2. Ratio check (only meaningful when there are ≥2 templates)
    if len(distances) >= 2:
        second_dist = distances[1][0]
        if second_dist > 0 and (best_dist / second_dist) >= _RATIO_THRESHOLD:
            return None  # too ambiguous — best match is not clearly better

    # Confidence: 0% at threshold, 100% at distance=0
    confidence = round(max(0, (1 - best_dist / FACE_MATCH_THRESHOLD) * 100))

    return {**best_t, 'distance': best_dist, 'confidence': confidence}


def identify_multi(embeddings: list, templates: list) -> dict | None:
    """
    Identify using multiple embeddings from the browser (e.g. 3 frames).
    Averages the embeddings first for better accuracy, then calls identify().
    Falls back to single-embedding identify() if only one frame provided.
    """
    if not embeddings:
        return None
    if len(embeddings) == 1:
        return identify(embeddings[0], templates)
    avg = average_embeddings(embeddings)
    return identify(avg, templates)


def enroll_from_embeddings(embeddings: list) -> tuple:
    """
    Average multiple 128-d embeddings into one template.
    embeddings : list of 128-d float lists from browser (one per captured frame)
    Returns (averaged_embedding: list[float], quality: float)
    """
    if not embeddings:
        raise FaceServiceError('No embeddings provided')
    avg = average_embeddings(embeddings)
    # Quality estimate: higher if embeddings are consistent (low variance)
    if len(embeddings) > 1:
        variances = [
            sum((e[i] - avg[i]) ** 2 for e in embeddings) / len(embeddings)
            for i in range(len(avg))
        ]
        mean_var = sum(variances) / len(variances)
        # Lower variance → higher quality. Clamp to [70, 98].
        quality = round(max(70.0, min(98.0, 98.0 - mean_var * 5000)))
    else:
        quality = 80.0
    return avg, quality


# ── Compatibility shims ───────────────────────────────────────────────────────

def get_face_device():
    return _ServerFaceDevice()

def check_blink(frames_b64: list) -> dict:
    return {'blink_detected': True, 'ear_values': [], 'reason': None}


class _ServerFaceDevice:
    """Thin shim so old call sites (device.identify / device.enroll) still work."""

    def identify(self, embedding_or_b64, templates: list) -> dict | None:
        if isinstance(embedding_or_b64, list):
            return identify(embedding_or_b64, templates)
        return None

    def enroll(self, embeddings: list) -> tuple:
        return enroll_from_embeddings(embeddings)

    def liveness_check(self, *args, **kwargs) -> dict:
        return {'is_live': True, 'score': 90, 'checks': {}, 'reason': None}
