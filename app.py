import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
    logging.info("Environment variables loaded from .env file")
except ImportError:
    logging.info("python-dotenv not installed, using system environment variables")
except Exception as e:
    logging.warning(f"Could not load .env file: {e}")

# Configure logging
logging.basicConfig(level=logging.DEBUG)


class Base(DeclarativeBase):
    pass


# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get(
    "SESSION_SECRET") or "dev-secret-key-change-in-production"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration - prioritize MySQL for local development
database_url = None
db_type = None

# Check for MySQL configuration first (local development priority)
mysql_config = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': os.environ.get('MYSQL_PORT', '3306'),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', 'root@123'),
    'database': os.environ.get('MYSQL_DATABASE', 'wms_db_dev')
}

# Try MySQL first if any MySQL environment variables are set or DATABASE_URL contains mysql
database_url_env = os.environ.get("DATABASE_URL", "")
has_mysql_env = any(os.environ.get(key) for key in ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE'])
is_mysql_url = database_url_env.startswith("mysql")

if has_mysql_env or is_mysql_url:
    try:
        if is_mysql_url:
            database_url = database_url_env
            logging.info("✅ Using MySQL from DATABASE_URL environment variable")
        else:
            database_url = f"mysql+pymysql://{mysql_config['user']}:{mysql_config['password']}@{mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}"
            logging.info("✅ Using MySQL from individual environment variables")
        
        # Test MySQL connection
        from sqlalchemy import create_engine, text
        test_engine = create_engine(database_url, connect_args={'connect_timeout': 5})
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20
        }
        db_type = "mysql"
        logging.info("✅ MySQL database connection successful")
        
    except Exception as e:
        logging.warning(f"⚠️ MySQL connection failed: {e}")
        database_url = None

# Fallback to PostgreSQL (Replit environment)
if not database_url:
    database_url = os.environ.get("DATABASE_URL")
    if database_url and not database_url.startswith("mysql"):
        logging.info("✅ Using PostgreSQL database (Replit environment)")
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20
        }
        db_type = "postgresql"

# Final fallback to SQLite
if not database_url:
    logging.warning("⚠️ No database found, using SQLite fallback")
    sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'wms.db')
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_path}"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    db_type = "sqlite"
    # Ensure instance directory exists
    os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
    logging.info(f"SQLite database path: {sqlite_path}")

# Store database type for use in other modules
app.config["DB_TYPE"] = db_type

# Initialize extensions with app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore
login_manager.login_message = 'Please log in to access this page.'

# SAP B1 Configuration
app.config['SAP_B1_SERVER'] = os.environ.get('SAP_B1_SERVER',
                                             'https://192.168.0.194:50000')
app.config['SAP_B1_USERNAME'] = os.environ.get('SAP_B1_USERNAME', 'manager')
app.config['SAP_B1_PASSWORD'] = os.environ.get('SAP_B1_PASSWORD', '1422')
app.config['SAP_B1_COMPANY_DB'] = os.environ.get('SAP_B1_COMPANY_DB',
                                                 'EINV-TESTDB-LIVE-HUST')

# Import models after app is configured to avoid circular imports
import models
import models_extensions

with app.app_context():
    # Create all database tables first
    db.create_all()
    logging.info("Database tables created")
    
    # Create default data for PostgreSQL database
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
        # Continue with application startup

# Initialize dual database support for MySQL sync 
# Enable by default but fail gracefully if MySQL not available
try:
    from db_dual_support import init_dual_database
    dual_db = init_dual_database(app)
    app.config['DUAL_DB'] = dual_db
    logging.info("✅ Dual database support initialized for MySQL sync")
except Exception as e:
    logging.warning(f"⚠️ Dual database support not available: {e}")
    app.config['DUAL_DB'] = None
    logging.info("💡 MySQL sync disabled, using single database mode")

# Import routes to register them
import routes
