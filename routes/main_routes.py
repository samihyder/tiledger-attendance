from flask import Blueprint, render_template, redirect, url_for
from datetime import date
from auth import login_required, current_user
import db_manager as db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    from datetime import datetime
    now   = datetime.now()
    today = date.today().strftime('%Y-%m-%d')
    stats = db.get_today_stats(today)
    # Before 04:00 AM we're in the previous night's shift — show its punches
    if now.hour < 4:
        from datetime import timedelta
        prev = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        recent_punches = db.get_attendance_logs(date_from=prev, date_to=today)
    else:
        recent_punches = db.get_attendance_logs(date_from=today, date_to=today)
    sync_history   = db.get_sync_history(limit=5)
    today_display  = now.strftime('%A, %d %b %Y')
    return render_template(
        'dashboard.html',
        stats=stats,
        recent_punches=recent_punches[:10],
        sync_history=sync_history,
        today=today,
        today_display=today_display,
        user=current_user(),
    )
