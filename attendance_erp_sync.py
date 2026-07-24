"""
Event-triggered attendance sync to the kitchenosv2 ERP.

Fires once an employee's shift completes (punch-out recorded), POSTing that
employee's day's attendance to the ERP's HMAC-signed webhook
(/api/attendance/webhook) instead of relying on the older manual/scheduled
sync_service.py mirror. Best-effort: a failure here must never block or
fail the employee's actual punch — it's logged and swallowed.
"""

import hmac
import hashlib
import json
import logging
import urllib.request
import urllib.error

import db_manager as db
from config import Config

logger = logging.getLogger(__name__)


def _sign(body: bytes, secret: str) -> str:
    return 'sha256=' + hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()


def _build_record(employee_id: int, shift_date: str) -> dict | None:
    """Aggregates this employee's punches for the shift into one attendance_daily record."""
    employee = db.get_employee(employee_id)
    if not employee:
        return None

    punches = db.get_shift_punches(employee_id, shift_date)
    ins = sorted([p for p in punches if p['punch_type'] == 'in'], key=lambda p: p['punch_time'])
    outs = sorted([p for p in punches if p['punch_type'] == 'out'], key=lambda p: p['punch_time'])
    if not ins or not outs:
        return None

    first_in = ins[0]
    last_out = outs[-1]
    return {
        'employee_code': employee['employee_code'],
        'full_name': employee['full_name'],
        'punch_in': first_in['punch_time'][11:16],
        'punch_out': last_out['punch_time'][11:16],
        'minutes_late': int(first_in.get('minutes_late') or 0),
        'punch_source': last_out.get('punch_source') or 'biometric',
    }


def sync_shift_close(employee_id: int, shift_date: str) -> None:
    """Best-effort push of one employee's completed shift to the ERP. Never raises."""
    try:
        if not (Config.ERP_WEBHOOK_URL and Config.ATTENDANCE_WEBHOOK_SECRET and Config.ERP_ENTITY_ID):
            logger.info('Attendance ERP sync skipped: ERP_WEBHOOK_URL/ATTENDANCE_WEBHOOK_SECRET/ERP_ENTITY_ID not configured')
            return

        record = _build_record(employee_id, shift_date)
        if not record:
            logger.warning('Attendance ERP sync skipped: incomplete in/out punches for employee %s on %s', employee_id, shift_date)
            return

        payload = {
            'entity_id': Config.ERP_ENTITY_ID,
            'date': shift_date,
            'records': [record],
        }
        body = json.dumps(payload).encode('utf-8')
        signature = _sign(body, Config.ATTENDANCE_WEBHOOK_SECRET)

        req = urllib.request.Request(
            Config.ERP_WEBHOOK_URL,
            data=body,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'x-attendance-signature': signature,
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status >= 300:
                logger.error('Attendance ERP sync failed: HTTP %s for employee %s on %s', resp.status, employee_id, shift_date)
    except urllib.error.HTTPError as e:
        logger.error('Attendance ERP sync failed: HTTP %s %s for employee %s on %s', e.code, e.read(), employee_id, shift_date)
    except Exception as e:
        logger.error('Attendance ERP sync failed for employee %s on %s: %s', employee_id, shift_date, e)
