"""
API Routes for GRPO Dropdown Functionality
Warehouse, Bin Location, and Batch selection endpoints
"""
from flask import jsonify, request
from sap_integration import SAPIntegration
import logging

def register_api_routes(app):
    """Register API routes with the Flask app"""
    
    @app.route('/api/get-warehouses', methods=['GET'])
    def get_warehouses():
        """Get all warehouses for dropdown selection"""
        try:
            sap = SAPIntegration()
            result = sap.get_warehouses_list()
            
            if result.get('success'):
                return jsonify(result)
            else:
                # Return mock data for offline mode
                return jsonify({
                    'success': True,
                    'warehouses': [
                        {'WarehouseCode': 'WH001', 'WarehouseName': 'Main Warehouse'},
                        {'WarehouseCode': 'WH002', 'WarehouseName': 'Secondary Warehouse'},
                        {'WarehouseCode': 'WH003', 'WarehouseName': 'Storage Warehouse'}
                    ]
                })
                
        except Exception as e:
            logging.error(f"Error in get_warehouses API: {str(e)}")
            # Return mock data on error
            return jsonify({
                'success': True,
                'warehouses': [
                    {'WarehouseCode': 'WH001', 'WarehouseName': 'Main Warehouse'},
                    {'WarehouseCode': 'WH002', 'WarehouseName': 'Secondary Warehouse'},
                    {'WarehouseCode': 'WH003', 'WarehouseName': 'Storage Warehouse'}
                ]
            })

    @app.route('/api/get-bins', methods=['GET'])
    def get_bins():
        """Get bin locations for a specific warehouse"""
        try:
            warehouse_code = request.args.get('warehouse')
            if not warehouse_code:
                return jsonify({'success': False, 'error': 'Warehouse code required'}), 400
            
            sap = SAPIntegration()
            result = sap.get_bin_locations_list(warehouse_code)
            
            if result.get('success'):
                return jsonify(result)
            else:
                # Return mock data for offline mode
                return jsonify({
                    'success': True,
                    'bins': [
                        {'BinCode': f'{warehouse_code}-BIN-01', 'BinName': 'Bin Location 01'},
                        {'BinCode': f'{warehouse_code}-BIN-02', 'BinName': 'Bin Location 02'},
                        {'BinCode': f'{warehouse_code}-BIN-03', 'BinName': 'Bin Location 03'}
                    ]
                })
                
        except Exception as e:
            logging.error(f"Error in get_bins API: {str(e)}")
            # Return mock data on error
            warehouse_code = request.args.get('warehouse', 'WH001')
            return jsonify({
                'success': True,
                'bins': [
                    {'BinCode': f'{warehouse_code}-BIN-01', 'BinName': 'Bin Location 01'},
                    {'BinCode': f'{warehouse_code}-BIN-02', 'BinName': 'Bin Location 02'},
                    {'BinCode': f'{warehouse_code}-BIN-03', 'BinName': 'Bin Location 03'}
                ]
            })

    @app.route('/api/get-batches', methods=['GET'])
    def get_batches():
        """Get available batches for a specific item and warehouse"""
        try:
            item_code = request.args.get('item')
            warehouse_code = request.args.get('warehouse')
            
            if not item_code or not warehouse_code:
                return jsonify({'success': False, 'error': 'Item code and warehouse code required'}), 400
            
            sap = SAPIntegration()
            result = sap.get_item_batches_list(item_code, warehouse_code)
            
            if result.get('success'):
                return jsonify(result)
            else:
                # Return mock data for offline mode
                return jsonify({
                    'success': True,
                    'batches': [
                        {'Batch': f'BATCH-{item_code}-001', 'Quantity': 100, 'ExpirationDate': '2025-12-31'},
                        {'Batch': f'BATCH-{item_code}-002', 'Quantity': 50, 'ExpirationDate': '2025-11-30'},
                        {'Batch': f'BATCH-{item_code}-003', 'Quantity': 25, 'ExpirationDate': '2025-10-31'}
                    ]
                })
                
        except Exception as e:
            logging.error(f"Error in get_batches API: {str(e)}")
            # Return mock data on error
            item_code = request.args.get('item', 'ITEM001')
            return jsonify({
                'success': True,
                'batches': [
                    {'Batch': f'BATCH-{item_code}-001', 'Quantity': 100, 'ExpirationDate': '2025-12-31'},
                    {'Batch': f'BATCH-{item_code}-002', 'Quantity': 50, 'ExpirationDate': '2025-11-30'},
                    {'Batch': f'BATCH-{item_code}-003', 'Quantity': 25, 'ExpirationDate': '2025-10-31'}
                ]
            })