"""
Biometric Service — ZKTeco ZK9500 (and compatible) fingerprint scanner.

Architecture:
  - AbstractBiometricDevice: interface every device backend must implement.
  - ZKFingerDevice: wraps the ZKFinger C SDK via ctypes.
  - MockDevice: no-hardware simulation for development / testing.

Runtime selection: set BIOMETRIC_MOCK=true in environment to use MockDevice.

ZKFinger SDK notes:
  - Download ZKFinger SDK from ZKTeco's developer portal.
  - Place the .dll (Windows) or .so (Linux) in the project root or set ZK_SDK_PATH.
  - Functions used: ZKFP_Init, ZKFP_OpenDevice, ZKFP_CloseDevice,
    ZKFP_Terminate, ZKFP_AcquireFingerprint, ZKFP_Identify, ZKFP_Verify,
    ZKFP_DBFree, ZKFP_GetImageQuality.
"""

import ctypes
import os
import sys
import time
import random
from abc import ABC, abstractmethod
from config import Config

# ──────────────────────────────────────────────────────────────────────────────
# Return codes from ZKFinger SDK
# ──────────────────────────────────────────────────────────────────────────────
ZKFP_ERR_OK           =  0
ZKFP_ERR_INITLIB      = -1
ZKFP_ERR_OPENDEVICE   = -2
ZKFP_ERR_PARAM        = -3
ZKFP_ERR_MEMORY       = -4
ZKFP_ERR_NOTIMPLEMENT = -5
ZKFP_ERR_CAPTURE      = -6
ZKFP_ERR_EXTRACT      = -7
ZKFP_ERR_ABSIMILAR    = -8   # fingerprint too similar to another registered
ZKFP_ERR_DBFULL       = -9
ZKFP_ERR_IDENTIFY     = -10
ZKFP_ERR_TIMEOUT      = -24

IMG_WIDTH   = 328
IMG_HEIGHT  = 356
IMG_SIZE    = IMG_WIDTH * IMG_HEIGHT


class BiometricError(Exception):
    pass

# ──────────────────────────────────────────────────────────────────────────────
# Abstract interface
# ──────────────────────────────────────────────────────────────────────────────

class AbstractBiometricDevice(ABC):
    @abstractmethod
    def open(self) -> bool: ...

    @abstractmethod
    def close(self): ...

    @abstractmethod
    def capture_template(self, timeout_sec: int = 10) -> tuple[bytes, int]:
        """Capture a single fingerprint. Returns (template_bytes, quality_0_to_100)."""
        ...

    @abstractmethod
    def enroll(self, scans_required: int = 3) -> tuple[bytes, int]:
        """
        Perform multi-scan enrollment. Captures scans_required prints,
        merges them into a single high-quality template.
        Returns (merged_template_bytes, average_quality).
        """
        ...

    @abstractmethod
    def identify(self, templates: list[dict]) -> dict | None:
        """
        1:N identification. templates is a list of dicts:
          {'employee_id': int, 'finger_index': int, 'template_data': bytes}
        Returns the matched dict or None.
        """
        ...

    @abstractmethod
    def verify(self, stored_template: bytes, captured_template: bytes) -> tuple[bool, int]:
        """1:1 verification. Returns (matched: bool, score: int)."""
        ...

    @property
    @abstractmethod
    def is_open(self) -> bool: ...


# ──────────────────────────────────────────────────────────────────────────────
# ZKFinger SDK (production)
# ──────────────────────────────────────────────────────────────────────────────

class ZKFingerDevice(AbstractBiometricDevice):
    """
    Wraps ZKFinger SDK (libzkfp / zkfp.dll) via ctypes.
    Compatible with ZK9500, ZK9000, SLK20R, and most ZKTeco USB scanners.
    """

    def __init__(self, device_index: int = 0, sdk_path: str = ''):
        self._index = device_index
        self._handle = None
        self._db_handle = None
        self._lib = None
        self._sdk_path = sdk_path or self._find_sdk()

    def _find_sdk(self) -> str:
        candidates = ['libzkfp.so', 'libzkfp.so.1', 'zkfp.dll']
        for c in candidates:
            if os.path.exists(c):
                return c
        return 'libzkfp.so'

    def _load_lib(self):
        try:
            lib = ctypes.CDLL(self._sdk_path)
            # Declare return types
            lib.ZKFP_Init.restype = ctypes.c_int
            lib.ZKFP_OpenDevice.restype = ctypes.c_void_p
            lib.ZKFP_CloseDevice.restype = ctypes.c_int
            lib.ZKFP_Terminate.restype = ctypes.c_int
            lib.ZKFP_AcquireFingerprint.restype = ctypes.c_int
            lib.ZKFP_DBInit.restype = ctypes.c_void_p
            lib.ZKFP_DBFree.restype = ctypes.c_int
            lib.ZKFP_DBAdd.restype = ctypes.c_int
            lib.ZKFP_DBDel.restype = ctypes.c_int
            lib.ZKFP_DBClear.restype = ctypes.c_int
            lib.ZKFP_DBIdentify.restype = ctypes.c_int
            lib.ZKFP_DBMerge.restype = ctypes.c_int
            lib.ZKFP_Verify.restype = ctypes.c_int
            return lib
        except OSError as e:
            raise BiometricError(f'Failed to load ZKFinger SDK from {self._sdk_path}: {e}')

    def open(self) -> bool:
        self._lib = self._load_lib()
        ret = self._lib.ZKFP_Init()
        if ret != ZKFP_ERR_OK:
            raise BiometricError(f'ZKFP_Init failed: {ret}')
        handle = self._lib.ZKFP_OpenDevice(self._index)
        if not handle:
            self._lib.ZKFP_Terminate()
            raise BiometricError('ZKFP_OpenDevice failed — check device connection')
        self._handle = ctypes.c_void_p(handle)
        self._db_handle = ctypes.c_void_p(self._lib.ZKFP_DBInit())
        return True

    def close(self):
        if self._lib and self._handle:
            if self._db_handle:
                self._lib.ZKFP_DBFree(self._db_handle)
                self._db_handle = None
            self._lib.ZKFP_CloseDevice(self._handle)
            self._lib.ZKFP_Terminate()
            self._handle = None

    @property
    def is_open(self) -> bool:
        return self._handle is not None

    def capture_template(self, timeout_sec: int = 10) -> tuple[bytes, int]:
        img_buf   = (ctypes.c_ubyte * IMG_SIZE)()
        img_size  = ctypes.c_int(IMG_SIZE)
        tmpl_buf  = (ctypes.c_ubyte * Config.BIOMETRIC_TEMPLATE_SIZE)()
        tmpl_size = ctypes.c_int(Config.BIOMETRIC_TEMPLATE_SIZE)

        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            ret = self._lib.ZKFP_AcquireFingerprint(
                self._handle, img_buf, ctypes.byref(img_size),
                tmpl_buf, ctypes.byref(tmpl_size)
            )
            if ret == ZKFP_ERR_OK:
                template = bytes(tmpl_buf[:tmpl_size.value])
                # Estimate quality from image (simplified — use SDK quality API if available)
                quality = min(100, max(0, int(sum(img_buf) / IMG_SIZE)))
                return template, quality
            time.sleep(0.1)
        raise BiometricError('Fingerprint capture timed out — please place finger on scanner')

    def enroll(self, scans_required: int = 3) -> tuple[bytes, int]:
        templates = []
        qualities = []
        for i in range(scans_required):
            tmpl, quality = self.capture_template(timeout_sec=15)
            templates.append((ctypes.c_ubyte * len(tmpl))(*tmpl))
            qualities.append(quality)
            time.sleep(0.5)  # brief pause between scans

        merged_buf  = (ctypes.c_ubyte * Config.BIOMETRIC_TEMPLATE_SIZE)()
        merged_size = ctypes.c_int(Config.BIOMETRIC_TEMPLATE_SIZE)
        ret = self._lib.ZKFP_DBMerge(
            self._db_handle,
            templates[0], len(templates[0]),
            templates[1], len(templates[1]),
            templates[2] if len(templates) > 2 else templates[0],
            len(templates[2]) if len(templates) > 2 else len(templates[0]),
            merged_buf, ctypes.byref(merged_size)
        )
        if ret != ZKFP_ERR_OK:
            raise BiometricError(f'Template merge failed: {ret} — try enrollment again')

        merged = bytes(merged_buf[:merged_size.value])
        avg_quality = int(sum(qualities) / len(qualities))
        return merged, avg_quality

    def identify(self, templates: list[dict]) -> dict | None:
        db = ctypes.c_void_p(self._lib.ZKFP_DBInit())
        try:
            for t in templates:
                data = t['template_data']
                buf = (ctypes.c_ubyte * len(data))(*data)
                self._lib.ZKFP_DBAdd(db, t['employee_id'] * 10 + t['finger_index'], buf, len(data))

            img_buf   = (ctypes.c_ubyte * IMG_SIZE)()
            img_size  = ctypes.c_int(IMG_SIZE)
            tmpl_buf  = (ctypes.c_ubyte * Config.BIOMETRIC_TEMPLATE_SIZE)()
            tmpl_size = ctypes.c_int(Config.BIOMETRIC_TEMPLATE_SIZE)

            ret = self._lib.ZKFP_AcquireFingerprint(
                self._handle, img_buf, ctypes.byref(img_size),
                tmpl_buf, ctypes.byref(tmpl_size)
            )
            if ret != ZKFP_ERR_OK:
                return None

            uid  = ctypes.c_int(0)
            score = ctypes.c_int(0)
            ret = self._lib.ZKFP_DBIdentify(
                db, tmpl_buf, tmpl_size,
                ctypes.byref(uid), ctypes.byref(score)
            )
            if ret == ZKFP_ERR_OK and score.value >= Config.BIOMETRIC_IDENTIFY_THRESHOLD:
                raw_uid = uid.value
                emp_id = raw_uid // 10
                finger = raw_uid % 10
                for t in templates:
                    if t['employee_id'] == emp_id and t['finger_index'] == finger:
                        return {**t, 'score': score.value}
            return None
        finally:
            self._lib.ZKFP_DBFree(db)

    def verify(self, stored_template: bytes, captured_template: bytes) -> tuple[bool, int]:
        buf1 = (ctypes.c_ubyte * len(stored_template))(*stored_template)
        buf2 = (ctypes.c_ubyte * len(captured_template))(*captured_template)
        score = ctypes.c_int(0)
        ret = self._lib.ZKFP_Verify(
            self._db_handle, buf1, len(buf1), buf2, len(buf2), ctypes.byref(score)
        )
        matched = (ret == ZKFP_ERR_OK and score.value >= Config.BIOMETRIC_MATCH_THRESHOLD)
        return matched, score.value


# ──────────────────────────────────────────────────────────────────────────────
# Mock device (development / no-hardware testing)
# ──────────────────────────────────────────────────────────────────────────────

class MockDevice(AbstractBiometricDevice):
    """
    Simulates biometric operations. Generates deterministic fake templates.
    DO NOT use in production.
    """

    def __init__(self):
        self._open = False
        self._mock_employee_id = None  # set via set_mock_employee() for testing

    def set_mock_employee(self, employee_id: int):
        """Call this before identify() in tests to control which employee 'scans'."""
        self._mock_employee_id = employee_id

    def open(self) -> bool:
        self._open = True
        print('[MOCK] Biometric device opened (simulation mode)')
        return True

    def close(self):
        self._open = False

    @property
    def is_open(self) -> bool:
        return self._open

    def _fake_template(self, seed: int = None) -> bytes:
        rng = random.Random(seed)
        return bytes([rng.randint(0, 255) for _ in range(Config.BIOMETRIC_TEMPLATE_SIZE)])

    def capture_template(self, timeout_sec: int = 10) -> tuple[bytes, int]:
        time.sleep(0.3)   # simulate scan delay
        return self._fake_template(random.randint(0, 9999)), random.randint(75, 95)

    def enroll(self, scans_required: int = 3) -> tuple[bytes, int]:
        print(f'[MOCK] Enrollment: {scans_required} scans simulated')
        time.sleep(0.5 * scans_required)
        seed = random.randint(1000, 9999)
        return self._fake_template(seed), 88

    def identify(self, templates: list[dict]) -> dict | None:
        time.sleep(0.4)
        if self._mock_employee_id is not None:
            for t in templates:
                if t['employee_id'] == self._mock_employee_id:
                    return {**t, 'score': 82}
        if templates:
            return {**templates[0], 'score': 78}
        return None

    def verify(self, stored_template: bytes, captured_template: bytes) -> tuple[bool, int]:
        time.sleep(0.2)
        return True, 80


# ──────────────────────────────────────────────────────────────────────────────
# Singleton device instance
# ──────────────────────────────────────────────────────────────────────────────

_device: AbstractBiometricDevice | None = None

def get_device() -> AbstractBiometricDevice:
    global _device
    if _device is None:
        if Config.BIOMETRIC_MOCK_MODE:
            _device = MockDevice()
        else:
            _device = ZKFingerDevice(
                device_index=Config.BIOMETRIC_DEVICE_INDEX,
                sdk_path=Config.BIOMETRIC_SDK_PATH,
            )
    return _device

def open_device() -> bool:
    device = get_device()
    if not device.is_open:
        return device.open()
    return True

def close_device():
    global _device
    if _device and _device.is_open:
        _device.close()
    _device = None
