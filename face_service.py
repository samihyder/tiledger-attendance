"""
Face Recognition Service

Required libraries (install when hardware is ready):
    pip install face_recognition opencv-python numpy Pillow

face_recognition uses dlib's ResNet model to produce a 128-dimensional
numeric embedding per face.  NO image is stored — only the float array.

Anti-spoofing runs 4 passive checks + 1 active blink challenge.
Set FACE_MOCK=true in environment to run without camera or libraries.

Anti-spoofing checks:
  1. Texture / Laplacian variance  — blurry/too-sharp photos
  2. FFT frequency peak ratio       — screen displays (regular pixel grid)
  3. HSV saturation distribution    — printed photos (flat, wrong gamut)
  4. Specular highlight ratio        — abnormal paper/screen reflections
  5. Blink challenge (active)        — any static image cannot blink

Match threshold: Euclidean distance < 0.55 (adjustable in config.py).
"""

from __future__ import annotations  # keeps np.ndarray in type hints as strings — never evaluated at import

import os
import base64
import json
from io import BytesIO
from abc import ABC, abstractmethod

from config import Config

# numpy and Pillow are only needed when face recognition runs locally.
# On Vercel (FACE_MOCK_MODE=True) these are never imported.
if not Config.FACE_MOCK_MODE:
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        pass  # will fall through to mock mode
else:
    # Provide stubs so type annotations in this file don't crash at parse time
    import types as _types
    np  = _types.ModuleType('numpy')
    Image = None


# ──────────────────────────────────────────────────────────────────────────────
# Config additions (read from Config, fall back to defaults)
# ──────────────────────────────────────────────────────────────────────────────
FACE_MATCH_THRESHOLD  = float(getattr(Config, 'FACE_MATCH_THRESHOLD',  0.55))
FACE_SPOOF_MIN_SCORE  = int(getattr(Config,   'FACE_SPOOF_MIN_SCORE',  60))
FACE_ENROLL_FRAMES    = int(getattr(Config,   'FACE_ENROLL_FRAMES',    3))

# Mock mode: on Vercel/cloud (Config.FACE_MOCK_MODE=True), or if face_recognition
# isn't installed (no hardware), or if FACE_MOCK=true is explicitly set.
try:
    import face_recognition as _fr_check
    _FACE_LIB_AVAILABLE = True
except ImportError:
    _FACE_LIB_AVAILABLE = False

FACE_MOCK_MODE = Config.FACE_MOCK_MODE or not _FACE_LIB_AVAILABLE


class FaceServiceError(Exception):
    pass


# ──────────────────────────────────────────────────────────────────────────────
# Image helpers
# ──────────────────────────────────────────────────────────────────────────────

def b64_to_numpy(b64_string: str):
    """Convert base64 data-URL or raw base64 JPEG/PNG to numpy HxWx3 uint8."""
    if b64_string.startswith('data:'):
        b64_string = b64_string.split(',', 1)[1]
    img_bytes = base64.b64decode(b64_string)
    pil_img   = Image.open(BytesIO(img_bytes)).convert('RGB')
    return np.array(pil_img)       # H×W×3 RGB uint8


def numpy_to_bgr(rgb_array):
    """face_recognition works in RGB; OpenCV works in BGR."""
    import cv2
    return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)


# ──────────────────────────────────────────────────────────────────────────────
# Anti-spoofing (passive)
# ──────────────────────────────────────────────────────────────────────────────

def _liveness_checks(rgb_image, face_location=None):
    """
    Run 4 passive anti-spoofing checks on the face region.
    Returns dict: {is_live, score 0–100, checks {name: {pass, value}}, reason}
    """
    import cv2

    bgr = numpy_to_bgr(rgb_image)

    # Crop to face region if provided
    if face_location:
        top, right, bottom, left = face_location
        pad = 10
        h, w = bgr.shape[:2]
        top    = max(0, top    - pad)
        left   = max(0, left   - pad)
        bottom = min(h, bottom + pad)
        right  = min(w, right  + pad)
        roi = bgr[top:bottom, left:right]
    else:
        roi = bgr

    if roi.size == 0:
        return {'is_live': False, 'score': 0,
                'checks': {}, 'reason': 'Face region empty'}

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # ── Check 1: Texture / Laplacian variance ──────────────────────────────
    # Printed photos are often unnaturally sharp or flat.
    # Real faces: 80–5000. Too low → blurry photo. Too high → printed sharp text.
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    texture_ok = 80 < lap_var < 7000

    # ── Check 2: FFT frequency peak ratio (screen detection) ──────────────
    # Screens produce a regular pixel grid → strong repeating frequencies in FFT.
    f   = np.fft.fft2(gray.astype(np.float32))
    mag = np.abs(np.fft.fftshift(f))
    ch, cw = gray.shape[0] // 2, gray.shape[1] // 2
    mag[ch-8:ch+8, cw-8:cw+8] = 0          # suppress DC component
    peak_ratio = float(mag.max() / (mag.mean() + 1e-6))
    screen_ok  = peak_ratio < 60            # screens → ratio > 80

    # ── Check 3: HSV saturation distribution (printed photo detection) ────
    # Printed/scanned photos have flat, shifted saturation vs real skin.
    hsv      = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    sat      = hsv[:, :, 1].astype(float)
    sat_mean = float(sat.mean())
    sat_std  = float(sat.std())
    color_ok = sat_mean > 12 and sat_std > 6   # too uniform = printed

    # ── Check 4: Specular highlight ratio ─────────────────────────────────
    # Real skin has a small number of natural highlights.
    # Paper has many bright spots (shine); screens have large bright zones.
    _, thresh       = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY)
    highlight_ratio = float(thresh.sum()) / (255.0 * gray.size + 1e-6)
    highlight_ok    = 0.00005 < highlight_ratio < 0.08

    checks = {
        'texture':   {'pass': texture_ok,   'label': 'Texture',         'value': round(lap_var, 1)},
        'screen':    {'pass': screen_ok,     'label': 'Screen check',    'value': round(peak_ratio, 1)},
        'color':     {'pass': color_ok,      'label': 'Color analysis',  'value': round(sat_mean, 1)},
        'highlight': {'pass': highlight_ok,  'label': 'Skin highlights', 'value': round(highlight_ratio * 1000, 3)},
    }

    passed = sum(1 for c in checks.values() if c['pass'])
    score  = round(passed / len(checks) * 100)
    is_live = score >= FACE_SPOOF_MIN_SCORE

    return {
        'is_live': is_live,
        'score':   score,
        'checks':  checks,
        'reason':  None if is_live else 'Spoof detected — ensure you are in front of the camera with good lighting',
    }


def check_blink(frames_b64: list[str]) -> dict:
    """
    Active liveness: detect blink across a sequence of frames.
    frames_b64: list of 5–8 base64 frames captured ~150 ms apart.
    Returns {blink_detected, ear_values, reason}

    Eye Aspect Ratio (EAR) = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
    EAR < 0.25 → eye closed (blink)
    """
    import face_recognition
    import cv2

    ear_values = []
    blink_detected = False

    for b64 in frames_b64:
        try:
            rgb = b64_to_numpy(b64)
            landmarks_list = face_recognition.face_landmarks(rgb)
            if not landmarks_list:
                continue
            lm = landmarks_list[0]

            def ear(eye_points):
                p = np.array(eye_points)
                A = np.linalg.norm(p[1] - p[5])
                B = np.linalg.norm(p[2] - p[4])
                C = np.linalg.norm(p[0] - p[3])
                return float((A + B) / (2.0 * C + 1e-6))

            left_eye  = np.array(lm['left_eye'])
            right_eye = np.array(lm['right_eye'])
            avg_ear = (ear(left_eye) + ear(right_eye)) / 2
            ear_values.append(round(avg_ear, 3))
            if avg_ear < 0.25:
                blink_detected = True
        except Exception:
            continue

    return {
        'blink_detected': blink_detected,
        'ear_values': ear_values,
        'reason': None if blink_detected else 'No blink detected — please blink naturally when prompted',
    }


# ──────────────────────────────────────────────────────────────────────────────
# Abstract interface
# ──────────────────────────────────────────────────────────────────────────────

class AbstractFaceDevice(ABC):

    @abstractmethod
    def get_embedding(self, b64_image: str) -> tuple[list, tuple]:
        """
        Detect face, run anti-spoofing, return (embedding_128d, face_location).
        embedding is a plain Python list of 128 floats (JSON-serialisable).
        Raises FaceServiceError on failure.
        """
        ...

    @abstractmethod
    def enroll(self, frames_b64: list[str]) -> tuple[list, float, dict]:
        """
        Enroll from multiple frames. Returns (merged_embedding, quality, spoof_result).
        """
        ...

    @abstractmethod
    def identify(self, b64_image: str, templates: list[dict]) -> dict | None:
        """
        1:N identification. templates: [{employee_id, embedding_json}]
        Returns matched template dict + spoof_result, or None.
        """
        ...

    @abstractmethod
    def liveness_check(self, b64_image: str) -> dict:
        """Run passive anti-spoofing on a single frame."""
        ...


# ──────────────────────────────────────────────────────────────────────────────
# Production: face_recognition + OpenCV
# ──────────────────────────────────────────────────────────────────────────────

class FaceRecognitionDevice(AbstractFaceDevice):

    def _load_embedding(self, b64: str) -> tuple[np.ndarray, tuple | None, dict]:
        """Returns (encoding_array, face_location, spoof_result)."""
        import face_recognition

        rgb = b64_to_numpy(b64)

        locations = face_recognition.face_locations(rgb, model='hog')
        if not locations:
            raise FaceServiceError('No face detected — please look directly at the camera')
        if len(locations) > 1:
            raise FaceServiceError('Multiple faces detected — only one person should be in frame')

        loc   = locations[0]
        spoof = _liveness_checks(rgb, face_location=loc)
        if not spoof['is_live']:
            raise FaceServiceError(f'Anti-spoofing failed (score {spoof["score"]}%) — {spoof["reason"]}')

        encodings = face_recognition.face_encodings(rgb, known_face_locations=[loc])
        if not encodings:
            raise FaceServiceError('Face detected but encoding failed — try better lighting')

        return encodings[0], loc, spoof

    def get_embedding(self, b64_image: str) -> tuple[list, tuple]:
        enc, loc, _ = self._load_embedding(b64_image)
        return enc.tolist(), loc

    def enroll(self, frames_b64: list[str]) -> tuple[list, float, dict]:
        """Average embeddings across frames for higher quality template."""
        encodings = []
        last_spoof = {}
        for b64 in frames_b64:
            try:
                enc, _, spoof = self._load_embedding(b64)
                encodings.append(enc)
                last_spoof = spoof
            except FaceServiceError:
                continue

        if not encodings:
            raise FaceServiceError('Could not extract any valid face from the provided frames')

        merged  = np.mean(encodings, axis=0)
        quality = round(float(last_spoof.get('score', 75)), 1)
        return merged.tolist(), quality, last_spoof

    def identify(self, b64_image: str, templates: list[dict]) -> dict | None:
        import face_recognition

        rgb = b64_to_numpy(b64_image)
        locations = face_recognition.face_locations(rgb, model='hog')
        if not locations:
            return None

        loc   = locations[0]
        spoof = _liveness_checks(rgb, face_location=loc)
        if not spoof['is_live']:
            raise FaceServiceError(f'Spoof detected ({spoof["score"]}%) — {spoof["reason"]}')

        encodings = face_recognition.face_encodings(rgb, known_face_locations=[loc])
        if not encodings:
            return None

        captured = encodings[0]
        known    = [np.array(json.loads(t['embedding'])) for t in templates]
        distances = face_recognition.face_distance(known, captured)

        best_idx  = int(np.argmin(distances))
        best_dist = float(distances[best_idx])

        if best_dist > FACE_MATCH_THRESHOLD:
            return None

        confidence = round((1 - best_dist / FACE_MATCH_THRESHOLD) * 100)
        return {**templates[best_idx], 'distance': best_dist, 'confidence': confidence, 'spoof': spoof}

    def liveness_check(self, b64_image: str) -> dict:
        rgb = b64_to_numpy(b64_image)
        import face_recognition
        locs = face_recognition.face_locations(rgb)
        loc  = locs[0] if locs else None
        return _liveness_checks(rgb, face_location=loc)


# ──────────────────────────────────────────────────────────────────────────────
# Mock device (dev / no-library testing)
# ──────────────────────────────────────────────────────────────────────────────

class MockFaceDevice(AbstractFaceDevice):
    """
    Simulates face recognition without libraries or camera.
    embeddings are deterministic float arrays based on employee_id.
    NEVER use in production.
    """

    def __init__(self):
        self._mock_employee_id: int | None = None

    def set_mock_employee(self, employee_id: int):
        self._mock_employee_id = employee_id

    def _mock_embedding(self, seed: int) -> list:
        rng = np.random.default_rng(seed)
        v = rng.uniform(-1, 1, 128)
        return (v / np.linalg.norm(v)).tolist()

    def _mock_spoof(self) -> dict:
        return {
            'is_live': True, 'score': 90,
            'checks': {
                'texture':   {'pass': True, 'label': 'Texture',        'value': 450.0},
                'screen':    {'pass': True, 'label': 'Screen check',   'value': 12.3},
                'color':     {'pass': True, 'label': 'Color analysis', 'value': 35.0},
                'highlight': {'pass': True, 'label': 'Skin highlights','value': 0.012},
            },
            'reason': None,
        }

    def get_embedding(self, b64_image: str) -> tuple[list, tuple]:
        seed = self._mock_employee_id or 42
        return self._mock_embedding(seed), (50, 200, 200, 50)

    def enroll(self, frames_b64: list[str]) -> tuple[list, float, dict]:
        seed = self._mock_employee_id or 42
        return self._mock_embedding(seed), 88.0, self._mock_spoof()

    def identify(self, b64_image: str, templates: list[dict]) -> dict | None:
        import time; time.sleep(0.3)
        if not templates:
            return None
        target_id = self._mock_employee_id
        for t in templates:
            if target_id and t['employee_id'] == target_id:
                return {**t, 'distance': 0.3, 'confidence': 85, 'spoof': self._mock_spoof()}
        t = templates[0]
        return {**t, 'distance': 0.35, 'confidence': 78, 'spoof': self._mock_spoof()}

    def liveness_check(self, b64_image: str) -> dict:
        return self._mock_spoof()


# ──────────────────────────────────────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────────────────────────────────────

_face_device: AbstractFaceDevice | None = None

def get_face_device() -> AbstractFaceDevice:
    global _face_device
    if _face_device is None:
        _face_device = MockFaceDevice() if FACE_MOCK_MODE else FaceRecognitionDevice()
    return _face_device
