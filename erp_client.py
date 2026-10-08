"""
ERP client — the attendance app keeps no database of its own (owner 2026-10-08,
kitchenosv2 docs/PAYROLL-PLAN.md). Staff, roster, punches and enrolled faces
live in the TiLedger ERP; this app signs in with the ERP login and calls the
ERP's /api/attendance-app/* endpoints with its app session.
"""
import json
import os
import urllib.error
import urllib.request

ERP_BASE_URL = os.environ.get('ERP_BASE_URL', 'https://tiledger.mutexsystems.co.uk').rstrip('/')


class ErpError(Exception):
    def __init__(self, message, status=500):
        super().__init__(message)
        self.status = status


def call(method: str, path: str, session_token: str | None = None, body: dict | None = None, timeout: int = 20):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    headers = {'Content-Type': 'application/json'}
    if session_token:
        headers['Authorization'] = f'Bearer {session_token}'
    req = urllib.request.Request(f'{ERP_BASE_URL}{path}', data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode('utf-8') or '{}')
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode('utf-8') or '{}')
        except Exception:
            payload = {}
        raise ErpError(payload.get('error') or f'TiLedger returned {e.code}', e.code)
    except urllib.error.URLError as e:
        raise ErpError(f'Cannot reach TiLedger: {e.reason}', 503)
    return payload.get('data', payload)
