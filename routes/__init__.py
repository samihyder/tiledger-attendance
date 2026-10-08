# The attendance app does check-in / check-out and face enrolment only
# (owner 2026-10-08). Staff, roster, rules, manual attendance, overtime,
# leave and payroll moved to the TiLedger ERP — the old blueprints in this
# folder are no longer registered.
from .erp_routes import erp_bp


def register_blueprints(app):
    app.register_blueprint(erp_bp)
