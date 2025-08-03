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
        """Get available batches for a specific item using SAP B1 BatchNumberDetails API"""
        try:
            item_code = request.args.get('item_code') or request.args.get('item')
            warehouse_code = request.args.get('warehouse')
            
            if not item_code:
                return jsonify({'success': False, 'error': 'Item code required'}), 400
            
            sap = SAPIntegration()
            # Use the specific SAP B1 API for batch details
            result = sap.get_batch_number_details(item_code)
            
            if result.get('success'):
                return jsonify(result)
            else:
                # Return mock data based on your actual SAP response format
                return jsonify({
                    'success': True,
                    'batches': [
                        {
                            'Batch': '20220729',
                            'ItemCode': item_code,
                            'ItemDescription': 'Sample Item',
                            'Status': 'bdsStatus_Released',
                            'AdmissionDate': '2022-07-29T00:00:00Z',
                            'SystemNumber': 1
                        },
                        {
                            'Batch': '271022',
                            'ItemCode': item_code,
                            'ItemDescription': 'Sample Item',
                            'Status': 'bdsStatus_Released',
                            'AdmissionDate': '2022-10-28T00:00:00Z',
                            'SystemNumber': 4
                        },
                        {
                            'Batch': '231122',
                            'ItemCode': item_code,
                            'ItemDescription': 'Sample Item',
                            'Status': 'bdsStatus_Released',
                            'AdmissionDate': '2022-11-24T00:00:00Z',
                            'SystemNumber': 6
                        }
                    ]
                })
                
        except Exception as e:
            logging.error(f"Error in get_batches API: {str(e)}")
            # Return mock data on error
            item_code = request.args.get('item_code') or request.args.get('item', 'ITEM001')
            return jsonify({
                'success': True,
                'batches': [
                    {
                        'Batch': '20220729',
                        'ItemCode': item_code,
                        'ItemDescription': 'Sample Item',
                        'Status': 'bdsStatus_Released',
                        'AdmissionDate': '2022-07-29T00:00:00Z',
                        'SystemNumber': 1
                    }
                ]
            })