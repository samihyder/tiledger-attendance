"""Generate all TiLedger wireframe HTML files."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _base import page, login_page, LOGO_SVG

OUT = os.path.dirname(__file__)

def w(filename, html):
    path = os.path.join(OUT, filename)
    with open(path, 'w') as f:
        f.write(html)
    print(f"  ✓ {filename}")

# ─────────────────────────────────────────────────────────────────────────────
# 01 — LOGIN
# ─────────────────────────────────────────────────────────────────────────────
logo_lg = LOGO_SVG.format(w=56, h=56)
w("01-login.html", login_page(f"""
<div class="min-vh-100 d-flex align-items-center justify-content-center" style="background:linear-gradient(135deg,#0d6efd 0%,#0a58ca 100%)">
  <div class="card border-0 shadow-lg p-4" style="width:380px;border-radius:16px">
    <div class="text-center mb-4">
      {logo_lg}
      <h4 class="fw-bold mt-3 mb-0">TiLedger Attendance</h4>
      <div class="text-muted small">Sign in to continue</div>
    </div>
    <div class="mb-3">
      <label class="form-label fw-semibold">Username</label>
      <div class="input-group">
        <span class="input-group-text bg-light border-end-0"><i class="bi bi-person text-muted"></i></span>
        <input type="text" class="form-control border-start-0 ps-0" placeholder="admin" value="admin">
      </div>
    </div>
    <div class="mb-4">
      <label class="form-label fw-semibold">Password</label>
      <div class="input-group">
        <span class="input-group-text bg-light border-end-0"><i class="bi bi-lock text-muted"></i></span>
        <input type="password" class="form-control border-start-0 ps-0" placeholder="••••••••" value="admin@2026">
        <button class="btn btn-outline-secondary border-start-0"><i class="bi bi-eye"></i></button>
      </div>
    </div>
    <button class="btn btn-primary w-100 fw-semibold py-2">
      <i class="bi bi-box-arrow-in-right me-2"></i>Sign In
    </button>
    <div class="text-center mt-3 text-muted small">
      <i class="bi bi-shield-lock me-1"></i>Session expires at 04:00 AM daily
    </div>
  </div>
</div>
"""))

# ─────────────────────────────────────────────────────────────────────────────
# 02 — DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
w("02-dashboard.html", page("Dashboard", """
<div class="d-flex justify-content-between align-items-center mb-4">
  <div>
    <h4 class="fw-bold mb-0">Dashboard</h4>
    <div class="text-muted small">Monday, 16 June 2026</div>
  </div>
  <span class="badge bg-success fs-6 px-3 py-2"><i class="bi bi-circle-fill me-1" style="font-size:.5rem"></i>Live</span>
</div>

<!-- Stat cards -->
<div class="row g-3 mb-4">
  <div class="col-md-3">
    <div class="card border-0 shadow-sm text-center py-3">
      <div class="fs-1 fw-bold text-success">23</div>
      <div class="text-muted small">Present Today</div>
      <div class="text-muted" style="font-size:.7rem">of 30 scheduled</div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card border-0 shadow-sm text-center py-3">
      <div class="fs-1 fw-bold text-danger">7</div>
      <div class="text-muted small">Absent Today</div>
      <div class="text-muted" style="font-size:.7rem">roster assigned</div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card border-0 shadow-sm text-center py-3">
      <div class="fs-1 fw-bold text-warning">4</div>
      <div class="text-muted small">Late Arrivals</div>
      <div class="text-muted" style="font-size:.7rem">past grace period</div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card border-0 shadow-sm text-center py-3 border-warning border-2">
      <div class="fs-1 fw-bold text-warning">3</div>
      <div class="text-muted small">OT Pending</div>
      <div class="text-muted" style="font-size:.7rem"><a href="17-overtime-queue.html" class="text-warning">Review →</a></div>
    </div>
  </div>
</div>

<!-- Recent punches + Sync history -->
<div class="row g-3">
  <div class="col-md-7">
    <div class="card border-0 shadow-sm">
      <div class="card-header bg-white border-0 pt-3 pb-2 d-flex justify-content-between">
        <h6 class="fw-bold mb-0">Recent Punches</h6>
        <a href="04-attendance-log.html" class="btn btn-outline-secondary btn-sm">View All</a>
      </div>
      <div class="card-body p-0">
        <table class="table table-sm mb-0">
          <thead><tr><th>Employee</th><th>Time</th><th>Type</th><th>Source</th></tr></thead>
          <tbody>
            <tr><td><div class="fw-semibold">Ali Hassan</div><div class="text-muted small">EMP-001</div></td><td>09:02</td><td><span class="badge bg-success-subtle text-success">IN</span></td><td><i class="bi bi-fingerprint text-primary"></i></td></tr>
            <tr><td><div class="fw-semibold">Sara Ahmed</div><div class="text-muted small">EMP-002</div></td><td>09:07</td><td><span class="badge bg-success-subtle text-success">IN</span></td><td><i class="bi bi-person-bounding-box text-info"></i></td></tr>
            <tr><td><div class="fw-semibold">Bilal Khan</div><div class="text-muted small">EMP-005</div></td><td>09:18 <span class="badge bg-warning text-dark ms-1" style="font-size:.6rem">+8 min</span></td><td><span class="badge bg-success-subtle text-success">IN</span></td><td><i class="bi bi-fingerprint text-primary"></i></td></tr>
            <tr><td><div class="fw-semibold">Fatima Malik</div><div class="text-muted small">EMP-008</div></td><td>09:22</td><td><span class="badge bg-success-subtle text-success">IN</span></td><td><i class="bi bi-pencil text-secondary"></i></td></tr>
            <tr><td><div class="fw-semibold">Omar Siddiqui</div><div class="text-muted small">EMP-003</div></td><td>18:05</td><td><span class="badge bg-danger-subtle text-danger">OUT</span></td><td><i class="bi bi-fingerprint text-primary"></i></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
  <div class="col-md-5">
    <div class="card border-0 shadow-sm mb-3">
      <div class="card-header bg-white border-0 pt-3 pb-2">
        <h6 class="fw-bold mb-0">Absent Today</h6>
      </div>
      <div class="card-body p-0">
        <table class="table table-sm mb-0">
          <tbody>
            <tr><td><div class="fw-semibold">Kamran Raza</div><div class="text-muted small">EMP-010 · Sales</div></td><td class="text-end"><span class="badge bg-danger">Absent</span></td></tr>
            <tr><td><div class="fw-semibold">Nadia Iqbal</div><div class="text-muted small">EMP-014 · HR</div></td><td class="text-end"><span class="badge bg-danger">Absent</span></td></tr>
            <tr><td><div class="fw-semibold">Asad Mirza</div><div class="text-muted small">EMP-017 · Ops</div></td><td class="text-end"><span class="badge bg-danger">Absent</span></td></tr>
          </tbody>
        </table>
      </div>
    </div>
    <div class="card border-0 shadow-sm">
      <div class="card-header bg-white border-0 pt-3 pb-2">
        <h6 class="fw-bold mb-0">Sync History</h6>
      </div>
      <div class="card-body p-0">
        <table class="table table-sm mb-0">
          <tbody>
            <tr><td class="text-muted small">Today 04:02</td><td><span class="badge bg-success">Success</span></td><td class="text-muted small">142 records</td></tr>
            <tr><td class="text-muted small">Yesterday</td><td><span class="badge bg-success">Success</span></td><td class="text-muted small">138 records</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>
""", "02-dashboard.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 03 — PUNCH SCREEN
# ─────────────────────────────────────────────────────────────────────────────
w("03-punch-screen.html", page("Punch Screen", """
<div class="d-flex justify-content-between align-items-center mb-3">
  <h4 class="fw-bold mb-0">Punch Screen</h4>
  <button class="btn btn-outline-warning btn-sm"><i class="bi bi-unlock me-1"></i>Enable Manual Mode</button>
</div>
<div class="row g-3">
  <!-- Terminal -->
  <div class="col-md-5">
    <div class="card border-0 shadow-sm p-4">
      <div class="text-center mb-3">
        <div class="display-4 fw-bold text-dark">09:24</div>
        <div class="text-muted small">Monday, 16 June 2026</div>
      </div>
      <!-- Mode tabs -->
      <ul class="nav nav-pills nav-fill mb-4">
        <li class="nav-item"><button class="nav-link active"><i class="bi bi-fingerprint me-1"></i>Fingerprint</button></li>
        <li class="nav-item"><button class="nav-link"><i class="bi bi-person-bounding-box me-1"></i>Face</button></li>
      </ul>
      <!-- Scanner area -->
      <div class="text-center py-4 mb-3" style="border:2px dashed #dee2e6;border-radius:12px;background:#f8f9fa">
        <i class="bi bi-fingerprint" style="font-size:5rem;color:#0d6efd;opacity:.7"></i>
        <div class="text-muted small mt-2 fw-semibold">Place finger on scanner</div>
        <div class="text-muted" style="font-size:.75rem">ZKTeco ZK9500 ready</div>
      </div>
      <!-- Status -->
      <div class="alert alert-success py-2 small d-flex align-items-center mb-0">
        <i class="bi bi-check-circle-fill me-2"></i>
        <div><strong>Ali Hassan</strong> punched <strong>IN</strong> at 09:02 AM</div>
      </div>
    </div>
  </div>
  <!-- Face panel (inactive) -->
  <div class="col-md-4">
    <div class="card border-0 shadow-sm p-3">
      <h6 class="fw-bold mb-3"><i class="bi bi-person-bounding-box me-2 text-info"></i>Face Recognition</h6>
      <div class="ratio ratio-4x3 mb-3 rounded overflow-hidden bg-dark d-flex align-items-center justify-content-center" style="border-radius:8px!important">
        <div class="d-flex flex-column align-items-center justify-content-center text-white opacity-50">
          <i class="bi bi-camera-video fs-1"></i>
          <div class="small mt-2">Camera inactive</div>
        </div>
      </div>
      <button class="btn btn-info w-100 text-white"><i class="bi bi-camera-video me-2"></i>Start Camera</button>
      <div class="text-muted small text-center mt-2">Liveness blink detection enabled</div>
    </div>
  </div>
  <!-- Recent punches -->
  <div class="col-md-3">
    <div class="card border-0 shadow-sm">
      <div class="card-header bg-white border-0 pt-3 pb-2">
        <h6 class="fw-bold mb-0 small">Recent Punches</h6>
      </div>
      <div class="card-body p-0">
        <table class="table table-sm mb-0">
          <tbody>
            <tr><td class="small"><strong>Ali Hassan</strong><br><span class="text-muted">09:02 IN</span></td><td><i class="bi bi-fingerprint text-primary"></i></td></tr>
            <tr><td class="small"><strong>Sara Ahmed</strong><br><span class="text-muted">09:07 IN</span></td><td><i class="bi bi-person-bounding-box text-info"></i></td></tr>
            <tr><td class="small"><strong>Bilal Khan</strong><br><span class="text-muted">09:18 IN</span></td><td><i class="bi bi-fingerprint text-primary"></i></td></tr>
            <tr><td class="small"><strong>Fatima Malik</strong><br><span class="text-muted">09:22 IN</span></td><td><i class="bi bi-pencil text-secondary"></i></td></tr>
            <tr><td class="small"><strong>Omar Siddiqui</strong><br><span class="text-muted">18:05 OUT</span></td><td><i class="bi bi-fingerprint text-primary"></i></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>
""", "03-punch-screen.html", role="store", fullname="Store Manager"))

# ─────────────────────────────────────────────────────────────────────────────
# 04 — ATTENDANCE LOG
# ─────────────────────────────────────────────────────────────────────────────
w("04-attendance-log.html", page("Attendance Log", """
<div class="d-flex justify-content-between align-items-center mb-4">
  <div>
    <h4 class="fw-bold mb-0">Attendance Log</h4>
    <p class="text-muted small mb-0">1,240 punch records — page 1 of 25</p>
  </div>
  <a href="05-manual-entry.html" class="btn btn-outline-warning btn-sm"><i class="bi bi-pencil-square me-1"></i>Backdated Correction</a>
</div>
<!-- Filters -->
<div class="card border-0 shadow-sm mb-4">
  <div class="card-body py-3">
    <form class="row g-2 align-items-end">
      <div class="col-md-3"><label class="form-label small fw-semibold mb-1">From</label><input type="date" class="form-control form-control-sm" value="2026-06-01"></div>
      <div class="col-md-3"><label class="form-label small fw-semibold mb-1">To</label><input type="date" class="form-control form-control-sm" value="2026-06-16"></div>
      <div class="col-md-4"><label class="form-label small fw-semibold mb-1">Employee</label>
        <select class="form-select form-select-sm"><option>All Employees</option><option>Ali Hassan</option><option>Sara Ahmed</option></select>
      </div>
      <div class="col-md-2"><button class="btn btn-primary btn-sm w-100"><i class="bi bi-funnel me-1"></i>Filter</button></div>
    </form>
  </div>
</div>
<!-- Table -->
<div class="card border-0 shadow-sm">
  <div class="card-body p-0">
    <table class="table mb-0">
      <thead><tr><th>Employee</th><th>Date</th><th>Time</th><th>Type</th><th>Source</th><th>Late (min)</th><th>Shift</th><th></th></tr></thead>
      <tbody>
        <tr><td><div class="fw-semibold">Ali Hassan</div><div class="text-muted small">EMP-001</div></td><td class="small">Mon 16 Jun</td><td class="fw-semibold">09:02</td><td><span class="badge bg-success">IN</span></td><td><i class="bi bi-fingerprint text-primary" title="Biometric"></i></td><td><span class="text-muted">—</span></td><td class="small text-muted">Morning</td><td><button class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></button></td></tr>
        <tr><td><div class="fw-semibold">Sara Ahmed</div><div class="text-muted small">EMP-002</div></td><td class="small">Mon 16 Jun</td><td class="fw-semibold">09:07</td><td><span class="badge bg-success">IN</span></td><td><i class="bi bi-person-bounding-box text-info" title="Face"></i></td><td><span class="text-muted">—</span></td><td class="small text-muted">Morning</td><td><button class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></button></td></tr>
        <tr class="table-warning"><td><div class="fw-semibold">Bilal Khan</div><div class="text-muted small">EMP-005</div></td><td class="small">Mon 16 Jun</td><td class="fw-semibold">09:18</td><td><span class="badge bg-success">IN</span></td><td><i class="bi bi-fingerprint text-primary"></i></td><td><span class="badge bg-warning text-dark">8 min</span></td><td class="small text-muted">Morning</td><td><button class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></button></td></tr>
        <tr><td><div class="fw-semibold">Fatima Malik</div><div class="text-muted small">EMP-008</div></td><td class="small">Mon 16 Jun</td><td class="fw-semibold">09:22</td><td><span class="badge bg-success">IN</span></td><td><i class="bi bi-pencil text-secondary" title="Manual"></i></td><td><span class="text-muted">—</span></td><td class="small text-muted">Morning</td><td><button class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></button></td></tr>
        <tr><td><div class="fw-semibold">Omar Siddiqui</div><div class="text-muted small">EMP-003</div></td><td class="small">Mon 16 Jun</td><td class="fw-semibold">18:05</td><td><span class="badge bg-danger">OUT</span></td><td><i class="bi bi-fingerprint text-primary"></i></td><td><span class="text-muted">—</span></td><td class="small text-muted">Morning</td><td><button class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></button></td></tr>
        <tr class="table-info"><td><div class="fw-semibold">Omar Siddiqui</div><div class="text-muted small">EMP-003</div></td><td class="small">Mon 16 Jun</td><td class="fw-semibold">19:42 <span class="badge bg-info text-dark ms-1" style="font-size:.6rem">+97 min OT</span></td><td><span class="badge bg-danger">OUT</span></td><td><i class="bi bi-fingerprint text-primary"></i></td><td><span class="text-muted">—</span></td><td class="small text-muted">Morning</td><td><button class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></button></td></tr>
      </tbody>
    </table>
  </div>
</div>
<!-- Pagination -->
<nav class="mt-3">
  <ul class="pagination pagination-sm justify-content-center mb-0">
    <li class="page-item disabled"><a class="page-link"><i class="bi bi-chevron-left"></i></a></li>
    <li class="page-item active"><a class="page-link">1</a></li>
    <li class="page-item"><a class="page-link">2</a></li>
    <li class="page-item"><a class="page-link">3</a></li>
    <li class="page-item disabled"><span class="page-link">…</span></li>
    <li class="page-item"><a class="page-link">25</a></li>
    <li class="page-item"><a class="page-link"><i class="bi bi-chevron-right"></i></a></li>
  </ul>
</nav>
""", "04-attendance-log.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 05 — MANUAL ENTRY
# ─────────────────────────────────────────────────────────────────────────────
w("05-manual-entry.html", page("Manual Entry", """
<h4 class="fw-bold mb-1">Manual Attendance Entry</h4>
<p class="text-muted small mb-4">Backdated or corrected punch records — Super Admin only</p>
<div class="row justify-content-center">
  <div class="col-md-6">
    <div class="card border-0 shadow-sm p-4">
      <div class="mb-3">
        <label class="form-label fw-semibold">Employee</label>
        <select class="form-select"><option>— Select Employee —</option><option>Ali Hassan (EMP-001)</option><option>Sara Ahmed (EMP-002)</option><option>Bilal Khan (EMP-005)</option></select>
      </div>
      <div class="row g-2 mb-3">
        <div class="col"><label class="form-label fw-semibold">Date</label><input type="date" class="form-control" value="2026-06-16"></div>
        <div class="col"><label class="form-label fw-semibold">Time</label><input type="time" class="form-control" value="09:00"></div>
      </div>
      <div class="mb-3">
        <label class="form-label fw-semibold">Punch Type</label>
        <div class="d-flex gap-3">
          <div class="form-check"><input class="form-check-input" type="radio" name="ptype" checked><label class="form-check-label">IN</label></div>
          <div class="form-check"><input class="form-check-input" type="radio" name="ptype"><label class="form-check-label">OUT</label></div>
        </div>
      </div>
      <div class="mb-4">
        <label class="form-label fw-semibold">Reason / Notes</label>
        <textarea class="form-control" rows="2" placeholder="e.g. Biometric device offline on this day"></textarea>
      </div>
      <button class="btn btn-warning w-100 fw-semibold"><i class="bi bi-pencil-square me-2"></i>Save Manual Punch</button>
    </div>
  </div>
</div>
""", "05-manual-entry.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 06 — ROSTER LIST
# ─────────────────────────────────────────────────────────────────────────────
w("06-roster-list.html", page("Rosters", """
<div class="d-flex justify-content-between align-items-center mb-4">
  <h4 class="fw-bold mb-0">Rosters</h4>
  <a href="07-roster-assign.html" class="btn btn-primary btn-sm"><i class="bi bi-plus-lg me-1"></i>Assign Roster</a>
</div>
<div class="card border-0 shadow-sm mb-3">
  <div class="card-body py-2">
    <form class="row g-2 align-items-end">
      <div class="col-md-3"><input type="date" class="form-control form-control-sm" value="2026-06-01"></div>
      <div class="col-md-3"><input type="date" class="form-control form-control-sm" value="2026-06-30"></div>
      <div class="col-md-4"><select class="form-select form-select-sm"><option>All Employees</option><option>Ali Hassan</option></select></div>
      <div class="col-md-2"><button class="btn btn-primary btn-sm w-100">Filter</button></div>
    </form>
  </div>
</div>
<div class="card border-0 shadow-sm">
  <div class="card-body p-0">
    <table class="table mb-0">
      <thead><tr><th>Date</th><th>Employee</th><th>Shift</th><th>Hours</th><th>Status</th><th>Notes</th><th></th></tr></thead>
      <tbody>
        <tr><td class="small fw-semibold">Mon 16 Jun</td><td><div class="fw-semibold">Ali Hassan</div><div class="text-muted small">EMP-001</div></td><td><span class="badge bg-primary-subtle text-primary">Morning Shift</span></td><td class="small text-muted">09:00–18:00</td><td><span class="badge bg-success">Working</span></td><td class="small text-muted">—</td><td><a href="#" class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></a></td></tr>
        <tr><td class="small fw-semibold">Mon 16 Jun</td><td><div class="fw-semibold">Sara Ahmed</div><div class="text-muted small">EMP-002</div></td><td><span class="badge bg-primary-subtle text-primary">Morning Shift</span></td><td class="small text-muted">09:00–18:00</td><td><span class="badge bg-success">Working</span></td><td class="small text-muted">—</td><td><a href="#" class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></a></td></tr>
        <tr class="table-info"><td class="small fw-semibold">Mon 16 Jun</td><td><div class="fw-semibold">Bilal Khan</div><div class="text-muted small">EMP-005</div></td><td><span class="badge bg-secondary">—</span></td><td class="small text-muted">—</td><td><span class="badge bg-info text-dark">Holiday</span></td><td class="small text-muted">Eid Holiday</td><td><a href="#" class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></a></td></tr>
        <tr><td class="small fw-semibold">Tue 17 Jun</td><td><div class="fw-semibold">Ali Hassan</div><div class="text-muted small">EMP-001</div></td><td><span class="badge bg-primary-subtle text-primary">Morning Shift</span></td><td class="small text-muted">09:00–18:00</td><td><span class="badge bg-success">Working</span></td><td class="small text-muted">—</td><td><a href="#" class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></a></td></tr>
      </tbody>
    </table>
  </div>
</div>
""", "06-roster-list.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 07 — ROSTER ASSIGN
# ─────────────────────────────────────────────────────────────────────────────
w("07-roster-assign.html", page("Assign Roster", """
<h4 class="fw-bold mb-1">Assign Roster</h4>
<p class="text-muted small mb-4">Bulk-assign shifts to employees across a date range</p>
<div class="row justify-content-center">
  <div class="col-md-7">
    <div class="card border-0 shadow-sm p-4">
      <div class="mb-3">
        <label class="form-label fw-semibold">Employees</label>
        <select class="form-select" multiple style="height:120px">
          <option selected>Ali Hassan (EMP-001)</option>
          <option selected>Sara Ahmed (EMP-002)</option>
          <option>Bilal Khan (EMP-005)</option>
          <option>Fatima Malik (EMP-008)</option>
          <option>Omar Siddiqui (EMP-003)</option>
        </select>
        <div class="form-text">Hold Ctrl/Cmd to select multiple</div>
      </div>
      <div class="row g-2 mb-3">
        <div class="col"><label class="form-label fw-semibold">From Date</label><input type="date" class="form-control" value="2026-07-01"></div>
        <div class="col"><label class="form-label fw-semibold">To Date</label><input type="date" class="form-control" value="2026-07-31"></div>
      </div>
      <div class="mb-3">
        <label class="form-label fw-semibold">Shift</label>
        <select class="form-select">
          <option>Morning Shift (09:00 – 18:00, grace 10 min)</option>
          <option>Night Shift (19:00 – 04:00, grace 15 min)</option>
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label fw-semibold">Weekly Off</label>
        <div class="d-flex flex-wrap gap-2">
          <div class="form-check"><input class="form-check-input" type="checkbox"><label class="form-check-label small">Mon</label></div>
          <div class="form-check"><input class="form-check-input" type="checkbox"><label class="form-check-label small">Tue</label></div>
          <div class="form-check"><input class="form-check-input" type="checkbox"><label class="form-check-label small">Wed</label></div>
          <div class="form-check"><input class="form-check-input" type="checkbox"><label class="form-check-label small">Thu</label></div>
          <div class="form-check"><input class="form-check-input" type="checkbox"><label class="form-check-label small">Fri</label></div>
          <div class="form-check"><input class="form-check-input" type="checkbox" checked><label class="form-check-label small">Sat</label></div>
          <div class="form-check"><input class="form-check-input" type="checkbox" checked><label class="form-check-label small">Sun</label></div>
        </div>
      </div>
      <div class="mb-4">
        <label class="form-label fw-semibold">Notes (optional)</label>
        <input type="text" class="form-control" placeholder="e.g. Summer schedule">
      </div>
      <button class="btn btn-primary w-100 fw-semibold"><i class="bi bi-calendar-check me-2"></i>Assign Roster</button>
    </div>
  </div>
</div>
""", "06-roster-list.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 08 — SHIFTS
# ─────────────────────────────────────────────────────────────────────────────
w("08-shifts.html", page("Shifts", """
<div class="d-flex justify-content-between align-items-center mb-4">
  <h4 class="fw-bold mb-0">Shifts</h4>
  <button class="btn btn-primary btn-sm"><i class="bi bi-plus-lg me-1"></i>New Shift</button>
</div>
<div class="card border-0 shadow-sm">
  <div class="card-body p-0">
    <table class="table mb-0">
      <thead><tr><th>Shift Name</th><th>Start</th><th>End</th><th>Grace</th><th>Duration</th><th>Status</th><th></th></tr></thead>
      <tbody>
        <tr><td class="fw-semibold">Morning Shift</td><td>09:00</td><td>18:00</td><td>10 min</td><td class="text-muted">9 hrs</td><td><span class="badge bg-success">Active</span></td><td><button class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></button></td></tr>
        <tr><td class="fw-semibold">Night Shift</td><td>19:00</td><td>04:00</td><td>15 min</td><td class="text-muted">9 hrs</td><td><span class="badge bg-success">Active</span></td><td><button class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></button></td></tr>
        <tr class="text-muted"><td>Split Shift</td><td>08:00</td><td>13:00</td><td>5 min</td><td class="text-muted">5 hrs</td><td><span class="badge bg-secondary">Inactive</span></td><td><button class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></button></td></tr>
      </tbody>
    </table>
  </div>
</div>
""", "08-shifts.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 09 — EMPLOYEE LIST
# ─────────────────────────────────────────────────────────────────────────────
w("09-employee-list.html", page("Employees", """
<div class="d-flex justify-content-between align-items-center mb-4">
  <h4 class="fw-bold mb-0">Employees</h4>
  <a href="10-employee-form.html" class="btn btn-primary btn-sm"><i class="bi bi-plus-lg me-1"></i>New Employee</a>
</div>
<div class="row g-3 mb-3">
  <div class="col-md-4"><input type="text" class="form-control" placeholder="Search by name or code…"></div>
  <div class="col-md-3"><select class="form-select"><option>All Departments</option><option>Sales</option><option>HR</option><option>Operations</option></select></div>
  <div class="col-md-2"><select class="form-select"><option>Active</option><option>Inactive</option><option>All</option></select></div>
</div>
<div class="card border-0 shadow-sm">
  <div class="card-body p-0">
    <table class="table mb-0">
      <thead><tr><th>Code</th><th>Name</th><th>Department</th><th>Designation</th><th>Salary</th><th>Enrolled</th><th>Status</th><th></th></tr></thead>
      <tbody>
        <tr><td class="fw-semibold text-primary">EMP-001</td><td><div class="fw-semibold">Ali Hassan</div><div class="text-muted small">ali@company.com</div></td><td>Sales</td><td class="small">Senior Executive</td><td class="small">PKR 45,000</td><td><i class="bi bi-fingerprint text-primary" title="Biometric"></i> <i class="bi bi-person-bounding-box text-info ms-1" title="Face"></i></td><td><span class="badge bg-success">Active</span></td><td class="d-flex gap-1"><a href="10-employee-form.html" class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></a><a href="11-employee-enroll.html" class="btn btn-outline-primary btn-sm py-0"><i class="bi bi-fingerprint"></i></a></td></tr>
        <tr><td class="fw-semibold text-primary">EMP-002</td><td><div class="fw-semibold">Sara Ahmed</div><div class="text-muted small">sara@company.com</div></td><td>HR</td><td class="small">HR Manager</td><td class="small">PKR 60,000</td><td><i class="bi bi-person-bounding-box text-info" title="Face only"></i></td><td><span class="badge bg-success">Active</span></td><td class="d-flex gap-1"><a href="10-employee-form.html" class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></a><a href="11-employee-enroll.html" class="btn btn-outline-primary btn-sm py-0"><i class="bi bi-fingerprint"></i></a></td></tr>
        <tr><td class="fw-semibold text-primary">EMP-003</td><td><div class="fw-semibold">Omar Siddiqui</div><div class="text-muted small">omar@company.com</div></td><td>Operations</td><td class="small">Team Lead</td><td class="small">PKR 55,000</td><td><i class="bi bi-fingerprint text-primary"></i></td><td><span class="badge bg-success">Active</span></td><td class="d-flex gap-1"><a href="10-employee-form.html" class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></a><a href="11-employee-enroll.html" class="btn btn-outline-primary btn-sm py-0"><i class="bi bi-fingerprint"></i></a></td></tr>
        <tr class="text-muted"><td class="fw-semibold">EMP-012</td><td><div class="fw-semibold">Kamran Raza</div><div class="text-muted small">—</div></td><td>Sales</td><td class="small">Executive</td><td class="small">PKR 35,000</td><td><span class="text-muted small">—</span></td><td><span class="badge bg-secondary">Inactive</span></td><td class="d-flex gap-1"><a href="10-employee-form.html" class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></a></td></tr>
      </tbody>
    </table>
  </div>
</div>
""", "09-employee-list.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 10 — EMPLOYEE FORM
# ─────────────────────────────────────────────────────────────────────────────
w("10-employee-form.html", page("Edit Employee", """
<div class="d-flex align-items-center mb-4">
  <a href="09-employee-list.html" class="btn btn-outline-secondary btn-sm me-3"><i class="bi bi-arrow-left"></i></a>
  <h4 class="fw-bold mb-0">Edit Employee — Ali Hassan</h4>
</div>
<div class="row">
  <div class="col-md-7">
    <div class="card border-0 shadow-sm p-4 mb-3">
      <h6 class="fw-bold mb-3 text-muted text-uppercase small">Personal Details</h6>
      <div class="row g-3 mb-3">
        <div class="col"><label class="form-label fw-semibold">Employee Code</label><input class="form-control" value="EMP-001"></div>
        <div class="col"><label class="form-label fw-semibold">Full Name</label><input class="form-control" value="Ali Hassan"></div>
      </div>
      <div class="row g-3 mb-3">
        <div class="col"><label class="form-label fw-semibold">Department</label><input class="form-control" value="Sales"></div>
        <div class="col"><label class="form-label fw-semibold">Designation</label><input class="form-control" value="Senior Executive"></div>
      </div>
      <div class="row g-3 mb-3">
        <div class="col"><label class="form-label fw-semibold">Phone</label><input class="form-control" value="+92 300 1234567"></div>
        <div class="col"><label class="form-label fw-semibold">Email</label><input class="form-control" value="ali@company.com"></div>
      </div>
      <div class="row g-3">
        <div class="col"><label class="form-label fw-semibold">Joining Date</label><input type="date" class="form-control" value="2024-01-15"></div>
        <div class="col"><label class="form-label fw-semibold">Weekly Off</label>
          <select class="form-select"><option>Monday</option><option>Friday</option><option selected>Saturday</option><option>Sunday</option></select></div>
      </div>
    </div>
    <div class="card border-0 shadow-sm p-4">
      <h6 class="fw-bold mb-3 text-muted text-uppercase small">Payroll Settings</h6>
      <div class="row g-3 mb-3">
        <div class="col"><label class="form-label fw-semibold">Monthly Salary (PKR)</label><input class="form-control" value="45000"></div>
        <div class="col"><label class="form-label fw-semibold">Late Deduction / Min (auto)</label><input class="form-control" value="2.88" disabled></div>
      </div>
      <div class="form-check mb-3">
        <input class="form-check-input" type="checkbox" id="override">
        <label class="form-check-label fw-semibold" for="override">Override deduction rate manually</label>
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-primary fw-semibold px-4"><i class="bi bi-check2 me-1"></i>Save Changes</button>
        <button class="btn btn-outline-danger"><i class="bi bi-person-dash me-1"></i>Deactivate</button>
      </div>
    </div>
  </div>
  <div class="col-md-5">
    <div class="card border-0 shadow-sm p-4">
      <h6 class="fw-bold mb-3 text-muted text-uppercase small">Biometric Enrollment</h6>
      <div class="d-flex align-items-center mb-3">
        <i class="bi bi-fingerprint fs-2 text-primary me-3"></i>
        <div><div class="fw-semibold">Fingerprint</div><div class="text-success small"><i class="bi bi-check-circle me-1"></i>Enrolled (Right Index)</div></div>
      </div>
      <div class="d-flex align-items-center mb-4">
        <i class="bi bi-person-bounding-box fs-2 text-info me-3"></i>
        <div><div class="fw-semibold">Face Recognition</div><div class="text-success small"><i class="bi bi-check-circle me-1"></i>Enrolled (quality 94%)</div></div>
      </div>
      <a href="11-employee-enroll.html" class="btn btn-outline-primary w-100"><i class="bi bi-fingerprint me-1"></i>Manage Enrollment</a>
    </div>
    <div class="card border-0 shadow-sm p-4 mt-3">
      <h6 class="fw-bold mb-3 text-muted text-uppercase small">Quick Links</h6>
      <a href="13-payroll-detail.html" class="btn btn-outline-secondary w-100 mb-2 text-start"><i class="bi bi-cash-stack me-2 text-success"></i>View Payroll</a>
      <a href="04-attendance-log.html" class="btn btn-outline-secondary w-100 text-start"><i class="bi bi-clock-history me-2 text-primary"></i>Attendance Log</a>
    </div>
  </div>
</div>
""", "09-employee-list.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 11 — EMPLOYEE ENROLL
# ─────────────────────────────────────────────────────────────────────────────
w("11-employee-enroll.html", page("Biometric Enrollment", """
<div class="d-flex align-items-center mb-4">
  <a href="09-employee-list.html" class="btn btn-outline-secondary btn-sm me-3"><i class="bi bi-arrow-left"></i></a>
  <h4 class="fw-bold mb-0">Enrollment — Ali Hassan <span class="text-muted fw-normal small">EMP-001</span></h4>
</div>
<div class="row g-3">
  <div class="col-md-5">
    <div class="card border-0 shadow-sm p-4 mb-3">
      <h6 class="fw-bold mb-3"><i class="bi bi-fingerprint me-2 text-primary"></i>Fingerprint</h6>
      <div class="mb-3">
        <label class="form-label fw-semibold small">Select Finger</label>
        <select class="form-select form-select-sm">
          <option>Right Thumb</option><option selected>Right Index ✓ (enrolled)</option>
          <option>Right Middle</option><option>Left Index</option>
        </select>
      </div>
      <div class="d-flex gap-2 mb-3">
        <div class="text-center flex-fill py-2 rounded" style="background:#d1e7dd"><i class="bi bi-check-lg text-success"></i><div style="font-size:.7rem">Scan 1</div></div>
        <div class="text-center flex-fill py-2 rounded" style="background:#d1e7dd"><i class="bi bi-check-lg text-success"></i><div style="font-size:.7rem">Scan 2</div></div>
        <div class="text-center flex-fill py-2 rounded" style="background:#d1e7dd"><i class="bi bi-check-lg text-success"></i><div style="font-size:.7rem">Scan 3</div></div>
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-primary flex-fill btn-sm"><i class="bi bi-fingerprint me-1"></i>Re-enroll</button>
        <button class="btn btn-outline-danger btn-sm"><i class="bi bi-trash3"></i></button>
      </div>
    </div>
  </div>
  <div class="col-md-7">
    <div class="card border-0 shadow-sm p-4">
      <h6 class="fw-bold mb-3"><i class="bi bi-person-bounding-box me-2 text-info"></i>Face Recognition</h6>
      <div class="row g-3">
        <div class="col-md-6">
          <div class="ratio ratio-4x3 bg-dark rounded overflow-hidden mb-2" style="border-radius:8px!important">
            <div class="d-flex flex-column align-items-center justify-content-center text-white opacity-50">
              <i class="bi bi-camera-video fs-1"></i>
              <div class="small mt-2">Camera preview</div>
            </div>
          </div>
          <button class="btn btn-info w-100 text-white btn-sm"><i class="bi bi-camera me-1"></i>Start Camera</button>
        </div>
        <div class="col-md-6">
          <div class="alert alert-success py-2 small mb-3">
            <i class="bi bi-check-circle me-1"></i>Face enrolled<br>
            <span class="text-muted">Quality: 94% · 5 frames</span>
          </div>
          <div class="mb-2 small fw-semibold">Enrollment steps:</div>
          <ol class="small text-muted ps-3">
            <li>Position face in frame</li>
            <li>Blink when prompted</li>
            <li>5 frames captured automatically</li>
            <li>Embeddings averaged & saved</li>
          </ol>
          <button class="btn btn-outline-danger w-100 btn-sm mt-2"><i class="bi bi-trash3 me-1"></i>Delete Face Template</button>
        </div>
      </div>
    </div>
  </div>
</div>
""", "09-employee-list.html", role="system_admin", fullname="System Admin"))

# ─────────────────────────────────────────────────────────────────────────────
# 12 — PAYROLL OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
w("12-payroll-overview.html", page("Payroll Overview", """
<div class="d-flex justify-content-between align-items-center mb-4">
  <h4 class="fw-bold mb-0">Payroll Overview</h4>
  <a href="20-payroll-export.html" class="btn btn-outline-success btn-sm"><i class="bi bi-file-earmark-excel me-1"></i>Export XLSX</a>
</div>
<div class="card border-0 shadow-sm mb-4">
  <div class="card-body py-3">
    <form class="row g-2 align-items-end">
      <div class="col-md-3"><label class="form-label small fw-semibold mb-1">From</label><input type="date" class="form-control form-control-sm" value="2026-06-01"></div>
      <div class="col-md-3"><label class="form-label small fw-semibold mb-1">To</label><input type="date" class="form-control form-control-sm" value="2026-06-30"></div>
      <div class="col-md-3"><button class="btn btn-primary btn-sm"><i class="bi bi-search me-1"></i>Generate</button></div>
    </form>
  </div>
</div>
<!-- Summary cards -->
<div class="row g-3 mb-4">
  <div class="col-md-3"><div class="card border-0 shadow-sm text-center py-3"><div class="fs-2 fw-bold text-primary">30</div><div class="text-muted small">Employees</div></div></div>
  <div class="col-md-3"><div class="card border-0 shadow-sm text-center py-3"><div class="fs-2 fw-bold text-success">PKR 12,80,000</div><div class="text-muted small">Total Gross Salary</div></div></div>
  <div class="col-md-3"><div class="card border-0 shadow-sm text-center py-3"><div class="fs-2 fw-bold text-danger">PKR 24,600</div><div class="text-muted small">Total Deductions</div></div></div>
  <div class="col-md-3"><div class="card border-0 shadow-sm text-center py-3 border-success border-2"><div class="fs-2 fw-bold text-success">PKR 12,55,400</div><div class="text-muted small">Net Payable</div></div></div>
</div>
<div class="card border-0 shadow-sm">
  <div class="card-body p-0">
    <table class="table mb-0">
      <thead><tr><th>Employee</th><th>Dept</th><th>Working Days</th><th>Present</th><th>Absent</th><th>Late Days</th><th>Late (min)</th><th>Deduction</th><th>Net Payable</th><th></th></tr></thead>
      <tbody>
        <tr><td><div class="fw-semibold">Ali Hassan</div><div class="text-muted small">EMP-001</div></td><td class="small">Sales</td><td class="text-center">26</td><td class="text-center text-success fw-semibold">24</td><td class="text-center text-danger fw-semibold">2</td><td class="text-center text-warning">3</td><td class="text-center">24</td><td class="text-end text-danger">PKR 69</td><td class="text-end fw-bold text-success">PKR 44,931</td><td><a href="13-payroll-detail.html" class="btn btn-outline-primary btn-sm py-0">Detail</a></td></tr>
        <tr><td><div class="fw-semibold">Sara Ahmed</div><div class="text-muted small">EMP-002</div></td><td class="small">HR</td><td class="text-center">26</td><td class="text-center text-success fw-semibold">26</td><td class="text-center">0</td><td class="text-center">1</td><td class="text-center">5</td><td class="text-end text-danger">PKR 19</td><td class="text-end fw-bold text-success">PKR 59,981</td><td><a href="13-payroll-detail.html" class="btn btn-outline-primary btn-sm py-0">Detail</a></td></tr>
        <tr><td><div class="fw-semibold">Omar Siddiqui</div><div class="text-muted small">EMP-003</div></td><td class="small">Ops</td><td class="text-center">26</td><td class="text-center text-success fw-semibold">25</td><td class="text-center text-danger fw-semibold">1</td><td class="text-center text-warning">2</td><td class="text-center">18</td><td class="text-end text-danger">PKR 55</td><td class="text-end fw-bold text-success">PKR 54,945</td><td><a href="13-payroll-detail.html" class="btn btn-outline-primary btn-sm py-0">Detail</a></td></tr>
      </tbody>
      <tfoot class="table-dark fw-semibold">
        <tr><td colspan="2">TOTALS</td><td class="text-center">78</td><td class="text-center">75</td><td class="text-center">3</td><td class="text-center">6</td><td class="text-center">47</td><td class="text-end">PKR 143</td><td class="text-end">PKR 1,59,857</td><td></td></tr>
      </tfoot>
    </table>
  </div>
</div>
""", "12-payroll-overview.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 13 — PAYROLL DETAIL
# ─────────────────────────────────────────────────────────────────────────────
w("13-payroll-detail.html", page("Payroll Detail", """
<div class="d-flex align-items-center justify-content-between mb-4">
  <div class="d-flex align-items-center">
    <a href="12-payroll-overview.html" class="btn btn-sm btn-outline-secondary me-3"><i class="bi bi-arrow-left"></i></a>
    <div>
      <h4 class="fw-bold mb-0">Ali Hassan</h4>
      <div class="text-muted small">EMP-001 · Sales · <span class="text-success fw-semibold">PKR 45,000/month</span></div>
    </div>
  </div>
  <button class="btn btn-outline-secondary btn-sm"><i class="bi bi-printer me-1"></i>Print</button>
</div>
<!-- Summary cards -->
<div class="row g-3 mb-4">
  <div class="col-md-2"><div class="card border-0 shadow-sm text-center py-3"><div class="fs-3 fw-bold text-primary">26</div><div class="text-muted small">Working Days</div></div></div>
  <div class="col-md-2"><div class="card border-0 shadow-sm text-center py-3"><div class="fs-3 fw-bold text-success">24</div><div class="text-muted small">Present</div></div></div>
  <div class="col-md-2"><div class="card border-0 shadow-sm text-center py-3"><div class="fs-3 fw-bold text-danger">2</div><div class="text-muted small">Absent</div></div></div>
  <div class="col-md-2"><div class="card border-0 shadow-sm text-center py-3"><div class="fs-3 fw-bold text-secondary">1</div><div class="text-muted small">Holidays</div></div></div>
  <div class="col-md-2"><div class="card border-0 shadow-sm text-center py-3"><div class="fs-3 fw-bold text-warning">24</div><div class="text-muted small">Late (min)</div></div></div>
  <div class="col-md-2"><div class="card border-0 shadow-sm text-center py-3 border-danger border-2"><div class="fs-3 fw-bold text-danger">PKR 69</div><div class="text-muted small">Deductions</div></div></div>
</div>
<!-- Net Payable banner -->
<div class="card border-0 shadow-sm mb-4" style="border-left:4px solid #198754!important">
  <div class="card-body py-3 d-flex justify-content-between align-items-center">
    <div>
      <div class="text-muted small fw-semibold text-uppercase">Net Payable — June 2026</div>
      <div class="text-muted small">PKR 45,000 salary − PKR 69 deductions + PKR 2,000 bonus</div>
    </div>
    <div class="fs-2 fw-bold text-success">PKR 46,931</div>
  </div>
</div>
<!-- Day table -->
<div class="card border-0 shadow-sm mb-4">
  <div class="card-header bg-white border-0 pt-3 pb-2"><h6 class="fw-bold mb-0">Daily Attendance — June 2026</h6></div>
  <div class="card-body p-0">
    <table class="table table-sm mb-0">
      <thead><tr><th>Date</th><th>Day</th><th>Shift</th><th>Status</th><th>Punch In</th><th>Punch Out</th><th>Hours</th><th>OT</th><th>Late (min)</th><th class="text-end">Deduction</th></tr></thead>
      <tbody>
        <tr><td class="small">01 Jun</td><td class="small text-muted">Mon</td><td class="small">Morning</td><td><span class="badge bg-success">P</span></td><td class="small">09:02</td><td class="small">18:10</td><td class="small">9.1h</td><td class="small text-muted">—</td><td class="small">—</td><td class="text-end small">—</td></tr>
        <tr class="table-warning"><td class="small">02 Jun</td><td class="small text-muted">Tue</td><td class="small">Morning</td><td><span class="badge bg-success">P</span></td><td class="small">09:14</td><td class="small">18:05</td><td class="small">8.8h</td><td class="small text-muted">—</td><td class="small text-danger fw-semibold">14 min</td><td class="text-end small text-danger">PKR 40</td></tr>
        <tr class="table-info"><td class="small">03 Jun</td><td class="small text-muted">Wed</td><td class="small">Morning</td><td><span class="badge bg-info text-dark">H</span></td><td class="small text-muted">—</td><td class="small text-muted">—</td><td class="small text-muted">—</td><td class="small text-muted">—</td><td class="small">—</td><td class="text-end small">—</td></tr>
        <tr class="table-danger"><td class="small">04 Jun</td><td class="small text-muted">Thu</td><td class="small">Morning</td><td><span class="badge bg-danger">A</span></td><td class="small text-muted">—</td><td class="small text-muted">—</td><td class="small text-muted">—</td><td class="small text-muted">—</td><td class="small">—</td><td class="text-end small text-danger">PKR 29</td></tr>
        <tr class="table-primary"><td class="small">05 Jun</td><td class="small text-muted">Fri</td><td class="small">Morning</td><td><span class="badge bg-success">P</span></td><td class="small">08:58</td><td class="small text-primary fw-semibold">20:15 <span class="badge bg-primary ms-1" style="font-size:.6rem">+135 min OT ✓</span></td><td class="small">11.2h</td><td class="small text-primary fw-semibold">2.25h</td><td class="small">—</td><td class="text-end small">—</td></tr>
      </tbody>
      <tfoot class="table-dark fw-semibold"><tr><td colspan="6">TOTALS</td><td>9.0h avg</td><td class="text-primary">2.25h OT</td><td class="text-danger">24 min</td><td class="text-end text-danger">PKR 69</td></tr></tfoot>
    </table>
  </div>
</div>
<!-- Adjustments -->
<div class="card border-0 shadow-sm">
  <div class="card-header bg-white border-0 pt-3 pb-2 d-flex justify-content-between align-items-center">
    <h6 class="fw-bold mb-0"><i class="bi bi-sliders me-2 text-primary"></i>Manual Settlements &amp; Adjustments</h6>
    <button class="btn btn-primary btn-sm"><i class="bi bi-plus-lg me-1"></i>Add Adjustment</button>
  </div>
  <div class="card-body p-0">
    <table class="table table-sm mb-0">
      <thead><tr><th>Type</th><th>Description</th><th>Period</th><th class="text-end">Amount</th><th>Added By</th><th></th></tr></thead>
      <tbody>
        <tr><td><span class="badge bg-success">Bonus</span></td><td>Eid-ul-Adha Bonus</td><td class="small text-muted">01–30 Jun</td><td class="text-end fw-semibold text-success">+PKR 2,000</td><td class="small text-muted">Super Admin</td><td><button class="btn btn-link btn-sm text-danger p-0"><i class="bi bi-trash3"></i></button></td></tr>
        <tr><td><span class="badge bg-danger">Advance</span></td><td>Salary advance May</td><td class="small text-muted">01–31 May</td><td class="text-end fw-semibold text-danger">-PKR 5,000</td><td class="small text-muted">Super Admin</td><td><button class="btn btn-link btn-sm text-danger p-0"><i class="bi bi-trash3"></i></button></td></tr>
      </tbody>
      <tfoot class="table-light fw-semibold"><tr><td colspan="3">Adjustment Totals</td><td class="text-end"><span class="text-success">+PKR 2,000</span> <span class="text-danger ms-2">-PKR 5,000</span></td><td colspan="2"></td></tr></tfoot>
    </table>
  </div>
</div>
""", "12-payroll-overview.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 14 — SYNC STATUS
# ─────────────────────────────────────────────────────────────────────────────
w("14-sync-status.html", page("Sync to ERP", """
<div class="d-flex justify-content-between align-items-center mb-4">
  <h4 class="fw-bold mb-0">Sync to ERP</h4>
  <button class="btn btn-primary"><i class="bi bi-cloud-upload me-2"></i>Run Sync Now</button>
</div>
<div class="row g-3 mb-4">
  <div class="col-md-3"><div class="card border-0 shadow-sm text-center py-3"><div class="fs-2 fw-bold text-warning">42</div><div class="text-muted small">Unsynced Records</div></div></div>
  <div class="col-md-3"><div class="card border-0 shadow-sm text-center py-3"><div class="fs-2 fw-bold text-success">1,840</div><div class="text-muted small">Total Synced</div></div></div>
  <div class="col-md-3"><div class="card border-0 shadow-sm text-center py-3"><div class="fs-2 fw-bold text-primary">Today 04:02</div><div class="text-muted small">Last Sync</div></div></div>
  <div class="col-md-3"><div class="card border-0 shadow-sm text-center py-3"><div class="fs-2 fw-bold text-success"><i class="bi bi-circle-fill" style="font-size:1rem"></i></div><div class="text-muted small">ERP Connected</div></div></div>
</div>
<div class="alert alert-info py-2 small mb-4"><i class="bi bi-info-circle me-2"></i>Manager sync windows: <strong>17:00–17:30 · 23:30–00:00 · 04:00–05:00</strong>. Super Admin can sync anytime.</div>
<div class="card border-0 shadow-sm">
  <div class="card-header bg-white border-0 pt-3"><h6 class="fw-bold mb-0">Sync History</h6></div>
  <div class="card-body p-0">
    <table class="table mb-0">
      <thead><tr><th>Time</th><th>Records</th><th>Status</th><th>Synced By</th><th>Error</th></tr></thead>
      <tbody>
        <tr><td class="small">Today 04:02</td><td>142</td><td><span class="badge bg-success">Success</span></td><td class="small">Auto</td><td>—</td></tr>
        <tr><td class="small">Yesterday 23:32</td><td>38</td><td><span class="badge bg-success">Success</span></td><td class="small">Manager</td><td>—</td></tr>
        <tr><td class="small">15 Jun 17:01</td><td>0</td><td><span class="badge bg-secondary">No data</span></td><td class="small">Auto</td><td>—</td></tr>
        <tr><td class="small">14 Jun 04:00</td><td>128</td><td><span class="badge bg-warning text-dark">Partial</span></td><td class="small">Auto</td><td class="small text-danger">Timeout after 120 records</td></tr>
      </tbody>
    </table>
  </div>
</div>
""", "14-sync-status.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 15 — MANUAL GRANTS
# ─────────────────────────────────────────────────────────────────────────────
w("15-manual-grants.html", page("Manual Entry Grants", """
<div class="d-flex justify-content-between align-items-center mb-4">
  <div><h4 class="fw-bold mb-0">Manual Entry Grants</h4><p class="text-muted small mb-0">Temporarily allow managers to enter backdated attendance</p></div>
  <button class="btn btn-primary btn-sm"><i class="bi bi-key me-1"></i>Grant Access</button>
</div>
<div class="card border-0 shadow-sm">
  <div class="card-body p-0">
    <table class="table mb-0">
      <thead><tr><th>Manager</th><th>Grant Date</th><th>Time Window</th><th>Granted By</th><th>Granted At</th><th>Status</th><th></th></tr></thead>
      <tbody>
        <tr><td><div class="fw-semibold">Raza Manager</div><div class="text-muted small">manager role</div></td><td class="small">16 Jun 2026</td><td class="small fw-semibold">10:00 – 12:00</td><td class="small text-muted">Super Admin</td><td class="small text-muted">Today 09:45</td><td><span class="badge bg-success">Active Now</span></td><td><button class="btn btn-outline-danger btn-sm py-0">Revoke</button></td></tr>
        <tr class="text-muted"><td><div>Store Manager</div><div class="text-muted small">manager role</div></td><td class="small">15 Jun 2026</td><td class="small">09:00 – 11:00</td><td class="small text-muted">Super Admin</td><td class="small text-muted">Yesterday</td><td><span class="badge bg-secondary">Expired</span></td><td></td></tr>
      </tbody>
    </table>
  </div>
</div>
""", "15-manual-grants.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 16 — DATA CLEANUP
# ─────────────────────────────────────────────────────────────────────────────
w("16-data-cleanup.html", page("Data Cleanup", """
<h4 class="fw-bold mb-1">Data Cleanup</h4>
<p class="text-muted small mb-4">Manage attendance records — delete, deduplicate, recalculate</p>
<div class="row g-3">
  <div class="col-md-4">
    <div class="card border-0 shadow-sm p-4 h-100">
      <h6 class="fw-bold mb-1"><i class="bi bi-trash3 me-2 text-danger"></i>Delete Records</h6>
      <p class="text-muted small mb-3">Permanently delete all punches in a date range</p>
      <div class="mb-2"><label class="form-label small fw-semibold">From</label><input type="date" class="form-control form-control-sm" value="2026-06-01"></div>
      <div class="mb-3"><label class="form-label small fw-semibold">To</label><input type="date" class="form-control form-control-sm" value="2026-06-01"></div>
      <button class="btn btn-danger btn-sm w-100"><i class="bi bi-trash3 me-1"></i>Delete Range</button>
    </div>
  </div>
  <div class="col-md-4">
    <div class="card border-0 shadow-sm p-4 h-100">
      <h6 class="fw-bold mb-1"><i class="bi bi-copy me-2 text-warning"></i>Deduplicate</h6>
      <p class="text-muted small mb-3">Remove duplicate punches — keep earliest IN, latest OUT per day</p>
      <div class="mb-2"><label class="form-label small fw-semibold">From</label><input type="date" class="form-control form-control-sm"></div>
      <div class="mb-3"><label class="form-label small fw-semibold">To</label><input type="date" class="form-control form-control-sm"></div>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-warning btn-sm flex-fill"><i class="bi bi-eye me-1"></i>Preview</button>
        <button class="btn btn-warning btn-sm flex-fill"><i class="bi bi-copy me-1"></i>Run</button>
      </div>
    </div>
  </div>
  <div class="col-md-4">
    <div class="card border-0 shadow-sm p-4 h-100">
      <h6 class="fw-bold mb-1"><i class="bi bi-arrow-repeat me-2 text-primary"></i>Recalculate Late</h6>
      <p class="text-muted small mb-3">Recalculate minutes_late for all IN punches using current shift settings</p>
      <div class="mb-2"><label class="form-label small fw-semibold">From</label><input type="date" class="form-control form-control-sm"></div>
      <div class="mb-3"><label class="form-label small fw-semibold">To</label><input type="date" class="form-control form-control-sm"></div>
      <button class="btn btn-primary btn-sm w-100"><i class="bi bi-arrow-repeat me-1"></i>Recalculate</button>
    </div>
  </div>
</div>
""", "16-data-cleanup.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 17 — OVERTIME QUEUE (NEW)
# ─────────────────────────────────────────────────────────────────────────────
w("17-overtime-queue.html", page("Overtime Approvals", """
<div class="alert alert-primary py-2 small mb-3 wf-new">
  <i class="bi bi-stars me-2"></i><strong>New Feature</strong> — Overtime detection &amp; approval workflow (US-014 / US-015 / US-035 / US-036)
</div>
<div class="d-flex justify-content-between align-items-center mb-4">
  <div><h4 class="fw-bold mb-0">Overtime Approvals <span class="badge bg-danger ms-2">3 Pending</span></h4><p class="text-muted small mb-0">Auto-detected when punch-out exceeds shift end + 30 min threshold</p></div>
  <div class="d-flex gap-2">
    <button class="btn btn-outline-success btn-sm"><i class="bi bi-check-all me-1"></i>Approve All Selected</button>
    <button class="btn btn-outline-danger btn-sm"><i class="bi bi-x-lg me-1"></i>Reject All Selected</button>
  </div>
</div>
<!-- Config row -->
<div class="row g-3 mb-4">
  <div class="col-md-3"><div class="card border-0 shadow-sm text-center py-2"><div class="fw-bold text-primary">30 min</div><div class="text-muted small">OT Threshold</div></div></div>
  <div class="col-md-3"><div class="card border-0 shadow-sm text-center py-2"><div class="fw-bold text-primary">1.5×</div><div class="text-muted small">OT Pay Multiplier</div></div></div>
  <div class="col-md-3"><div class="card border-0 shadow-sm text-center py-2"><div class="fw-bold text-success">8</div><div class="text-muted small">Approved This Month</div></div></div>
  <div class="col-md-3"><div class="card border-0 shadow-sm text-center py-2"><div class="fw-bold text-danger">3</div><div class="text-muted small">Pending</div></div></div>
</div>
<!-- Tabs -->
<ul class="nav nav-tabs mb-3">
  <li class="nav-item"><button class="nav-link active">Pending <span class="badge bg-danger ms-1">3</span></button></li>
  <li class="nav-item"><button class="nav-link">Approved</button></li>
  <li class="nav-item"><button class="nav-link">Rejected</button></li>
  <li class="nav-item"><button class="nav-link">All</button></li>
</ul>
<div class="card border-0 shadow-sm">
  <div class="card-body p-0">
    <table class="table mb-0">
      <thead><tr><th><input type="checkbox"></th><th>Employee</th><th>Date</th><th>Shift End</th><th>Actual Out</th><th>OT Minutes</th><th>OT Pay (1.5×)</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody>
        <tr>
          <td><input type="checkbox"></td>
          <td><div class="fw-semibold">Omar Siddiqui</div><div class="text-muted small">EMP-003</div></td>
          <td class="small">Mon 16 Jun</td>
          <td class="small fw-semibold">18:00</td>
          <td class="small fw-semibold text-primary">19:42</td>
          <td><span class="badge bg-primary fs-6">102 min</span></td>
          <td class="fw-semibold text-success">PKR 524</td>
          <td><span class="badge bg-warning text-dark">Pending</span></td>
          <td>
            <div class="d-flex gap-1">
              <button class="btn btn-success btn-sm py-0"><i class="bi bi-check2 me-1"></i>Approve</button>
              <button class="btn btn-outline-danger btn-sm py-0"><i class="bi bi-x"></i></button>
            </div>
          </td>
        </tr>
        <tr>
          <td><input type="checkbox"></td>
          <td><div class="fw-semibold">Ali Hassan</div><div class="text-muted small">EMP-001</div></td>
          <td class="small">Fri 05 Jun</td>
          <td class="small fw-semibold">18:00</td>
          <td class="small fw-semibold text-primary">20:15</td>
          <td><span class="badge bg-primary fs-6">135 min</span></td>
          <td class="fw-semibold text-success">PKR 584</td>
          <td><span class="badge bg-warning text-dark">Pending</span></td>
          <td>
            <div class="d-flex gap-1">
              <button class="btn btn-success btn-sm py-0"><i class="bi bi-check2 me-1"></i>Approve</button>
              <button class="btn btn-outline-danger btn-sm py-0"><i class="bi bi-x"></i></button>
            </div>
          </td>
        </tr>
        <tr>
          <td><input type="checkbox"></td>
          <td><div class="fw-semibold">Bilal Khan</div><div class="text-muted small">EMP-005</div></td>
          <td class="small">Sat 06 Jun</td>
          <td class="small fw-semibold">18:00</td>
          <td class="small fw-semibold text-primary">20:45</td>
          <td><span class="badge bg-primary fs-6">165 min</span></td>
          <td class="fw-semibold text-success">PKR 594</td>
          <td><span class="badge bg-warning text-dark">Pending</span></td>
          <td>
            <div class="d-flex gap-1">
              <button class="btn btn-success btn-sm py-0"><i class="bi bi-check2 me-1"></i>Approve</button>
              <button class="btn btn-outline-danger btn-sm py-0"><i class="bi bi-x"></i></button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
<!-- OT Settings card -->
<div class="card border-0 shadow-sm mt-4 wf-new">
  <div class="card-header bg-white border-0 pt-3 pb-2">
    <h6 class="fw-bold mb-0"><i class="bi bi-gear me-2"></i>Overtime Settings</h6>
  </div>
  <div class="card-body">
    <div class="row g-3">
      <div class="col-md-3"><label class="form-label fw-semibold">OT Threshold (minutes)</label><input class="form-control" value="30" type="number"></div>
      <div class="col-md-3"><label class="form-label fw-semibold">Pay Multiplier</label><select class="form-select"><option>1.25×</option><option selected>1.5×</option><option>2.0×</option></select></div>
      <div class="col-md-6 d-flex align-items-end"><button class="btn btn-primary">Save OT Settings</button></div>
    </div>
  </div>
</div>
""", "17-overtime-queue.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 18 — USER MANAGEMENT (NEW)
# ─────────────────────────────────────────────────────────────────────────────
w("18-user-management.html", page("User Management", """
<div class="alert alert-primary py-2 small mb-3 wf-new">
  <i class="bi bi-stars me-2"></i><strong>New Feature</strong> — App user CRUD (US-006 / US-007)
</div>
<div class="d-flex justify-content-between align-items-center mb-4">
  <h4 class="fw-bold mb-0">User Management</h4>
  <button class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#newUserModal">
    <i class="bi bi-person-plus me-1"></i>New User
  </button>
</div>
<div class="card border-0 shadow-sm">
  <div class="card-body p-0">
    <table class="table mb-0">
      <thead><tr><th>Username</th><th>Full Name</th><th>Role</th><th>Last Login</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody>
        <tr><td class="fw-semibold">admin</td><td>Super Admin</td><td><span class="badge bg-primary">Super Admin</span></td><td class="small text-muted">Today 08:50</td><td><span class="badge bg-success">Active</span></td><td class="d-flex gap-1"><button class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></button><button class="btn btn-outline-warning btn-sm py-0" title="Reset Password"><i class="bi bi-key"></i></button></td></tr>
        <tr><td class="fw-semibold">manager1</td><td>Raza Ahmed</td><td><span class="badge bg-success">Manager</span></td><td class="small text-muted">Today 09:10</td><td><span class="badge bg-success">Active</span></td><td class="d-flex gap-1"><button class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></button><button class="btn btn-outline-warning btn-sm py-0" title="Reset Password"><i class="bi bi-key"></i></button><button class="btn btn-outline-danger btn-sm py-0"><i class="bi bi-person-dash"></i></button></td></tr>
        <tr><td class="fw-semibold">enroll1</td><td>IT Admin</td><td><span class="badge bg-info text-dark">System Admin</span></td><td class="small text-muted">3 days ago</td><td><span class="badge bg-success">Active</span></td><td class="d-flex gap-1"><button class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></button><button class="btn btn-outline-warning btn-sm py-0"><i class="bi bi-key"></i></button><button class="btn btn-outline-danger btn-sm py-0"><i class="bi bi-person-dash"></i></button></td></tr>
        <tr><td class="fw-semibold">store1</td><td>Store Terminal</td><td><span class="badge bg-warning text-dark">Store</span></td><td class="small text-muted">Today 07:58</td><td><span class="badge bg-success">Active</span></td><td class="d-flex gap-1"><button class="btn btn-outline-secondary btn-sm py-0"><i class="bi bi-pencil"></i></button><button class="btn btn-outline-warning btn-sm py-0"><i class="bi bi-key"></i></button><button class="btn btn-outline-danger btn-sm py-0"><i class="bi bi-person-dash"></i></button></td></tr>
        <tr class="text-muted"><td>cashier_old</td><td>Old Cashier</td><td><span class="badge bg-secondary">Cashier</span></td><td class="small text-muted">45 days ago</td><td><span class="badge bg-secondary">Inactive</span></td><td><button class="btn btn-outline-success btn-sm py-0"><i class="bi bi-person-check"></i></button></td></tr>
      </tbody>
    </table>
  </div>
</div>
<!-- New User Modal -->
<div class="modal fade" id="newUserModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header border-0">
        <h6 class="modal-title fw-bold"><i class="bi bi-person-plus me-2 text-primary"></i>Create New User</h6>
        <button class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <div class="mb-3"><label class="form-label fw-semibold">Username</label><input class="form-control" placeholder="e.g. manager2"></div>
        <div class="mb-3"><label class="form-label fw-semibold">Full Name</label><input class="form-control" placeholder="Full display name"></div>
        <div class="mb-3"><label class="form-label fw-semibold">Role</label>
          <select class="form-select">
            <option>Super Admin</option><option selected>Manager</option><option>System Admin</option><option>Store</option><option>Cashier</option>
          </select>
        </div>
        <div class="mb-3"><label class="form-label fw-semibold">Password</label><input type="password" class="form-control"></div>
        <div class="mb-3"><label class="form-label fw-semibold">Confirm Password</label><input type="password" class="form-control"></div>
      </div>
      <div class="modal-footer border-0">
        <button class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
        <button class="btn btn-primary btn-sm fw-semibold"><i class="bi bi-check2 me-1"></i>Create User</button>
      </div>
    </div>
  </div>
</div>
""", "18-user-management.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 19 — LEAVE MANAGEMENT (NEW)
# ─────────────────────────────────────────────────────────────────────────────
w("19-leave-management.html", page("Leave Management", """
<div class="alert alert-primary py-2 small mb-3 wf-new">
  <i class="bi bi-stars me-2"></i><strong>New Feature</strong> — Leave tracking &amp; approval (US-032)
</div>
<div class="d-flex justify-content-between align-items-center mb-4">
  <div><h4 class="fw-bold mb-0">Leave Requests <span class="badge bg-warning text-dark ms-2">2 Pending</span></h4></div>
  <button class="btn btn-primary btn-sm"><i class="bi bi-plus-lg me-1"></i>New Leave Request</button>
</div>
<ul class="nav nav-tabs mb-3">
  <li class="nav-item"><button class="nav-link active">Pending <span class="badge bg-warning text-dark ms-1">2</span></button></li>
  <li class="nav-item"><button class="nav-link">Approved</button></li>
  <li class="nav-item"><button class="nav-link">Rejected</button></li>
  <li class="nav-item"><button class="nav-link">All</button></li>
</ul>
<div class="card border-0 shadow-sm mb-4">
  <div class="card-body p-0">
    <table class="table mb-0">
      <thead><tr><th>Employee</th><th>Type</th><th>From</th><th>To</th><th>Days</th><th>Reason</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody>
        <tr>
          <td><div class="fw-semibold">Sara Ahmed</div><div class="text-muted small">EMP-002</div></td>
          <td><span class="badge bg-info text-dark">Sick Leave</span></td>
          <td class="small">18 Jun</td><td class="small">19 Jun</td><td class="text-center fw-semibold">2</td>
          <td class="small text-muted">Fever, doctor's rest advised</td>
          <td><span class="badge bg-warning text-dark">Pending</span></td>
          <td><div class="d-flex gap-1"><button class="btn btn-success btn-sm py-0"><i class="bi bi-check2 me-1"></i>Approve</button><button class="btn btn-outline-danger btn-sm py-0">Reject</button></div></td>
        </tr>
        <tr>
          <td><div class="fw-semibold">Bilal Khan</div><div class="text-muted small">EMP-005</div></td>
          <td><span class="badge bg-primary">Annual Leave</span></td>
          <td class="small">20 Jun</td><td class="small">25 Jun</td><td class="text-center fw-semibold">5</td>
          <td class="small text-muted">Family event</td>
          <td><span class="badge bg-warning text-dark">Pending</span></td>
          <td><div class="d-flex gap-1"><button class="btn btn-success btn-sm py-0"><i class="bi bi-check2 me-1"></i>Approve</button><button class="btn btn-outline-danger btn-sm py-0">Reject</button></div></td>
        </tr>
        <tr class="table-success">
          <td><div class="fw-semibold">Ali Hassan</div><div class="text-muted small">EMP-001</div></td>
          <td><span class="badge bg-primary">Annual Leave</span></td>
          <td class="small">01 Jun</td><td class="small">03 Jun</td><td class="text-center fw-semibold">3</td>
          <td class="small text-muted">Vacation</td>
          <td><span class="badge bg-success">Approved</span></td>
          <td class="small text-muted">By Admin</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
<!-- Leave Balances -->
<div class="card border-0 shadow-sm">
  <div class="card-header bg-white border-0 pt-3 pb-2"><h6 class="fw-bold mb-0">Leave Balances — 2026</h6></div>
  <div class="card-body p-0">
    <table class="table mb-0">
      <thead><tr><th>Employee</th><th class="text-center">Annual Entitled</th><th class="text-center">Annual Taken</th><th class="text-center">Annual Remaining</th><th class="text-center">Sick Taken</th><th class="text-center">Unpaid Taken</th></tr></thead>
      <tbody>
        <tr><td><div class="fw-semibold">Ali Hassan</div></td><td class="text-center">14</td><td class="text-center text-danger">3</td><td class="text-center text-success fw-semibold">11</td><td class="text-center">0</td><td class="text-center">0</td></tr>
        <tr><td><div class="fw-semibold">Sara Ahmed</div></td><td class="text-center">14</td><td class="text-center text-danger">0</td><td class="text-center text-success fw-semibold">14</td><td class="text-center text-warning">2 pending</td><td class="text-center">0</td></tr>
        <tr><td><div class="fw-semibold">Bilal Khan</div></td><td class="text-center">14</td><td class="text-center text-danger">0</td><td class="text-center text-success fw-semibold">14</td><td class="text-center">0</td><td class="text-center">0</td></tr>
      </tbody>
    </table>
  </div>
</div>
""", "19-leave-management.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 20 — PAYROLL EXPORT (NEW)
# ─────────────────────────────────────────────────────────────────────────────
w("20-payroll-export.html", page("Payroll Export", """
<div class="alert alert-primary py-2 small mb-3 wf-new">
  <i class="bi bi-stars me-2"></i><strong>New Feature</strong> — Payroll XLSX/CSV export (US-030)
</div>
<div class="d-flex justify-content-between align-items-center mb-4">
  <h4 class="fw-bold mb-0">Export Payroll</h4>
  <a href="12-payroll-overview.html" class="btn btn-outline-secondary btn-sm"><i class="bi bi-arrow-left me-1"></i>Back to Payroll</a>
</div>
<div class="row justify-content-center">
  <div class="col-md-6">
    <div class="card border-0 shadow-sm p-4">
      <div class="row g-3 mb-4">
        <div class="col"><label class="form-label fw-semibold">Period From</label><input type="date" class="form-control" value="2026-06-01"></div>
        <div class="col"><label class="form-label fw-semibold">Period To</label><input type="date" class="form-control" value="2026-06-30"></div>
      </div>
      <div class="mb-4">
        <label class="form-label fw-semibold">Include Columns</label>
        <div class="row g-2">
          <div class="col-6"><div class="form-check"><input class="form-check-input" type="checkbox" checked><label class="form-check-label small">Employee Code</label></div></div>
          <div class="col-6"><div class="form-check"><input class="form-check-input" type="checkbox" checked><label class="form-check-label small">Full Name</label></div></div>
          <div class="col-6"><div class="form-check"><input class="form-check-input" type="checkbox" checked><label class="form-check-label small">Department</label></div></div>
          <div class="col-6"><div class="form-check"><input class="form-check-input" type="checkbox" checked><label class="form-check-label small">Working Days</label></div></div>
          <div class="col-6"><div class="form-check"><input class="form-check-input" type="checkbox" checked><label class="form-check-label small">Present / Absent</label></div></div>
          <div class="col-6"><div class="form-check"><input class="form-check-input" type="checkbox" checked><label class="form-check-label small">Late Minutes</label></div></div>
          <div class="col-6"><div class="form-check"><input class="form-check-input" type="checkbox" checked><label class="form-check-label small">Late Deduction</label></div></div>
          <div class="col-6"><div class="form-check"><input class="form-check-input" type="checkbox" checked><label class="form-check-label small">OT Hours &amp; Pay</label></div></div>
          <div class="col-6"><div class="form-check"><input class="form-check-input" type="checkbox" checked><label class="form-check-label small">Adjustments</label></div></div>
          <div class="col-6"><div class="form-check"><input class="form-check-input" type="checkbox" checked><label class="form-check-label small">Net Payable</label></div></div>
        </div>
      </div>
      <div class="d-flex gap-3">
        <button class="btn btn-success flex-fill fw-semibold"><i class="bi bi-file-earmark-excel me-2"></i>Export XLSX</button>
        <button class="btn btn-outline-secondary flex-fill"><i class="bi bi-filetype-csv me-2"></i>Export CSV</button>
      </div>
    </div>
  </div>
</div>
""", "12-payroll-overview.html"))

# ─────────────────────────────────────────────────────────────────────────────
# 21 — REQUEST OVERRIDE
# ─────────────────────────────────────────────────────────────────────────────
w("21-override-request.html", login_page("""
<div class="min-vh-100 d-flex align-items-center justify-content-center bg-light">
  <div class="card border-0 shadow-lg p-4" style="width:380px;border-radius:16px">
    <div class="text-center mb-4">
      <div class="bg-warning bg-opacity-10 rounded-circle d-inline-flex p-3 mb-3">
        <i class="bi bi-shield-lock fs-2 text-warning"></i>
      </div>
      <h5 class="fw-bold mb-1">Override Required</h5>
      <p class="text-muted small">Enter the Super Admin override password to access <strong>Manual Attendance Entry</strong></p>
    </div>
    <div class="mb-4">
      <label class="form-label fw-semibold">Override Password</label>
      <input type="password" class="form-control" placeholder="Enter override password">
    </div>
    <button class="btn btn-warning w-100 fw-semibold mb-3"><i class="bi bi-unlock me-2"></i>Unlock Access</button>
    <a href="02-dashboard.html" class="btn btn-outline-secondary w-100">Cancel</a>
  </div>
</div>
"""))

# ─────────────────────────────────────────────────────────────────────────────
# INDEX
# ─────────────────────────────────────────────────────────────────────────────
screens = [
    ("01-login.html",            "Login",                   "Existing",  ""),
    ("02-dashboard.html",        "Dashboard",               "Existing",  ""),
    ("03-punch-screen.html",     "Punch Screen",            "Existing",  "Fingerprint + Face + Manual"),
    ("04-attendance-log.html",   "Attendance Log",          "Updated",   "Pagination added"),
    ("05-manual-entry.html",     "Manual Entry",            "Existing",  ""),
    ("06-roster-list.html",      "Roster List",             "Existing",  ""),
    ("07-roster-assign.html",    "Roster — Bulk Assign",    "Existing",  ""),
    ("08-shifts.html",           "Shifts",                  "Existing",  ""),
    ("09-employee-list.html",    "Employee List",           "Existing",  ""),
    ("10-employee-form.html",    "Employee Form",           "Existing",  "Edit & payroll link"),
    ("11-employee-enroll.html",  "Biometric Enrollment",    "Existing",  "Face + Fingerprint"),
    ("12-payroll-overview.html", "Payroll Overview",        "Updated",   "Net Payable column, Export button"),
    ("13-payroll-detail.html",   "Payroll Detail",          "Updated",   "Net Payable banner + Adjustments"),
    ("14-sync-status.html",      "Sync to ERP",             "Existing",  ""),
    ("15-manual-grants.html",    "Manual Entry Grants",     "Existing",  ""),
    ("16-data-cleanup.html",     "Data Cleanup",            "Existing",  ""),
    ("17-overtime-queue.html",   "Overtime Approvals",      "NEW",       "US-014/015/035/036 — auto-detect, admin approve"),
    ("18-user-management.html",  "User Management",         "NEW",       "US-006/007 — CRUD + password reset"),
    ("19-leave-management.html", "Leave Management",        "NEW",       "US-032 — requests, approval, balance"),
    ("20-payroll-export.html",   "Payroll Export",          "NEW",       "US-030 — XLSX/CSV with column picker"),
    ("21-override-request.html", "Override Request",        "Existing",  ""),
]

badges = {"Existing": "bg-secondary", "Updated": "bg-primary", "NEW": "bg-success"}

rows = ""
for i, (href, name, status, note) in enumerate(screens, 1):
    badge_cls = badges.get(status, "bg-secondary")
    note_html = f'<span class="text-muted small">{note}</span>' if note else ""
    rows += f"""<tr>
      <td class="text-muted small">{i:02d}</td>
      <td><a href="{href}" class="fw-semibold text-decoration-none">{name}</a></td>
      <td><span class="badge {badge_cls}">{status}</span></td>
      <td>{note_html}</td>
      <td><a href="{href}" class="btn btn-outline-primary btn-sm py-0">Open →</a></td>
    </tr>"""

logo_lg = LOGO_SVG.format(w=48, h=48)
index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>TiLedger — Wireframe Index</title>
  <link href="../static/vendor/bootstrap.min.css" rel="stylesheet">
  <link href="../static/vendor/bootstrap-icons.min.css" rel="stylesheet">
  <style>body{{font-family:'Segoe UI',system-ui,sans-serif}}.table th{{font-size:.78rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:#6c757d}}</style>
</head>
<body class="bg-light">
<div class="container py-5" style="max-width:860px">
  <div class="text-center mb-5">
    {logo_lg}
    <h2 class="fw-bold mt-3 mb-1">TiLedger Attendance System</h2>
    <p class="text-muted">Wireframe Index — {len(screens)} screens across all features</p>
    <div class="d-flex justify-content-center gap-2 mt-3">
      <span class="badge bg-secondary fs-6">Existing — no change</span>
      <span class="badge bg-primary fs-6">Updated — new functionality</span>
      <span class="badge bg-success fs-6">NEW — gap feature</span>
    </div>
  </div>
  <div class="card border-0 shadow-sm">
    <div class="card-body p-0">
      <table class="table mb-0">
        <thead><tr><th>#</th><th>Screen</th><th>Status</th><th>Notes</th><th></th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </div>
  <div class="text-center mt-4 text-muted small">
    <i class="bi bi-info-circle me-1"></i>
    Wireframes use local Bootstrap from <code>/static/vendor/</code> — open from project root.
  </div>
</div>
</body></html>"""

w("index.html", index_html)
print(f"\nDone — {len(screens)+1} files written to wireframes/")
