"""
Inventory Transfer Models
Contains all models related to inventory transfers between warehouses/bins
"""
from app import db
from datetime import datetime
from modules.shared.models import User

class InventoryTransfer(db.Model):
    """Main inventory transfer document header"""
    __tablename__ = 'inventory_transfers'
    
    id = db.Column(db.Integer, primary_key=True)
    transfer_request_number = db.Column(db.String(50), nullable=False)
    sap_document_number = db.Column(db.String(50))
    status = db.Column(db.String(20), default='draft')  # draft, submitted, qc_approved, posted, rejected, reopened
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    qc_approver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    qc_approved_at = db.Column(db.DateTime)
    qc_notes = db.Column(db.Text)
    from_warehouse = db.Column(db.String(10))
    to_warehouse = db.Column(db.String(10))
    transfer_type = db.Column(db.String(20), default='warehouse')  # warehouse, bin, emergency
    priority = db.Column(db.String(10), default='normal')  # low, normal, high, urgent
    reason_code = db.Column(db.String(20))  # adjustment, relocation, damaged, expired
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='inventory_transfers')
    qc_approver = db.relationship('User', foreign_keys=[qc_approver_id])
    items = db.relationship('InventoryTransferItem', backref='transfer', lazy=True, cascade='all, delete-orphan')
    history = db.relationship('TransferStatusHistory', backref='transfer', lazy=True, cascade='all, delete-orphan')

class InventoryTransferItem(db.Model):
    """Inventory transfer line items"""
    __tablename__ = 'inventory_transfer_items'
    
    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('inventory_transfers.id'), nullable=False)
    item_code = db.Column(db.String(50), nullable=False)
    item_name = db.Column(db.String(200))
    quantity = db.Column(db.Numeric(15, 3), nullable=False)
    unit_of_measure = db.Column(db.String(10))
    from_warehouse_code = db.Column(db.String(10))
    to_warehouse_code = db.Column(db.String(10))
    from_bin = db.Column(db.String(20))
    to_bin = db.Column(db.String(20))
    batch_number = db.Column(db.String(50))
    serial_number = db.Column(db.String(50))
    expiry_date = db.Column(db.Date)
    unit_price = db.Column(db.Numeric(15, 4))
    total_value = db.Column(db.Numeric(15, 2))
    qc_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    base_entry = db.Column(db.Integer)  # SAP Transfer Request DocEntry
    base_line = db.Column(db.Integer)   # SAP Transfer Request Line Number
    sap_line_number = db.Column(db.Integer)  # Line number in posted SAP document
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TransferStatusHistory(db.Model):
    """Track status changes for inventory transfers"""
    __tablename__ = 'transfer_status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('inventory_transfers.id'), nullable=False)
    previous_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    change_reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    changed_by = db.relationship('User', backref='status_changes')

class TransferRequest(db.Model):
    """SAP B1 Transfer Requests (for reference)"""
    __tablename__ = 'transfer_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    sap_doc_entry = db.Column(db.Integer, unique=True, nullable=False)
    request_number = db.Column(db.String(50), nullable=False)
    from_warehouse = db.Column(db.String(10))
    to_warehouse = db.Column(db.String(10))
    document_status = db.Column(db.String(20))  # Open, Closed
    total_lines = db.Column(db.Integer)
    total_quantity = db.Column(db.Numeric(15, 3))
    created_by = db.Column(db.String(50))
    document_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    comments = db.Column(db.Text)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_processed = db.Column(db.Boolean, default=False)