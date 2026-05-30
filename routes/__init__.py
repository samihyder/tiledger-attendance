from .auth_routes import auth_bp
from .main_routes import main_bp
from .employee_routes import employee_bp
from .roster_routes import roster_bp
from .attendance_routes import attendance_bp
from .sync_routes import sync_bp
from .payroll_routes import payroll_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(employee_bp,  url_prefix='/employees')
    app.register_blueprint(roster_bp,    url_prefix='/roster')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(sync_bp,      url_prefix='/sync')
    app.register_blueprint(payroll_bp,   url_prefix='/payroll')
