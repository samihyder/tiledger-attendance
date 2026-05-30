from __future__ import annotations

from flask import Blueprint, render_template, redirect, url_for, flash
from datetime import date
from auth import login_required, current_user
import db_manager as db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    today = date.today().strftime('%Y-%m-%d')
    try:
        stats         = db.get_today_stats(today)
        recent_punches = db.get_attendance_logs(date_from=today, date_to=today)
        sync_history  = db.get_sync_history(limit=5)
    except Exception as e:
        flash(f'Database error: {e}', 'danger')
        stats          = {'total': 0, 'present': 0, 'late': 0, 'absent': 0}
        recent_punches = []
        sync_history   = []

    return render_template(
        'dashboard.html',
        stats=stats,
        recent_punches=recent_punches[:10],
        sync_history=sync_history,
        today=today,
        user=current_user(),
    )
