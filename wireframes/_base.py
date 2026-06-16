"""Shared HTML fragments for TiLedger wireframes."""

LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" width="{w}" height="{h}">
  <circle cx="32" cy="32" r="32" fill="#0d6efd"/>
  <g stroke="#ffffff" stroke-linecap="round" fill="none">
    <path stroke-width="2.2" d="M19 38 C17 26 24 16 32 16 C40 16 47 26 45 38"/>
    <path stroke-width="2"   d="M22 39 C21 29 26 21 32 21 C38 21 43 29 42 39"/>
    <path stroke-width="1.8" d="M25 40 C24.5 32 27.5 26 32 26 C36.5 26 39.5 32 39 40"/>
    <path stroke-width="1.6" d="M28 41 C28 35 29.5 31 32 31 C34.5 31 36 35 36 41"/>
    <path stroke-width="1.4" d="M31 41 C31 38 31.5 36 32 36 C32.5 36 33 38 33 41"/>
  </g>
  <text x="32" y="56" font-family="'Arial Black',Arial,sans-serif" font-weight="900"
        font-size="11" fill="#ffffff" text-anchor="middle" letter-spacing="1">TL</text>
</svg>"""

BOOTSTRAP_CSS = "../static/vendor/bootstrap.min.css"
BOOTSTRAP_ICONS = "../static/vendor/bootstrap-icons.min.css"
BOOTSTRAP_JS  = "../static/vendor/bootstrap.bundle.min.js"

NAV_LINKS = [
    ("bi-speedometer2", "Dashboard",       "02-dashboard.html",        ["super_admin","manager","store","cashier"]),
    ("bi-fingerprint",  "Punch Screen",    "03-punch-screen.html",     ["super_admin","manager","store","cashier"]),
    ("bi-clock-history","Attendance Log",  "04-attendance-log.html",   ["super_admin","manager"]),
    ("bi-pencil-square","Manual Entry",    "05-manual-entry.html",     ["super_admin","store"]),
    ("bi-calendar3",    "Rosters",         "06-roster-list.html",      ["super_admin","manager"]),
    ("bi-clock",        "Shifts",          "08-shifts.html",           ["super_admin","manager"]),
    ("bi-people",       "Employees",       "09-employee-list.html",    ["super_admin","manager","system_admin"]),
    ("bi-cash-stack",   "Payroll",         "12-payroll-overview.html", ["super_admin"]),
    ("bi-hourglass-split","Overtime Queue","17-overtime-queue.html",   ["super_admin"]),
    ("bi-person-gear",  "Users",           "18-user-management.html",  ["super_admin"]),
    ("bi-calendar-check","Leave Requests", "19-leave-management.html", ["super_admin","manager"]),
    ("bi-key",          "Manual Grants",   "15-manual-grants.html",    ["super_admin"]),
    ("bi-trash3",       "Data Cleanup",    "16-data-cleanup.html",     ["super_admin"]),
    ("bi-cloud-upload", "Sync to ERP",     "14-sync-status.html",      ["super_admin"]),
]

WIREFRAME_BADGE = """
<div style="position:fixed;bottom:12px;right:12px;z-index:9999;
  background:#fff3cd;border:1px solid #ffc107;border-radius:8px;
  padding:6px 14px;font-size:11px;font-weight:600;color:#664d03;box-shadow:0 2px 8px rgba(0,0,0,.15)">
  ✏️ WIREFRAME — Not functional
</div>"""

def head(title, active_file=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title} — TiLedger Wireframe</title>
  <link href="{BOOTSTRAP_CSS}" rel="stylesheet">
  <link href="{BOOTSTRAP_ICONS}" rel="stylesheet">
  <style>
    body{{font-family:'Segoe UI',system-ui,sans-serif;background:#f8f9fa}}
    .sidebar .nav-link{{border-radius:8px;padding:8px 12px;margin-bottom:2px;transition:background .15s,color .15s}}
    .sidebar .nav-link:hover,.sidebar .nav-link.active{{background:rgba(255,255,255,.12);color:#fff!important}}
    .card{{border-radius:12px}}
    .card-header{{border-radius:12px 12px 0 0!important}}
    .table th{{font-size:.78rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:#6c757d}}
    .table td{{vertical-align:middle}}
    .badge{{font-weight:500}}
    .form-control:focus,.form-select:focus{{border-color:#0d6efd;box-shadow:0 0 0 3px rgba(13,110,253,.15)}}
    ::-webkit-scrollbar{{width:6px}}
    ::-webkit-scrollbar-thumb{{background:rgba(0,0,0,.2);border-radius:4px}}
    .wf-new{{border-left:3px solid #0d6efd!important}}
    .wf-gap{{border-left:3px solid #ffc107!important}}
  </style>
</head>
<body class="bg-light">
<div class="d-flex" style="min-height:100vh">
"""

def sidebar(active_file="", role="super_admin", username="Admin", fullname="Super Admin"):
    links_html = ""
    prev_group = None
    groups = {
        "bi-speedometer2": None,
        "bi-fingerprint": None,
        "bi-clock-history": "Attendance",
        "bi-pencil-square": "Attendance",
        "bi-calendar3": "Roster",
        "bi-clock": "Roster",
        "bi-people": "People",
        "bi-cash-stack": "Finance",
        "bi-hourglass-split": "Finance",
        "bi-person-gear": "Admin",
        "bi-calendar-check": "Admin",
        "bi-key": "Admin",
        "bi-trash3": "Admin",
        "bi-cloud-upload": "System",
    }
    for icon, label, href, roles in NAV_LINKS:
        if role not in roles:
            continue
        grp = groups.get(icon)
        if grp and grp != prev_group:
            links_html += f'<li class="nav-item mt-2"><div class="text-secondary px-2 small text-uppercase fw-semibold">{grp}</div></li>\n'
            prev_group = grp
        is_new = href in ("17-overtime-queue.html","18-user-management.html","19-leave-management.html")
        new_badge = ' <span class="badge bg-primary ms-1" style="font-size:.55rem">NEW</span>' if is_new else ""
        active_cls = "active text-white" if href == active_file else ""
        links_html += f'<li class="nav-item"><a class="nav-link text-white-50 {active_cls}" href="{href}"><i class="bi {icon} me-2"></i>{label}{new_badge}</a></li>\n'

    logo = LOGO_SVG.format(w=28, h=28)
    role_badge_color = {"super_admin":"primary","manager":"success","system_admin":"info","store":"warning","cashier":"secondary"}.get(role,"secondary")
    role_label = role.replace("_"," ").title()
    return f"""
  <nav class="sidebar bg-dark text-white d-flex flex-column p-0" style="width:240px;min-height:100vh;flex-shrink:0">
    <div class="px-3 py-4 border-bottom border-secondary">
      <div class="fw-bold fs-5 text-white d-flex align-items-center gap-2">
        {logo} TiLedger
      </div>
      <div class="text-secondary small mt-1">{fullname}</div>
      <span class="badge bg-{role_badge_color} mt-1">{role_label}</span>
    </div>
    <div class="flex-grow-1 py-2">
      <ul class="nav flex-column px-2">{links_html}</ul>
    </div>
    <div class="px-3 py-3 border-top border-secondary">
      <button class="btn btn-link nav-link text-white-50 small p-0">
        <i class="bi bi-box-arrow-left me-1"></i>Logout
      </button>
    </div>
  </nav>
"""

def main_wrap(content):
    return f'<div class="flex-grow-1 p-4">{content}</div>'

def foot():
    return f"""
  {WIREFRAME_BADGE}
</div>
<script src="{BOOTSTRAP_JS}"></script>
</body></html>"""

def page(title, content, active_file="", role="super_admin", fullname="Super Admin"):
    return head(title, active_file) + sidebar(active_file, role=role, fullname=fullname) + main_wrap(content) + foot()

def login_page(content):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Login — TiLedger Wireframe</title>
  <link href="{BOOTSTRAP_CSS}" rel="stylesheet">
  <link href="{BOOTSTRAP_ICONS}" rel="stylesheet">
  <style>body{{font-family:'Segoe UI',system-ui,sans-serif}}</style>
</head>
<body class="bg-light">
<div class="w-100">{content}</div>
{WIREFRAME_BADGE}
<script src="{BOOTSTRAP_JS}"></script>
</body></html>"""
