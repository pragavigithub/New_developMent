"""
Inventory Transfer Routes
All routes related to inventory transfers between warehouses/bins
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from modules.inventory_transfer.models import InventoryTransfer, InventoryTransferItem, TransferStatusHistory
from modules.shared.models import User
import logging
from datetime import datetime

transfer_bp = Blueprint('inventory_transfer', __name__, url_prefix='/inventory_transfer')

@transfer_bp.route('/')
@login_required
def index():
    """Inventory Transfer main page - list all transfers for current user"""
    if not current_user.has_permission('inventory_transfer'):
        flash('Access denied - Inventory Transfer permissions required', 'error')
        return redirect(url_for('dashboard'))
    
    transfers = InventoryTransfer.query.filter_by(user_id=current_user.id).order_by(InventoryTransfer.created_at.desc()).all()
    return render_template('inventory_transfer/inventory_transfer.html', transfers=transfers)

@transfer_bp.route('/detail/<int:transfer_id>')
@login_required
def detail(transfer_id):
    """Inventory Transfer detail page"""
    transfer = InventoryTransfer.query.get_or_404(transfer_id)
    
    # Check permissions
    if transfer.user_id != current_user.id and current_user.role not in ['admin', 'manager', 'qc']:
        flash('Access denied - You can only view your own transfers', 'error')
        return redirect(url_for('inventory_transfer.index'))
    
    return render_template('inventory_transfer/inventory_transfer_detail.html', transfer=transfer)

@transfer_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new inventory transfer"""
    if not current_user.has_permission('inventory_transfer'):
        flash('Access denied - Inventory Transfer permissions required', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        transfer_request_number = request.form.get('transfer_request_number')
        from_warehouse = request.form.get('from_warehouse')
        to_warehouse = request.form.get('to_warehouse')
        
        if not transfer_request_number:
            flash('Transfer request number is required', 'error')
            return redirect(url_for('inventory_transfer.create'))
        
        # Check if transfer already exists
        existing_transfer = InventoryTransfer.query.filter_by(
            transfer_request_number=transfer_request_number, 
            user_id=current_user.id
        ).first()
        
        if existing_transfer:
            flash(f'Transfer already exists for request {transfer_request_number}', 'warning')
            return redirect(url_for('inventory_transfer.detail', transfer_id=existing_transfer.id))
        
        # Create new transfer
        transfer = InventoryTransfer(
            transfer_request_number=transfer_request_number,
            user_id=current_user.id,
            from_warehouse=from_warehouse,
            to_warehouse=to_warehouse,
            status='draft'
        )
        
        db.session.add(transfer)
        db.session.commit()
        
        # Log status change
        log_status_change(transfer.id, None, 'draft', current_user.id, 'Transfer created')
        
        logging.info(f"✅ Inventory Transfer created for request {transfer_request_number} by user {current_user.username}")
        flash(f'Inventory Transfer created for request {transfer_request_number}', 'success')
        return redirect(url_for('inventory_transfer.detail', transfer_id=transfer.id))
    
    return render_template('inventory_transfer/create_transfer.html')

@transfer_bp.route('/<int:transfer_id>/submit', methods=['POST'])
@login_required
def submit(transfer_id):
    """Submit transfer for QC approval"""
    try:
        transfer = InventoryTransfer.query.get_or_404(transfer_id)
        
        # Check permissions
        if transfer.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        if transfer.status != 'draft':
            return jsonify({'success': False, 'error': 'Only draft transfers can be submitted'}), 400
        
        if not transfer.items:
            return jsonify({'success': False, 'error': 'Cannot submit transfer without items'}), 400
        
        # Update status
        old_status = transfer.status
        transfer.status = 'submitted'
        transfer.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Log status change
        log_status_change(transfer_id, old_status, 'submitted', current_user.id, 'Transfer submitted for QC approval')
        
        logging.info(f"📤 Inventory Transfer {transfer_id} submitted for QC approval")
        return jsonify({
            'success': True,
            'message': 'Transfer submitted for QC approval',
            'status': 'submitted'
        })
        
    except Exception as e:
        logging.error(f"Error submitting transfer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@transfer_bp.route('/<int:transfer_id>/qc_approve', methods=['POST'])
@login_required
def qc_approve(transfer_id):
    """QC approve transfer and post to SAP B1"""
    try:
        transfer = InventoryTransfer.query.get_or_404(transfer_id)
        
        # Check QC permissions
        if not current_user.has_permission('qc_dashboard') and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'QC permissions required'}), 403
        
        if transfer.status != 'submitted':
            return jsonify({'success': False, 'error': 'Only submitted transfers can be approved'}), 400
        
        # Get QC notes
        qc_notes = request.json.get('qc_notes', '') if request.is_json else request.form.get('qc_notes', '')
        
        # Mark items as approved
        for item in transfer.items:
            item.qc_status = 'approved'
        
        # Update transfer status
        old_status = transfer.status
        transfer.status = 'qc_approved'
        transfer.qc_approver_id = current_user.id
        transfer.qc_approved_at = datetime.utcnow()
        transfer.qc_notes = qc_notes
        
        # Here you would integrate with SAP B1 to create Stock Transfer
        # For now, we'll simulate success
        transfer.sap_document_number = f"ST-{transfer_id}-{datetime.now().strftime('%Y%m%d')}"
        
        db.session.commit()
        
        # Log status change
        log_status_change(transfer_id, old_status, 'qc_approved', current_user.id, f'Transfer QC approved and posted to SAP B1 as {transfer.sap_document_number}')
        
        logging.info(f"✅ Inventory Transfer {transfer_id} QC approved and posted to SAP B1")
        return jsonify({
            'success': True,
            'message': f'Transfer QC approved and posted to SAP B1 as {transfer.sap_document_number}',
            'sap_document_number': transfer.sap_document_number
        })
        
    except Exception as e:
        logging.error(f"Error approving transfer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@transfer_bp.route('/<int:transfer_id>/qc_reject', methods=['POST'])
@login_required
def qc_reject(transfer_id):
    """QC reject transfer"""
    try:
        transfer = InventoryTransfer.query.get_or_404(transfer_id)
        
        # Check QC permissions
        if not current_user.has_permission('qc_dashboard') and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'QC permissions required'}), 403
        
        if transfer.status != 'submitted':
            return jsonify({'success': False, 'error': 'Only submitted transfers can be rejected'}), 400
        
        # Get rejection reason
        qc_notes = request.json.get('qc_notes', '') if request.is_json else request.form.get('qc_notes', '')
        
        if not qc_notes:
            return jsonify({'success': False, 'error': 'Rejection reason is required'}), 400
        
        # Mark items as rejected
        for item in transfer.items:
            item.qc_status = 'rejected'
        
        # Update transfer status
        old_status = transfer.status
        transfer.status = 'rejected'
        transfer.qc_approver_id = current_user.id
        transfer.qc_approved_at = datetime.utcnow()
        transfer.qc_notes = qc_notes
        
        db.session.commit()
        
        # Log status change
        log_status_change(transfer_id, old_status, 'rejected', current_user.id, f'Transfer rejected by QC: {qc_notes}')
        
        logging.info(f"❌ Inventory Transfer {transfer_id} rejected by QC")
        return jsonify({
            'success': True,
            'message': 'Transfer rejected by QC',
            'status': 'rejected'
        })
        
    except Exception as e:
        logging.error(f"Error rejecting transfer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@transfer_bp.route('/<int:transfer_id>/reopen', methods=['POST'])
@login_required
def reopen(transfer_id):
    """Reopen a rejected transfer"""
    try:
        transfer = InventoryTransfer.query.get_or_404(transfer_id)
        
        # Check permissions
        if transfer.user_id != current_user.id and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'Access denied - You can only reopen your own transfers'}), 403
        
        if transfer.status != 'rejected':
            return jsonify({'success': False, 'error': 'Only rejected transfers can be reopened'}), 400
        
        # Reset transfer to draft status
        old_status = transfer.status
        transfer.status = 'draft'
        transfer.qc_approver_id = None
        transfer.qc_approved_at = None
        transfer.qc_notes = None
        transfer.updated_at = datetime.utcnow()
        
        # Reset all items to pending
        for item in transfer.items:
            item.qc_status = 'pending'
        
        db.session.commit()
        
        # Log status change
        log_status_change(transfer_id, old_status, 'draft', current_user.id, 'Transfer reopened and reset to draft status')
        
        logging.info(f"🔄 Inventory Transfer {transfer_id} reopened and reset to draft status")
        return jsonify({
            'success': True,
            'message': 'Transfer reopened successfully. You can now edit and resubmit it.',
            'status': 'draft'
        })
        
    except Exception as e:
        logging.error(f"Error reopening transfer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def log_status_change(transfer_id, previous_status, new_status, changed_by_id, notes=None):
    """Log status change to history table"""
    try:
        history = TransferStatusHistory(
            transfer_id=transfer_id,
            previous_status=previous_status,
            new_status=new_status,
            changed_by_id=changed_by_id,
            notes=notes
        )
        db.session.add(history)
        db.session.commit()
    except Exception as e:
        logging.error(f"Error logging status change: {str(e)}")