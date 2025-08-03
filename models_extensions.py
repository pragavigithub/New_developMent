from app import db
from datetime import datetime

class Branch(db.Model):
    """Branch/Location model for multi-branch support"""
    __tablename__ = 'branches'
    
    id = db.Column(db.String(10), primary_key=True)  # Branch code like 'BR001'
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)  # Match MySQL schema field name
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Make these fields optional and only include them if they exist in the schema
    address = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    manager_name = db.Column(db.String(100), nullable=True)
    is_default = db.Column(db.Boolean, default=False, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

class UserSession(db.Model):
    """Track user login sessions"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(256), nullable=False)
    branch_id = db.Column(db.String(10), nullable=True)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class PasswordResetToken(db.Model):
    """Password reset tokens for users"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(256), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Admin who created token
    created_at = db.Column(db.DateTime, default=datetime.utcnow)