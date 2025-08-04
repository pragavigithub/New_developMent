import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or "dev-secret-key-change-in-production"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database - Use SQLite for now
sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'wms.db')
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_path}"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["DB_TYPE"] = "sqlite"

# Ensure instance directory exists
os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
logging.info(f"SQLite database path: {sqlite_path}")

# Initialize extensions with app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# SAP B1 Configuration
app.config['SAP_B1_SERVER'] = os.environ.get('SAP_B1_SERVER', 'https://192.168.0.194:50000')
app.config['SAP_B1_USERNAME'] = os.environ.get('SAP_B1_USERNAME', 'manager')
app.config['SAP_B1_PASSWORD'] = os.environ.get('SAP_B1_PASSWORD', '1422')
app.config['SAP_B1_COMPANY_DB'] = os.environ.get('SAP_B1_COMPANY_DB', 'EINV-TESTDB-LIVE-HUST')

# Disable dual database support for now
app.config['DUAL_DB'] = None

# Import models after app is configured to avoid circular imports
import models
import models_extensions

with app.app_context():
    # Create all database tables first
    db.create_all()
    logging.info("Database tables created")
    
    # Create default data
    try:
        from models_extensions import Branch
        from werkzeug.security import generate_password_hash
        from models import User
        
        # Create default branch
        default_branch = Branch.query.filter_by(id='BR001').first()
        if not default_branch:
            default_branch = Branch()
            default_branch.id = 'BR001'
            default_branch.name = 'Main Branch'
            default_branch.description = 'Main Office Branch'
            default_branch.address = 'Main Office'
            default_branch.phone = '123-456-7890'
            default_branch.email = 'main@company.com'
            default_branch.manager_name = 'Branch Manager'
            default_branch.is_active = True
            default_branch.is_default = True
            db.session.add(default_branch)
            logging.info("Default branch created")
        
        # Create default admin user
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User()
            admin.username = 'admin'
            admin.email = 'admin@company.com'
            admin.password_hash = generate_password_hash('admin123')
            admin.first_name = 'System'
            admin.last_name = 'Administrator'
            admin.role = 'admin'
            admin.branch_id = 'BR001'
            admin.branch_name = 'Main Branch'
            admin.default_branch_id = 'BR001'
            admin.user_is_active = True
            admin.must_change_password = False
            db.session.add(admin)
            logging.info("Default admin user created")
            
        db.session.commit()
        logging.info("✅ Default data initialization completed")
        
    except Exception as e:
        logging.error(f"Error initializing default data: {e}")
        db.session.rollback()

logging.info("💡 Clean app configuration completed")