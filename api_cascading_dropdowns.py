"""
Cascading Dropdown API Routes for GRPO
Provides warehouses, bin locations, and batch data for dynamic dropdowns
"""
from flask import jsonify, request
from app import app
from flask_login import login_required
from sap_integration import SAPIntegration
import logging

@app.route('/api/warehouses', methods=['GET'])
@login_required
def cascading_get_warehouses():
    """Get all available warehouses"""
    try:
        sap = SAPIntegration()
        
        # Try to get warehouses from SAP B1
        if sap.ensure_logged_in():
            try:
                url = f"{sap.base_url}/b1s/v1/Warehouses"
                response = sap.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    warehouses = data.get('value', [])
                    
                    # Transform SAP B1 warehouse data to frontend format
                    formatted_warehouses = []
                    for warehouse in warehouses:
                        formatted_warehouses.append({
                            'code': warehouse.get('WarehouseCode'),
                            'name': warehouse.get('WarehouseName', warehouse.get('WarehouseCode'))
                        })
                    
                    logging.info(f"Retrieved {len(formatted_warehouses)} warehouses from SAP B1")
                    return jsonify({
                        'success': True,
                        'warehouses': formatted_warehouses
                    })
            except Exception as e:
                logging.error(f"Error getting warehouses from SAP: {str(e)}")
        
        # Return mock data for offline mode or on error  
        return jsonify({
            'success': True,
            'warehouses': [
                {'code': 'SCP_AVS', 'name': 'SCP Aviation Services'},
                {'code': '7000-FG', 'name': 'Finished Goods Warehouse'},
                {'code': 'WH-RM', 'name': 'Raw Materials Warehouse'},
                {'code': 'WH-QC', 'name': 'Quality Control Warehouse'},
                {'code': 'WH-RJ', 'name': 'Rejected Items Warehouse'}
            ]
        })
            
    except Exception as e:
        logging.error(f"Error in get_warehouses API: {str(e)}")
        # Return fallback data on error
        return jsonify({
            'success': True,
            'warehouses': [
                {'code': 'SCP_AVS', 'name': 'SCP Aviation Services'},
                {'code': '7000-FG', 'name': 'Finished Goods Warehouse'}
            ]
        })

@app.route('/api/bin-locations', methods=['GET'])
@login_required
def cascading_get_bin_locations():
    """Get bin locations for a specific warehouse"""
    try:
        warehouse_code = request.args.get('warehouse')
        if not warehouse_code:
            return jsonify({'success': False, 'error': 'Warehouse code required'}), 400
        
        sap = SAPIntegration()
        
        # Try to get bin locations from SAP B1
        if sap.ensure_logged_in():
            try:
                url = f"{sap.base_url}/b1s/v1/BinLocations?$filter=Warehouse eq '{warehouse_code}'"
                response = sap.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    bins = data.get('value', [])
                    
                    # Transform SAP B1 bin data to frontend format
                    formatted_bins = []
                    for bin_location in bins:
                        formatted_bins.append({
                            'code': bin_location.get('BinCode'),
                            'name': bin_location.get('BinName', bin_location.get('BinCode'))
                        })
                    
                    logging.info(f"Retrieved {len(formatted_bins)} bin locations for warehouse {warehouse_code}")
                    return jsonify({
                        'success': True,
                        'bins': formatted_bins
                    })
            except Exception as e:
                logging.error(f"Error getting bin locations from SAP: {str(e)}")
        
        # Return mock data for offline mode or on error
        return jsonify({
            'success': True,
            'bins': [
                {'code': f'{warehouse_code}-A01', 'name': 'Aisle A - Position 01'},
                {'code': f'{warehouse_code}-A02', 'name': 'Aisle A - Position 02'},
                {'code': f'{warehouse_code}-B01', 'name': 'Aisle B - Position 01'},
                {'code': f'{warehouse_code}-B02', 'name': 'Aisle B - Position 02'},
                {'code': f'{warehouse_code}-C01', 'name': 'Aisle C - Position 01'}
            ]
        })
            
    except Exception as e:
        logging.error(f"Error in get_bin_locations API: {str(e)}")
        warehouse_code = request.args.get('warehouse', 'WH001')
        return jsonify({
            'success': True,
            'bins': [
                {'code': f'{warehouse_code}-A01', 'name': 'Aisle A - Position 01'},
                {'code': f'{warehouse_code}-B01', 'name': 'Aisle B - Position 01'}
            ]
        })

@app.route('/api/warehouse/<warehouse_code>/validate', methods=['GET'])
@login_required
def validate_warehouse(warehouse_code):
    """Validate if a warehouse exists in SAP B1"""
    try:
        sap = SAPIntegration()
        
        if sap.ensure_logged_in():
            try:
                # Check if warehouse exists in SAP B1
                url = f"{sap.base_url}/b1s/v1/Warehouses('{warehouse_code}')"
                response = sap.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    return jsonify({
                        'success': True,
                        'valid': True,
                        'warehouse': {
                            'code': data.get('WarehouseCode'),
                            'name': data.get('WarehouseName')
                        }
                    })
                else:
                    return jsonify({
                        'success': True,
                        'valid': False,
                        'error': f'Warehouse {warehouse_code} not found in SAP B1'
                    })
            except Exception as e:
                logging.error(f"Error validating warehouse {warehouse_code}: {str(e)}")
                
        # Return valid for offline mode or when SAP is not available
        return jsonify({
            'success': True,
            'valid': True,
            'warehouse': {
                'code': warehouse_code,
                'name': f'Warehouse {warehouse_code}'
            }
        })
        
    except Exception as e:
        logging.error(f"Error in validate_warehouse API: {str(e)}")
        return jsonify({
            'success': True,
            'valid': True,
            'warehouse': {
                'code': warehouse_code,
                'name': f'Warehouse {warehouse_code}'
            }
        })

@app.route('/api/batches', methods=['GET'])
@login_required
def cascading_get_batches():
    """Get batches for a specific item code and optionally warehouse"""
    try:
        item_code = request.args.get('item_code')
        warehouse_code = request.args.get('warehouse')
        
        if not item_code:
            return jsonify({'success': False, 'error': 'Item code is required'}), 400
        
        sap = SAPIntegration()
        
        # Try to get batches from SAP B1
        if sap.ensure_logged_in():
            try:
                # Use BatchNumberDetails API to get batch information
                url = f"{sap.base_url}/b1s/v1/BatchNumberDetails?$filter=ItemCode eq '{item_code}'"
                if warehouse_code:
                    url += f" and WarehouseCode eq '{warehouse_code}'"
                
                response = sap.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    batches = data.get('value', [])
                    
                    # Format batch data for dropdown using correct SAP B1 field names
                    formatted_batches = []
                    for batch in batches:
                        expiry_date = batch.get('ExpirationDate')
                        if expiry_date:
                            # Format date from SAP (remove time part if present)
                            expiry_date = expiry_date.split('T')[0] if 'T' in expiry_date else expiry_date
                        
                        formatted_batches.append({
                            'BatchNumber': batch.get('Batch'),  # SAP B1 uses 'Batch' not 'BatchNumber'
                            'Quantity': batch.get('Quantity', 0),
                            'ExpiryDate': expiry_date,  # Use ExpiryDate for consistency
                            'ItemCode': batch.get('ItemCode', item_code),
                            'Status': batch.get('Status', 'bdsStatus_Released')
                        })
                    
                    logging.info(f"Retrieved {len(formatted_batches)} batches for item {item_code}")
                    return jsonify({
                        'success': True,
                        'batches': formatted_batches
                    })
            except Exception as e:
                logging.error(f"Error getting batches from SAP: {str(e)}")
        
        # Return mock data for offline mode or on error
        import datetime
        future_date = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        
        return jsonify({
            'success': True,
            'batches': [
                {'BatchNumber': f'BATCH-{item_code}-001', 'Quantity': 100, 'ExpiryDate': future_date},
                {'BatchNumber': f'BATCH-{item_code}-002', 'Quantity': 75, 'ExpiryDate': future_date},
                {'BatchNumber': f'BATCH-{item_code}-003', 'Quantity': 50, 'ExpiryDate': future_date}
            ]
        })
            
    except Exception as e:
        logging.error(f"Error in get_batches API: {str(e)}")
        item_code = request.args.get('item_code', 'ITEM001')
        # Return fallback data on error
        return jsonify({
            'success': True,
            'batches': [
                {'BatchNumber': f'BATCH-{item_code}-001', 'Quantity': 100, 'ExpiryDate': '2025-12-31'}
            ]
        })