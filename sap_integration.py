import requests
import json
import logging
from datetime import datetime
from app import app
import urllib.parse
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SAPIntegration:

    def __init__(self):
        self.base_url = app.config['SAP_B1_SERVER']
        self.username = app.config['SAP_B1_USERNAME']
        self.password = app.config['SAP_B1_PASSWORD']
        self.company_db = app.config['SAP_B1_COMPANY_DB']
        self.session_id = None
        self.session = requests.Session()
        self.session.verify = False  # For development, in production use proper SSL
        self.is_offline = False

        # Cache for frequently accessed data
        self._warehouse_cache = {}
        self._bin_cache = {}
        self._branch_cache = {}
        self._item_cache = {}
        self._batch_cache = {}

    def login(self):
        """Login to SAP B1 Service Layer"""
        # Check if SAP configuration exists
        if not self.base_url or not self.username or not self.password or not self.company_db:
            logging.warning(
                "SAP B1 configuration not complete. Running in offline mode.")
            return False

        login_url = f"{self.base_url}/b1s/v1/Login"
        login_data = {
            "UserName": self.username,
            "Password": self.password,
            "CompanyDB": self.company_db
        }

        try:
            response = self.session.post(login_url,
                                         json=login_data,
                                         timeout=10)
            if response.status_code == 200:
                self.session_id = response.json().get('SessionId')
                logging.info("Successfully logged in to SAP B1")
                return True
            else:
                logging.warning(
                    f"SAP B1 login failed: {response.text}. Running in offline mode."
                )
                return False
        except Exception as e:
            logging.warning(
                f"SAP B1 login error: {str(e)}. Running in offline mode.")
            return False

    def ensure_logged_in(self):
        """Ensure we have a valid session"""
        if not self.session_id:
            return self.login()
        return True

    def get_inventory_transfer_request(self, doc_num):
        """Get specific inventory transfer request from SAP B1"""
        if not self.ensure_logged_in():
            logging.warning(
                "SAP B1 not available, returning mock transfer request for validation"
            )
            # Return mock data for offline mode to allow testing
            return {
                'DocNum':
                int(doc_num) if doc_num.isdigit() else doc_num,
                'DocEntry':
                123,
                'DocStatus':
                'bost_Open',
                'DocumentStatus':
                'bost_Open',
                'FromWarehouse':
                'WH001',
                'ToWarehouse':
                'WH002',
                'StockTransferLines': [{
                    'LineNum': 0,
                    'ItemCode': 'ITM001',
                    'ItemDescription': 'Sample Item',
                    'Quantity': 10,
                    'FromWarehouseCode': 'WH001',
                    'WarehouseCode': 'WH002'
                }]
            }

        try:
            # Try multiple endpoints to find the transfer request
            endpoints_to_try = [
                f"InventoryTransferRequests?$filter=DocNum eq {doc_num}",
                f"InventoryTransferRequests?$filter=DocNum eq '{doc_num}'",
                f"StockTransfers?$filter=DocNum eq {doc_num}",
                f"StockTransfers?$filter=DocNum eq '{doc_num}'"
            ]

            for endpoint in endpoints_to_try:
                url = f"{self.base_url}/b1s/v1/{endpoint}"
                logging.info(f"🔍 Trying SAP B1 API: {url}")

                response = self.session.get(url)
                logging.info(f"📡 Response status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    transfers = data.get('value', [])
                    logging.info(
                        f"📦 Found {len(transfers)} transfer requests for DocNum {doc_num}"
                    )

                    if transfers:
                        transfer_data = transfers[0]
                        doc_status = transfer_data.get(
                            'DocumentStatus',
                            transfer_data.get('DocStatus', ''))
                        logging.info(
                            f"✅ Transfer request found: {transfer_data.get('DocNum')} - Status: {doc_status}"
                        )

                        # Normalize the response structure for consistent access
                        if 'StockTransferLines' not in transfer_data and 'DocumentLines' in transfer_data:
                            transfer_data[
                                'StockTransferLines'] = transfer_data[
                                    'DocumentLines']

                        # Ensure consistent status field
                        if 'DocumentStatus' in transfer_data and 'DocStatus' not in transfer_data:
                            transfer_data['DocStatus'] = transfer_data[
                                'DocumentStatus']

                        # Log the full structure for debugging
                        logging.info(
                            f"📋 Transfer Data: DocNum={transfer_data.get('DocNum')}, FromWarehouse={transfer_data.get('FromWarehouse')}, ToWarehouse={transfer_data.get('ToWarehouse')}"
                        )

                        return transfer_data
                    else:
                        logging.info(f"No results from endpoint: {endpoint}")
                        continue
                else:
                    logging.warning(
                        f"API call failed for {endpoint}: {response.status_code}"
                    )
                    continue

            # If no endpoint worked, return None
            logging.warning(
                f"❌ No transfer request found for DocNum {doc_num} in any endpoint"
            )
            return None

        except Exception as e:
            logging.error(
                f"❌ Error getting inventory transfer request: {str(e)}")
            return None

    def get_bins(self, warehouse_code):
        """Get bins for a specific warehouse"""
        if not self.ensure_logged_in():
            return []

        try:
            url = f"{self.base_url}/b1s/v1/BinLocations?$filter=Warehouse eq '{warehouse_code}'"
            response = self.session.get(url)

            if response.status_code == 200:
                data = response.json()
                bins = data.get('value', [])

                # Transform the data to match our expected format
                formatted_bins = []
                for bin_data in bins:
                    formatted_bins.append({
                        'BinCode':
                        bin_data.get('BinCode'),
                        'Description':
                        bin_data.get('Description', ''),
                        'Warehouse':
                        bin_data.get('Warehouse'),
                        'Active':
                        bin_data.get('Active', 'Y')
                    })

                return formatted_bins
            else:
                logging.error(f"Failed to get bins: {response.status_code}")
                return []
        except Exception as e:
            logging.error(f"Error getting bins: {str(e)}")
            return []

    def get_purchase_order(self, po_number):
        """Get purchase order details from SAP B1"""
        if not self.ensure_logged_in():
            # Return mock data for offline mode
            return {
                'DocNum':
                po_number,
                'CardCode':
                'V001',  # Sample vendor code
                'CardName':
                'Sample Vendor Ltd',
                'DocDate':
                '2025-01-08',
                'DocTotal':
                15000.00,
                'DocumentLines': [{
                    'LineNum': 0,
                    'ItemCode': 'ITM001',
                    'ItemDescription': 'Sample Item 1',
                    'Quantity': 100,
                    'OpenQuantity': 100,
                    'RemainingOpenQuantity': 100,
                    'Price': 50.00,
                    'UoMCode': 'EA',
                    'WarehouseCode': 'WH01',
                    'LineStatus': 'bost_Open'
                }, {
                    'LineNum': 1,
                    'ItemCode': 'ITM002',
                    'ItemDescription': 'Sample Item 2',
                    'Quantity': 50,
                    'OpenQuantity': 30,
                    'RemainingOpenQuantity': 30,
                    'Price': 200.00,
                    'UoMCode': 'KGS',
                    'WarehouseCode': 'WH01',
                    'LineStatus': 'bost_Open'
                }]
            }

        url = f"{self.base_url}/b1s/v1/PurchaseOrders?$filter=DocNum eq {po_number}"

        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['value']:
                    return data['value'][0]
            return None
        except Exception as e:
            logging.warning(
                f"Error fetching PO {po_number}: {str(e)}. Using offline mode."
            )
            # Return mock data on error
            return {
                'DocNum':
                po_number,
                'CardCode':
                'V001',
                'CardName':
                'Sample Vendor Ltd',
                'DocDate':
                '2025-01-08',
                'DocTotal':
                15000.00,
                'DocumentLines': [{
                    'LineNum': 0,
                    'ItemCode': 'ITM001',
                    'ItemDescription': 'Sample Item 1',
                    'Quantity': 100,
                    'OpenQuantity': 100,
                    'RemainingOpenQuantity': 100,
                    'Price': 50.00,
                    'UoMCode': 'EA',
                    'WarehouseCode': 'WH01',
                    'LineStatus': 'bost_Open'
                }]
            }

    def get_purchase_order_items(self, po_number):
        """Get purchase order line items"""
        try:
            po_data = self.get_purchase_order(po_number)
            if po_data:
                return po_data.get('DocumentLines', [])
        except Exception as e:
            logging.warning(
                f"Unable to fetch PO items for {po_number}: {str(e)}. Running in offline mode."
            )
        return []

    def get_item_master(self, item_code):
        """Get item master data from SAP B1"""
        if not self.ensure_logged_in():
            return None

        url = f"{self.base_url}/b1s/v1/Items('{item_code}')"

        try:
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logging.error(f"Error fetching item {item_code}: {str(e)}")
            return None

    def get_warehouse_bins(self, warehouse_code):
        """Get bins for a warehouse"""
        if not self.ensure_logged_in():
            return []

        url = f"{self.base_url}/b1s/v1/BinLocations?$filter=WhsCode eq '{warehouse_code}'"

        try:
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get('value', [])
            return []
        except Exception as e:
            logging.error(
                f"Error fetching bins for warehouse {warehouse_code}: {str(e)}"
            )
            return []

    def get_bin_items(self, bin_code):
        """Enhanced bin scanning with detailed item information using your exact API patterns"""
        if not self.ensure_logged_in():
            logging.warning("SAP B1 not available, returning mock bin data")
            return self._get_mock_bin_items(bin_code)

        try:
            logging.info(f"🔍 Enhanced bin scanning for: {bin_code}")
            
            # Step 1: Get bin information using your exact API pattern
            bin_info_url = f"{self.base_url}/b1s/v1/BinLocations?$filter=BinCode eq '{bin_code}'"
            logging.debug(f"[DEBUG] Calling URL: {bin_info_url}")
            bin_response = self.session.get(bin_info_url)
            logging.debug(f"[DEBUG] Status code: {bin_response.status_code}")

            if bin_response.status_code != 200:
                logging.warning(f"❌ Bin {bin_code} not found: {bin_response.status_code}")
                return []

            bin_data = bin_response.json().get('value', [])
            if not bin_data:
                logging.warning(f"❌ Bin {bin_code} does not exist")
                return []

            bin_info = bin_data[0]
            warehouse_code = bin_info.get('Warehouse', '')
            abs_entry = bin_info.get('AbsEntry', 0)

            logging.info(f"✅ Found bin {bin_code} in warehouse {warehouse_code} (AbsEntry: {abs_entry})")

            # Step 2: Get warehouse business place info using your exact API pattern
            warehouse_info_url = (f"{self.base_url}/b1s/v1/Warehouses?"
                                f"$select=BusinessPlaceID,WarehouseCode,DefaultBin&"
                                f"$filter=WarehouseCode eq '{warehouse_code}'")
            logging.debug(f"[DEBUG] Calling URL: {warehouse_info_url}")
            warehouse_response = self.session.get(warehouse_info_url)
            logging.debug(f"[DEBUG] Status code: {warehouse_response.status_code}")
            
            business_place_id = 0
            if warehouse_response.status_code == 200:
                warehouse_data = warehouse_response.json().get('value', [])
                if warehouse_data:
                    business_place_id = warehouse_data[0].get('BusinessPlaceID', 0)
                    logging.info(f"✅ Warehouse {warehouse_code} BusinessPlaceID: {business_place_id}")

            # Step 3: Get warehouse items using your exact crossjoin API pattern
            crossjoin_url = (f"{self.base_url}/b1s/v1/$crossjoin(Items,Items/ItemWarehouseInfoCollection)?"
                           f"$expand=Items($select=ItemCode,ItemName,QuantityOnStock),"
                           f"Items/ItemWarehouseInfoCollection($select=InStock,Ordered,StandardAveragePrice)&"
                           f"$filter=Items/ItemCode eq Items/ItemWarehouseInfoCollection/ItemCode and "
                           f"Items/ItemWarehouseInfoCollection/WarehouseCode eq '{warehouse_code}'")

            logging.debug(f"[DEBUG] Calling URL: {crossjoin_url}")
            headers = {"Prefer": "odata.maxpagesize=300"}
            crossjoin_response = self.session.get(crossjoin_url,headers=headers)
            logging.debug(f"[DEBUG] Status code: {crossjoin_response.status_code}")
            logging.debug(f"[DEBUG] Response text: {crossjoin_response.text[:300]}")

            if crossjoin_response.status_code != 200:
                logging.error(f"❌ Failed to get warehouse items: {crossjoin_response.status_code}")
                return []

            # Step 4: Process crossjoin results and enhance with batch details
            formatted_items = []
            crossjoin_data = crossjoin_response.json().get('value', [])
            
            logging.info(f"📦 Found {len(crossjoin_data)} items in warehouse {warehouse_code}")

            for item_data in crossjoin_data:
                try:
                    item_info = item_data.get('Items', {})
                    warehouse_info = item_data.get('Items/ItemWarehouseInfoCollection', {})
                    
                    item_code = item_info.get('ItemCode', '')
                    if not item_code:
                        continue

                    # Step 5: Get batch details for this item using your exact API pattern
                    batch_details = self._get_item_batch_details(item_code)
                    
                    # Skip items with zero InStock quantity
                    in_stock_qty = float(warehouse_info.get('InStock', 0))
                    if in_stock_qty <= 0:
                        logging.debug(f"⏭️ Skipping item {item_code} - InStock quantity is {in_stock_qty}")
                        continue
                    
                    # Create enhanced item record with all details
                    enhanced_item = {
                        'ItemCode': item_code,
                        'ItemName': item_info.get('ItemName', ''),
                        'UoM': item_info.get('InventoryUoM', 'EA'),
                        'QuantityOnStock': float(item_info.get('QuantityOnStock', 0)),
                        'OnHand': in_stock_qty,
                        'OnStock': in_stock_qty,
                        'InStock': in_stock_qty,
                        'Ordered': float(warehouse_info.get('Ordered', 0)),
                        'StandardAveragePrice': float(warehouse_info.get('StandardAveragePrice', 0)),
                        'WarehouseCode': warehouse_code,
                        'Warehouse': warehouse_code,
                        'BinCode': bin_code,
                        'BinAbsEntry': abs_entry,
                        'BusinessPlaceID': business_place_id,
                        'BatchDetails': batch_details
                    }

                    # Add batch summary for display
                    if batch_details:
                        enhanced_item['BatchCount'] = len(batch_details)
                        enhanced_item['BatchNumbers'] = [b.get('Batch', '') for b in batch_details]
                        enhanced_item['ExpiryDates'] = [b.get('ExpirationDate') for b in batch_details if b.get('ExpirationDate')]
                        enhanced_item['AdmissionDates'] = [b.get('AdmissionDate') for b in batch_details if b.get('AdmissionDate')]
                        # Use first batch info for main display
                        if batch_details:
                            first_batch = batch_details[0]
                            enhanced_item['BatchNumber'] = first_batch.get('Batch', '')
                            enhanced_item['Batch'] = first_batch.get('Batch', '')
                            enhanced_item['Status'] = first_batch.get('Status', 'bdsStatus_Released')
                            enhanced_item['AdmissionDate'] = first_batch.get('AdmissionDate', '')
                            enhanced_item['ExpirationDate'] = first_batch.get('ExpirationDate', '')
                            enhanced_item['ExpiryDate'] = first_batch.get('ExpirationDate', '')
                    else:
                        enhanced_item['BatchCount'] = 0
                        enhanced_item['BatchNumbers'] = []
                        enhanced_item['ExpiryDates'] = []
                        enhanced_item['AdmissionDates'] = []
                        enhanced_item['BatchNumber'] = ''
                        enhanced_item['Batch'] = ''
                        enhanced_item['Status'] = 'No Batch'
                        enhanced_item['AdmissionDate'] = ''
                        enhanced_item['ExpirationDate'] = ''
                        enhanced_item['ExpiryDate'] = ''

                    # Add legacy fields for compatibility
                    enhanced_item['Quantity'] = enhanced_item['OnHand']
                    enhanced_item['ItemDescription'] = enhanced_item['ItemName']

                    formatted_items.append(enhanced_item)
                    
                    logging.debug(f"✅ Enhanced item: {item_code} - OnHand: {enhanced_item['OnHand']}, Batches: {enhanced_item['BatchCount']}")

                except Exception as item_error:
                    logging.error(f"❌ Error processing item: {str(item_error)}")
                    continue

            logging.info(f"🎯 Successfully enhanced {len(formatted_items)} items for bin {bin_code}")
            return formatted_items

        except Exception as e:
            logging.error(f"❌ Error in enhanced bin scanning: {str(e)}")
            return []

    def _get_item_batch_details(self, item_code):
        """Get batch details for a specific item using your exact BatchNumberDetails API pattern"""
        try:
            batch_url = f"{self.base_url}/b1s/v1/BatchNumberDetails?$filter=ItemCode eq '{item_code}'"
            logging.debug(f"[DEBUG] Getting batch details for {item_code}")
            
            batch_response = self.session.get(batch_url)
            if batch_response.status_code == 200:
                batch_data = batch_response.json().get('value', [])
                logging.debug(f"✅ Found {len(batch_data)} batches for item {item_code}")
                return batch_data
            else:
                logging.debug(f"⚠️ No batch details found for item {item_code}")
                return []
                
        except Exception as e:
            logging.error(f"❌ Error getting batch details for {item_code}: {str(e)}")
            return []

    def _get_mock_bin_items(self, bin_code):
        """Mock data for offline mode with enhanced structure matching your API responses"""
        # Only return items with InStock > 0 to match the filtering logic
        return [
            {
                'ItemCode': 'CO0726Y',
                'ItemName': 'COATED LOWER PLATE',
                'ItemDescription': 'COATED LOWER PLATE',
                'UoM': 'EA',
                'QuantityOnStock': 100.0,
                'OnHand': 95.0,
                'OnStock': 95.0,
                'InStock': 95.0,
                'Ordered': 0.0,
                'StandardAveragePrice': 125.50,
                'WarehouseCode': '7000-FG',
                'Warehouse': '7000-FG',
                'BinCode': bin_code,
                'BinAbsEntry': 1,
                'BusinessPlaceID': 5,
                'BatchCount': 1,
                'BatchNumbers': ['20220729'],
                'ExpiryDates': [None],
                'AdmissionDates': ['2022-07-29T00:00:00Z'],
                'BatchNumber': '20220729',
                'Batch': '20220729',
                'Status': 'bdsStatus_Released',
                'AdmissionDate': '2022-07-29T00:00:00Z',
                'ExpirationDate': None,
                'ExpiryDate': None,
                'Quantity': 95.0,
                'BatchDetails': [{
                    'DocEntry': 1,
                    'ItemCode': 'CO0726Y',
                    'ItemDescription': 'COATED LOWER PLATE',
                    'Status': 'bdsStatus_Released',
                    'Batch': '20220729',
                    'AdmissionDate': '2022-07-29T00:00:00Z',
                    'ExpirationDate': None,
                    'SystemNumber': 1
                }]
            },
            {
                'ItemCode': 'CO0098Y',
                'ItemName': 'Big Aluminium Insert Coated RR AC0101',
                'ItemDescription': 'Big Aluminium Insert Coated RR AC0101',
                'UoM': 'PCS',
                'QuantityOnStock': 50.0,
                'OnHand': 48.0,
                'OnStock': 48.0,
                'InStock': 48.0,
                'Ordered': 10.0,
                'StandardAveragePrice': 89.75,
                'WarehouseCode': '7000-FG',
                'Warehouse': '7000-FG',
                'BinCode': bin_code,
                'BinAbsEntry': 1,
                'BusinessPlaceID': 5,
                'BatchCount': 1,
                'BatchNumbers': ['20220729'],
                'ExpiryDates': [None],
                'AdmissionDates': ['2022-07-29T00:00:00Z'],
                'BatchNumber': '20220729',
                'Batch': '20220729',
                'Status': 'bdsStatus_Released',
                'AdmissionDate': '2022-07-29T00:00:00Z',
                'ExpirationDate': None,
                'ExpiryDate': None,
                'Quantity': 48.0,
                'BatchDetails': [{
                    'DocEntry': 2,
                    'ItemCode': 'CO0098Y',
                    'ItemDescription': 'Big Aluminium Insert Coated RR AC0101',
                    'Status': 'bdsStatus_Released',
                    'Batch': '20220729',
                    'AdmissionDate': '2022-07-29T00:00:00Z',
                    'ExpirationDate': None,
                    'SystemNumber': 1
                }]
            }
        ]

    def get_available_bins(self, warehouse_code):
        """Get available bins for a warehouse"""
        if not self.ensure_logged_in():
            # Return fallback bins if SAP is not available
            return []

        try:
            # Get bins from SAP B1
            url = f"{self.base_url}/b1s/v1/BinLocations"
            params = {
                '$filter': f"Warehouse eq '{warehouse_code}' and Active eq 'Y'"
            }

            response = self.session.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                bins = []
                for bin_data in data.get('value', []):
                    bins.append({
                        'BinCode': bin_data.get('BinCode'),
                        'Description': bin_data.get('Description', '')
                    })
                return bins
            else:
                logging.error(f"Failed to get bins from SAP: {response.text}")
                return []

        except Exception as e:
            logging.error(f"Error getting bins from SAP: {str(e)}")
            return []

    def create_goods_receipt_po(self, grpo_document):
        """Create Goods Receipt PO in SAP B1"""
        if not self.ensure_logged_in():
            # Return success for offline mode
            import random
            return {
                'success': True,
                'error': None,
                'document_number': f'GRPO-{random.randint(100000, 999999)}'
            }

        url = f"{self.base_url}/b1s/v1/PurchaseDeliveryNotes"

        # Get PO data to ensure we have correct supplier code
        po_data = self.get_purchase_order(grpo_document.po_number)
        if not po_data:
            return {
                'success': False,
                'error': f'Purchase Order {grpo_document.po_number} not found'
            }

        supplier_code = po_data.get('CardCode')
        if not supplier_code:
            return {'success': False, 'error': 'Supplier code not found in PO'}

        # Build document lines
        document_lines = []
        for item in grpo_document.items:
            line = {
                "ItemCode": item.item_code,
                "Quantity": item.received_quantity,
                "UnitOfMeasure": item.unit_of_measure,
                "WarehouseCode": "WH01",  # Default warehouse
                "BinCode": item.bin_location
            }

            # Add batch information if available
            if item.batch_number:
                line["BatchNumbers"] = [{
                    "BatchNumber":
                    item.batch_number,
                    "Quantity":
                    item.received_quantity,
                    "ExpiryDate":
                    item.expiration_date.strftime('%Y-%m-%d')
                    if item.expiration_date else None
                }]

            # Add serial numbers if needed
            if item.generated_barcode:
                line["SerialNumbers"] = [{
                    "SerialNumber": item.generated_barcode,
                    "Quantity": 1
                }]

            document_lines.append(line)

        grpo_data = {
            "CardCode": supplier_code,
            "DocDate": grpo_document.created_at.strftime('%Y-%m-%d'),
            "DocumentLines": document_lines,
            "Comments":
            f"Created from WMS GRPO {grpo_document.id} by {grpo_document.user.username}",
            "U_WMS_GRPO_ID":
            str(grpo_document.id)  # Custom field to track WMS document
        }

        try:
            response = self.session.post(url, json=grpo_data)
            if response.status_code == 201:
                result = response.json()
                return {
                    'success': True,
                    'document_number': result.get('DocNum')
                }
            else:
                return {
                    'success': False,
                    'error': f"SAP B1 error: {response.text}"
                }
        except Exception as e:
            logging.error(f"Error creating GRPO in SAP B1: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_bin_abs_entry(self, bin_code, warehouse_code):
        """Get bin AbsEntry from SAP B1 for bin allocation"""
        if not self.ensure_logged_in():
            return None

        try:
            url = f"{self.base_url}/b1s/v1/BinLocations?$filter=BinCode eq '{bin_code}' and Warehouse eq '{warehouse_code}'"
            response = self.session.get(url)

            if response.status_code == 200:
                bins = response.json().get('value', [])
                if bins:
                    return bins[0].get('AbsEntry')
            return None
        except Exception as e:
            logging.error(
                f"Error getting bin AbsEntry for {bin_code}: {str(e)}")
            return None

    def get_batch_numbers(self, item_code):
        """Get batch numbers for specific item from SAP B1 BatchNumberDetails"""
        # Check cache first
        if item_code in self._batch_cache:
            return self._batch_cache[item_code]

        if not self.ensure_logged_in():
            logging.warning(
                f"SAP B1 not available, returning mock batch data for {item_code}"
            )
            # Return mock batch data for offline mode
            mock_batches = [{
                "Batch": f"BATCH-{item_code}-001",
                "ItemCode": item_code,
                "Status": "bdsStatus_Released",
                "ExpirationDate": None,
                "ManufacturingDate": None,
                "AdmissionDate": "2025-01-01T00:00:00Z"
            }, {
                "Batch": f"BATCH-{item_code}-002",
                "ItemCode": item_code,
                "Status": "bdsStatus_Released",
                "ExpirationDate": None,
                "ManufacturingDate": None,
                "AdmissionDate": "2025-01-01T00:00:00Z"
            }]
            self._batch_cache[item_code] = mock_batches
            return mock_batches

        try:
            url = f"{self.base_url}/b1s/v1/BatchNumberDetails?$filter=ItemCode eq '{item_code}' and Status eq 'bdsStatus_Released'"
            logging.info(f"🔍 Fetching batch numbers from SAP B1: {url}")

            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                batches = data.get('value', [])
                logging.info(
                    f"📦 Found {len(batches)} batch numbers for item {item_code}"
                )

                # Cache the results
                self._batch_cache[item_code] = batches
                return batches
            else:
                logging.warning(
                    f"Failed to fetch batch numbers: {response.status_code} - {response.text}"
                )
                return []
        except Exception as e:
            logging.error(
                f"Error fetching batch numbers for {item_code}: {str(e)}")
            return []

    def get_item_batches(self, item_code, warehouse_code=''):
        """Get available batches for an item with stock information"""
        logging.info(
            f"🔍 Getting batches for item {item_code} in warehouse {warehouse_code}"
        )

        if not self.ensure_logged_in():
            logging.warning("⚠️ No SAP B1 session - returning mock batch data")
            return self._get_mock_batch_data(item_code)

        try:
            # SAP B1 API to get batch details
            filter_clause = f"ItemCode eq '{item_code}'"
            if warehouse_code:
                filter_clause += f" and Warehouse eq '{warehouse_code}'"

            url = f"{self.base_url}/b1s/v1/BatchNumberDetails?$filter={filter_clause}&$select=BatchNumber,OnHandQuantity,ExpiryDate,ManufacturingDate,Warehouse"

            response = self.session.get(url)

            if response.status_code == 200:
                data = response.json()
                batches = data.get('value', [])
                logging.info(
                    f"✅ Found {len(batches)} batches for item {item_code}")
                return batches
            else:
                logging.error(
                    f"❌ SAP B1 API error getting batches: {response.status_code}"
                )
                return self._get_mock_batch_data(item_code)

        except Exception as e:
            logging.error(f"❌ Error getting batches from SAP B1: {str(e)}")
            return self._get_mock_batch_data(item_code)

    def get_batch_stock(self, item_code, batch_number, warehouse_code=''):
        """Get stock level for a specific batch"""
        logging.info(
            f"📊 Getting stock for batch {batch_number} of item {item_code}")

        if not self.ensure_logged_in():
            logging.warning("⚠️ No SAP B1 session - returning mock stock data")
            return {
                'OnHandQuantity': 100,
                'Warehouse': warehouse_code,
                'ExpiryDate': '2025-12-31',
                'ManufacturingDate': '2025-01-01'
            }

        try:
            filter_clause = f"ItemCode eq '{item_code}' and BatchNumber eq '{batch_number}'"
            if warehouse_code:
                filter_clause += f" and Warehouse eq '{warehouse_code}'"

            url = f"{self.base_url}/b1s/v1/BatchNumberDetails?$filter={filter_clause}"

            response = self.session.get(url)

            if response.status_code == 200:
                data = response.json()
                batches = data.get('value', [])
                if batches:
                    logging.info(
                        f"✅ Found stock for batch {batch_number}: {batches[0].get('OnHandQuantity', 0)}"
                    )
                    return batches[0]
                else:
                    logging.warning(
                        f"⚠️ Batch {batch_number} not found for item {item_code}"
                    )
                    return None
            else:
                logging.error(
                    f"❌ SAP B1 API error getting batch stock: {response.status_code}"
                )
                return {
                    'OnHandQuantity': 100,
                    'Warehouse': warehouse_code,
                    'ExpiryDate': '2025-12-31',
                    'ManufacturingDate': '2025-01-01'
                }

        except Exception as e:
            logging.error(f"❌ Error getting batch stock from SAP B1: {str(e)}")
            return {
                'OnHandQuantity': 100,
                'Warehouse': warehouse_code,
                'ExpiryDate': '2025-12-31',
                'ManufacturingDate': '2025-01-01'
            }

    def _get_mock_batch_data(self, item_code):
        """Return mock batch data for offline testing"""
        return [{
            'BatchNumber': 'A22',
            'OnHandQuantity': 66.0,
            'ExpiryDate': '2025-12-31T00:00:00Z',
            'ManufacturingDate': '2025-01-01T00:00:00Z',
            'Warehouse': 'ORD-CHN'
        }, {
            'BatchNumber': 'B23',
            'OnHandQuantity': 45.0,
            'ExpiryDate': '2026-06-30T00:00:00Z',
            'ManufacturingDate': '2025-06-01T00:00:00Z',
            'Warehouse': 'ORD-CHN'
        }, {
            'BatchNumber': 'C24',
            'OnHandQuantity': 32.0,
            'ExpiryDate': '2026-12-31T00:00:00Z',
            'ManufacturingDate': '2025-12-01T00:00:00Z',
            'Warehouse': 'ORD-CHN'
        }]

    def create_inventory_transfer(self, transfer_document):
        """Create Stock Transfer in SAP B1 with correct JSON structure"""
        if not self.ensure_logged_in():
            logging.warning(
                "SAP B1 not available, simulating transfer creation for testing"
            )
            return {
                'success': True,
                'document_number': f'ST-{transfer_document.id}'
            }

        url = f"{self.base_url}/b1s/v1/StockTransfers"

        # Get transfer request data for BaseEntry reference
        transfer_request_data = self.get_inventory_transfer_request(
            transfer_document.transfer_request_number)
        base_entry = transfer_request_data.get(
            'DocEntry') if transfer_request_data else None

        # Build stock transfer lines with enhanced structure
        stock_transfer_lines = []
        for index, item in enumerate(transfer_document.items):
            # Get item details for accurate UoM and pricing
            item_details = self.get_item_details(item.item_code)

            # Use actual item UoM if available
            actual_uom = item_details.get(
                'InventoryUoM',
                item.unit_of_measure) if item_details else item.unit_of_measure

            # Find corresponding line in transfer request for price info
            price = 0
            unit_price = 0
            uom_entry = None
            base_line = index

            if transfer_request_data and 'StockTransferLines' in transfer_request_data:
                for req_line in transfer_request_data['StockTransferLines']:
                    if req_line.get('ItemCode') == item.item_code:
                        price = req_line.get('Price', 0)
                        unit_price = req_line.get('UnitPrice', price)
                        uom_entry = req_line.get('UoMEntry')
                        base_line = req_line.get('LineNum', index)
                        break

            line = {
                "LineNum": index,
                "ItemCode": item.item_code,
                "Quantity": float(item.quantity),
                "WarehouseCode": transfer_document.to_warehouse,
                "FromWarehouseCode": transfer_document.from_warehouse,
                "UoMCode": actual_uom
            }

            # Add BaseEntry and BaseLine if available (reference to transfer request)
            if base_entry:
                line["BaseEntry"] = base_entry
                line["BaseLine"] = base_line
                line["BaseType"] = "1250000001"  # oInventoryTransferRequest

            # Add pricing if available
            if price > 0:
                line["Price"] = price
                line["UnitPrice"] = unit_price

            # Add UoMEntry if available
            if uom_entry:
                line["UoMEntry"] = uom_entry

            # Add batch numbers if present
            if item.batch_number:
                line["BatchNumbers"] = [{
                    "BaseLineNumber": index,
                    "BatchNumberProperty": item.batch_number,
                    "Quantity": float(item.quantity)
                }]

            # Add bin allocation if bins are specified
            # if item.from_bin or item.to_bin:
            #     line["BinAllocation"] = []
            #
            #     if item.from_bin:
            #         line["BinAllocation"].append({
            #             "BinActionType": "batFromWarehouse",
            #             "BinAbsEntry": self.get_bin_abs_entry(item.from_bin, transfer_document.from_warehouse),
            #             "Quantity": float(item.quantity)
            #         })
            #
            #     if item.to_bin:
            #         line["BinAllocation"].append({
            #             "BinActionType": "batToWarehouse",
            #             "BinAbsEntry": self.get_bin_abs_entry(item.to_bin, transfer_document.to_warehouse),
            #             "Quantity": float(item.quantity)
            #         })

            stock_transfer_lines.append(line)

        transfer_data = {
            "DocDate": datetime.now().strftime('%Y-%m-%d'),
            "Comments":
            f"QC Approved WMS Transfer {transfer_document.id} by {transfer_document.qc_approver.username if transfer_document.qc_approver else 'System'}",
            "FromWarehouse": transfer_document.from_warehouse,
            "ToWarehouse": transfer_document.to_warehouse,
            "StockTransferLines": stock_transfer_lines
        }
        print(transfer_data)
        # Log the JSON payload for debugging
        logging.info(f"📤 Sending stock transfer to SAP B1:")
        logging.info(f"JSON payload: {json.dumps(transfer_data, indent=2)}")

        try:
            response = self.session.post(url, json=transfer_data)
            logging.info(f"📡 SAP B1 response status: {response.status_code}")

            if response.status_code == 201:
                result = response.json()
                logging.info(
                    f"✅ Stock transfer created successfully: {result.get('DocNum')}"
                )
                return {
                    'success': True,
                    'document_number': result.get('DocNum')
                }
            else:
                error_msg = f"SAP B1 error: {response.text}"
                logging.error(
                    f"❌ Failed to create stock transfer: {error_msg}")
                return {'success': False, 'error': error_msg}
        except Exception as e:
            logging.error(
                f"❌ Error creating stock transfer in SAP B1: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_item_details(self, item_code):
        """Get detailed item information from SAP B1"""
        if not self.ensure_logged_in():
            return {
                'ItemCode': item_code,
                'ItemName': f'Mock Item {item_code}',
                'UoMGroupEntry': 1,
                'UoMCode': 'EA',
                'UoMName': 'Each',
                'InventoryUoM': 'EA',
                'DefaultWarehouse': 'WH001',
                'ItemType': 'itItems',
                'ManageSerialNumbers': 'N',
                'ManageBatchNumbers': 'N'
            }

        try:
            url = f"{self.base_url}/b1s/v1/Items('{item_code}')"
            response = self.session.get(url)

            if response.status_code == 200:
                item_data = response.json()

                # Get UoM details
                uom_group_entry = item_data.get('UoMGroupEntry')
                inventory_uom = item_data.get('InventoryUoM', 'EA')

                return {
                    'ItemCode': item_data.get('ItemCode'),
                    'ItemName': item_data.get('ItemName'),
                    'UoMGroupEntry': uom_group_entry,
                    'UoMCode': inventory_uom,
                    'InventoryUoM': inventory_uom,
                    'DefaultWarehouse': item_data.get('DefaultWarehouse'),
                    'ItemType': item_data.get('ItemType'),
                    'ManageSerialNumbers':
                    item_data.get('ManageSerialNumbers'),
                    'ManageBatchNumbers': item_data.get('ManageBatchNumbers')
                }
            else:
                logging.error(
                    f"Failed to get item details for {item_code}: {response.text}"
                )
                return None
        except Exception as e:
            logging.error(
                f"Error getting item details for {item_code}: {str(e)}")
            return None

    def create_inventory_counting(self, count_document):
        """Create Inventory Counting Document in SAP B1"""
        if not self.ensure_logged_in():
            return {'success': False, 'error': 'Not logged in to SAP B1'}

        url = f"{self.base_url}/b1s/v1/InventoryCountings"

        # Build document lines
        document_lines = []
        for item in count_document.items:
            line = {
                "ItemCode": item.item_code,
                "CountedQuantity": item.counted_quantity,
                "BinCode": count_document.bin_location
            }
            if item.batch_number:
                line["BatchNumber"] = item.batch_number
            document_lines.append(line)

        count_data = {
            "CountDate": datetime.now().strftime('%Y-%m-%d'),
            "CountTime": datetime.now().strftime('%H:%M:%S'),
            "Remarks": f"Created from WMS Count {count_document.id}",
            "InventoryCountingLines": document_lines
        }

        try:
            response = self.session.post(url, json=count_data)
            if response.status_code == 201:
                result = response.json()
                return {
                    'success': True,
                    'document_number': result.get('DocNum')
                }
            else:
                return {
                    'success': False,
                    'error': f"SAP B1 error: {response.text}"
                }
        except Exception as e:
            logging.error(
                f"Error creating inventory counting in SAP B1: {str(e)}")
            return {'success': False, 'error': str(e)}

    def sync_warehouses(self):
        """Sync warehouses from SAP B1 to local database"""
        if not self.ensure_logged_in():
            logging.warning("Cannot sync warehouses - SAP B1 not available")
            return False

        try:
            url = f"{self.base_url}/b1s/v1/Warehouses"
            response = self.session.get(url)

            if response.status_code == 200:
                warehouses = response.json().get('value', [])

                from app import db

                # Clear cache and update database
                self._warehouse_cache = {}

                for wh in warehouses:
                    # Check if warehouse exists in branches table
                    existing = db.session.execute(
                        db.text("SELECT id FROM branches WHERE id = :id"), {
                            "id": wh.get('WarehouseCode')
                        }).fetchone()

                    if not existing:
                        # Insert new warehouse as branch - use compatible SQL
                        import os
                        from app import app
                        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')

                        if 'postgresql' in db_uri.lower(
                        ) or 'mysql' in db_uri.lower():
                            insert_sql = """
                                INSERT INTO branches (id, name, address, is_active, created_at, updated_at)
                                VALUES (:id, :name, :address, :is_active, NOW(), NOW())
                            """
                        else:
                            insert_sql = """
                                INSERT INTO branches (id, name, address, is_active, created_at, updated_at)
                                VALUES (:id, :name, :address, :is_active, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """

                        db.session.execute(
                            db.text(insert_sql), {
                                "id": wh.get('WarehouseCode'),
                                "name": wh.get('WarehouseName', ''),
                                "address": wh.get('Street', ''),
                                "is_active": wh.get('Inactive') != 'Y'
                            })
                    else:
                        # Update existing warehouse - use compatible SQL
                        import os
                        from app import app
                        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')

                        if 'postgresql' in db_uri.lower(
                        ) or 'mysql' in db_uri.lower():
                            update_sql = """
                                UPDATE branches SET 
                                    name = :name, 
                                    address = :address, 
                                    is_active = :is_active,
                                    updated_at = NOW()
                                WHERE id = :id
                            """
                        else:
                            update_sql = """
                                UPDATE branches SET 
                                    name = :name, 
                                    address = :address, 
                                    is_active = :is_active,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = :id
                            """

                        db.session.execute(
                            db.text(update_sql), {
                                "id": wh.get('WarehouseCode'),
                                "name": wh.get('WarehouseName', ''),
                                "address": wh.get('Street', ''),
                                "is_active": wh.get('Inactive') != 'Y'
                            })

                    # Cache warehouse data
                    self._warehouse_cache[wh.get('WarehouseCode')] = {
                        'WarehouseCode': wh.get('WarehouseCode'),
                        'WarehouseName': wh.get('WarehouseName'),
                        'Address': wh.get('Street'),
                        'Active': wh.get('Inactive') != 'Y'
                    }

                db.session.commit()
                logging.info(
                    f"Synced {len(warehouses)} warehouses from SAP B1")
                return True

        except Exception as e:
            logging.error(f"Error syncing warehouses: {str(e)}")
            return False

    def sync_bins(self, warehouse_code=None):
        """Sync bin locations from SAP B1"""
        if not self.ensure_logged_in():
            logging.warning("Cannot sync bins - SAP B1 not available")
            return False

        try:
            # Get bins for specific warehouse or all warehouses
            if warehouse_code:
                url = f"{self.base_url}/b1s/v1/BinLocations?$filter=Warehouse eq '{warehouse_code}'"
            else:
                url = f"{self.base_url}/b1s/v1/BinLocations"

            response = self.session.get(url)

            if response.status_code == 200:
                bins = response.json().get('value', [])

                # Create bins table if not exists - use compatible SQL
                from app import db, app
                import os

                db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')

                if 'postgresql' in db_uri.lower():
                    create_table_sql = """
                        CREATE TABLE IF NOT EXISTS bin_locations (
                            id SERIAL PRIMARY KEY,
                            bin_code VARCHAR(50) NOT NULL,
                            warehouse_code VARCHAR(10) NOT NULL,
                            bin_name VARCHAR(100),
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW(),
                            UNIQUE(bin_code, warehouse_code)
                        )
                    """
                elif 'mysql' in db_uri.lower():
                    create_table_sql = """
                        CREATE TABLE IF NOT EXISTS bin_locations (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            bin_code VARCHAR(50) NOT NULL,
                            warehouse_code VARCHAR(10) NOT NULL,
                            bin_name VARCHAR(100),
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW() ON UPDATE NOW(),
                            UNIQUE KEY unique_bin_warehouse (bin_code, warehouse_code)
                        )
                    """
                else:
                    create_table_sql = """
                        CREATE TABLE IF NOT EXISTS bin_locations (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            bin_code VARCHAR(50) NOT NULL,
                            warehouse_code VARCHAR(10) NOT NULL,
                            bin_name VARCHAR(100),
                            is_active BOOLEAN DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(bin_code, warehouse_code)
                        )
                    """

                db.session.execute(db.text(create_table_sql))

                # Clear cache
                self._bin_cache = {}

                for bin_data in bins:
                    bin_code = bin_data.get('BinCode')
                    wh_code = bin_data.get(
                        'Warehouse')  # Use 'Warehouse' not 'WarehouseCode'

                    if bin_code and wh_code:
                        # Upsert bin location - use database-specific syntax
                        if 'postgresql' in db_uri.lower():
                            upsert_sql = """
                                INSERT INTO bin_locations (bin_code, warehouse_code, bin_name, is_active, created_at, updated_at)
                                VALUES (:bin_code, :warehouse_code, :bin_name, :is_active, NOW(), NOW())
                                ON CONFLICT (bin_code, warehouse_code) 
                                DO UPDATE SET 
                                    bin_name = EXCLUDED.bin_name,
                                    is_active = EXCLUDED.is_active,
                                    updated_at = NOW()
                            """
                        elif 'mysql' in db_uri.lower():
                            upsert_sql = """
                                INSERT INTO bin_locations (bin_code, warehouse_code, bin_name, is_active, created_at, updated_at)
                                VALUES (:bin_code, :warehouse_code, :bin_name, :is_active, NOW(), NOW())
                                ON DUPLICATE KEY UPDATE 
                                    bin_name = VALUES(bin_name),
                                    is_active = VALUES(is_active),
                                    updated_at = NOW()
                            """
                        else:
                            # SQLite - use INSERT OR REPLACE
                            upsert_sql = """
                                INSERT OR REPLACE INTO bin_locations (bin_code, warehouse_code, bin_name, is_active, created_at, updated_at)
                                VALUES (:bin_code, :warehouse_code, :bin_name, :is_active, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """

                        db.session.execute(
                            db.text(upsert_sql), {
                                "bin_code": bin_code,
                                "warehouse_code": wh_code,
                                "bin_name": bin_data.get('Description', ''),
                                "is_active": bin_data.get('Inactive') != 'Y'
                            })

                        # Cache bin data
                        cache_key = f"{wh_code}:{bin_code}"
                        self._bin_cache[cache_key] = {
                            'BinCode': bin_code,
                            'WarehouseCode': wh_code,
                            'Description': bin_data.get('Description', ''),
                            'Active': bin_data.get('Inactive') != 'Y'
                        }

                db.session.commit()
                logging.info(f"Synced {len(bins)} bin locations from SAP B1")
                return True

        except Exception as e:
            logging.error(f"Error syncing bins: {str(e)}")
            return False

    def sync_business_partners(self):
        """Sync business partners (suppliers/customers) from SAP B1"""
        if not self.ensure_logged_in():
            logging.warning(
                "Cannot sync business partners - SAP B1 not available")
            return False

        try:
            # Get suppliers and customers
            url = f"{self.base_url}/b1s/v1/BusinessPartners?$filter=CardType eq 'cSupplier' or CardType eq 'cCustomer'"
            response = self.session.get(url)

            if response.status_code == 200:
                partners = response.json().get('value', [])

                from app import db, app

                # Create business_partners table if not exists - use database-specific syntax
                db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')

                if 'postgresql' in db_uri.lower():
                    create_table_sql = """
                        CREATE TABLE IF NOT EXISTS business_partners (
                            id SERIAL PRIMARY KEY,
                            card_code VARCHAR(50) UNIQUE NOT NULL,
                            card_name VARCHAR(200) NOT NULL,
                            card_type VARCHAR(20) NOT NULL,
                            phone VARCHAR(50),
                            email VARCHAR(100),
                            address TEXT,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """
                elif 'mysql' in db_uri.lower():
                    create_table_sql = """
                        CREATE TABLE IF NOT EXISTS business_partners (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            card_code VARCHAR(50) UNIQUE NOT NULL,
                            card_name VARCHAR(200) NOT NULL,
                            card_type VARCHAR(20) NOT NULL,
                            phone VARCHAR(50),
                            email VARCHAR(100),
                            address TEXT,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW() ON UPDATE NOW()
                        )
                    """
                else:
                    create_table_sql = """
                        CREATE TABLE IF NOT EXISTS business_partners (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            card_code VARCHAR(50) UNIQUE NOT NULL,
                            card_name VARCHAR(200) NOT NULL,
                            card_type VARCHAR(20) NOT NULL,
                            phone VARCHAR(50),
                            email VARCHAR(100),
                            address TEXT,
                            is_active BOOLEAN DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """

                db.session.execute(db.text(create_table_sql))

                for partner in partners:
                    card_code = partner.get('CardCode')
                    if card_code:
                        # Use database-specific upsert syntax
                        if 'postgresql' in db_uri.lower():
                            upsert_sql = """
                                INSERT INTO business_partners (card_code, card_name, card_type, phone, email, address, is_active, created_at, updated_at)
                                VALUES (:card_code, :card_name, :card_type, :phone, :email, :address, :is_active, NOW(), NOW())
                                ON CONFLICT (card_code) 
                                DO UPDATE SET 
                                    card_name = EXCLUDED.card_name,
                                    card_type = EXCLUDED.card_type,
                                    phone = EXCLUDED.phone,
                                    email = EXCLUDED.email,
                                    address = EXCLUDED.address,
                                    is_active = EXCLUDED.is_active,
                                    updated_at = NOW()
                            """
                        elif 'mysql' in db_uri.lower():
                            upsert_sql = """
                                INSERT INTO business_partners (card_code, card_name, card_type, phone, email, address, is_active, created_at, updated_at)
                                VALUES (:card_code, :card_name, :card_type, :phone, :email, :address, :is_active, NOW(), NOW())
                                ON DUPLICATE KEY UPDATE 
                                    card_name = VALUES(card_name),
                                    card_type = VALUES(card_type),
                                    phone = VALUES(phone),
                                    email = VALUES(email),
                                    address = VALUES(address),
                                    is_active = VALUES(is_active),
                                    updated_at = NOW()
                            """
                        else:
                            # SQLite - use INSERT OR REPLACE
                            upsert_sql = """
                                INSERT OR REPLACE INTO business_partners (card_code, card_name, card_type, phone, email, address, is_active, created_at, updated_at)
                                VALUES (:card_code, :card_name, :card_type, :phone, :email, :address, :is_active, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """

                        db.session.execute(
                            db.text(upsert_sql), {
                                "card_code": card_code,
                                "card_name": partner.get('CardName', ''),
                                "card_type": partner.get('CardType', ''),
                                "phone": partner.get('Phone1', ''),
                                "email": partner.get('EmailAddress', ''),
                                "address": partner.get('Address', ''),
                                "is_active": partner.get('Valid') == 'Y'
                            })

                db.session.commit()
                logging.info(
                    f"Synced {len(partners)} business partners from SAP B1")
                return True

        except Exception as e:
            logging.error(f"Error syncing business partners: {str(e)}")
            return False

    def get_warehouse_business_place_id(self, warehouse_code):
        """Get BusinessPlaceID for a warehouse from SAP B1"""
        if not self.ensure_logged_in():
            return 5  # Default fallback

        try:
            url = f"{self.base_url}/b1s/v1/Warehouses"
            params = {
                '$select': 'BusinessPlaceID',
                '$filter': f"WarehouseCode eq '{warehouse_code}'"
            }

            response = self.session.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get('value') and len(data['value']) > 0:
                    return data['value'][0].get('BusinessPlaceID', 5)
            return 5  # Default fallback

        except Exception as e:
            logging.error(
                f"Error getting BusinessPlaceID for warehouse {warehouse_code}: {str(e)}"
            )
            return 5  # Default fallback

    def generate_external_reference_number(self, grpo_document):
        """Generate unique external reference number for Purchase Delivery Note"""
        from datetime import datetime

        # Get current date in YYYYMMDD format
        date_str = datetime.now().strftime('%Y%m%d')

        # Get sequence number for today
        try:
            from app import db

            # Create sequence table if not exists
            create_sequence_table = """
                CREATE TABLE IF NOT EXISTS pdn_sequence (
                    date_key VARCHAR(8) PRIMARY KEY,
                    sequence_number INTEGER DEFAULT 0
                )
            """
            db.session.execute(db.text(create_sequence_table))

            # Get or create sequence for today
            result = db.session.execute(
                db.text(
                    "SELECT sequence_number FROM pdn_sequence WHERE date_key = :date_key"
                ), {
                    "date_key": date_str
                }).fetchone()

            if result:
                sequence_num = result[0] + 1
                db.session.execute(
                    db.text(
                        "UPDATE pdn_sequence SET sequence_number = :seq WHERE date_key = :date_key"
                    ), {
                        "seq": sequence_num,
                        "date_key": date_str
                    })
            else:
                sequence_num = 1
                db.session.execute(
                    db.text(
                        "INSERT INTO pdn_sequence (date_key, sequence_number) VALUES (:date_key, :seq)"
                    ), {
                        "date_key": date_str,
                        "seq": sequence_num
                    })

            db.session.commit()

            # Format: EXT-REF-YYYYMMDD-XXX
            return f"EXT-REF-{date_str}-{sequence_num:03d}"

        except Exception as e:
            logging.error(
                f"Error generating external reference number: {str(e)}")
            # Fallback to timestamp-based reference
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            return f"EXT-REF-{timestamp}"

    def create_purchase_delivery_note(self, grpo_document):
        """Create Purchase Delivery Note in SAP B1 with exact JSON structure specified"""
        if not self.ensure_logged_in():
            # Return success for offline mode
            import random
            return {
                'success': True,
                'error': None,
                'document_number': f'PDN-{random.randint(100000, 999999)}'
            }

        # Get PO data first to ensure proper field mapping
        po_data = self.get_purchase_order(grpo_document.po_number)
        if not po_data:
            return {
                'success':
                False,
                'error':
                f'Purchase Order {grpo_document.po_number} not found in SAP B1'
            }

        # Extract required fields from PO with correct date formatting
        card_code = po_data.get('CardCode')
        po_doc_entry = po_data.get('DocEntry')

        # Use PO dates in correct format (YYYY-MM-DD, not with time)
        doc_date = po_data.get('DocDate', '2024-02-24')
        doc_due_date = po_data.get('DocDueDate', '2024-03-05')

        # Ensure dates are in YYYY-MM-DD format (remove time if present)
        if 'T' in doc_date:
            doc_date = doc_date.split('T')[0]
        if 'T' in doc_due_date:
            doc_due_date = doc_due_date.split('T')[0]

        if not card_code or not po_doc_entry:
            return {
                'success': False,
                'error': 'Missing CardCode or PO DocEntry from SAP B1'
            }

        # Generate unique external reference number
        external_ref = self.generate_external_reference_number(grpo_document)

        # Get first warehouse code from PO DocumentLines to determine BusinessPlaceID
        first_warehouse_code = None
        if grpo_document.items:
            for item in grpo_document.items:
                if item.qc_status == 'approved':
                    # Find matching PO line to get proper warehouse code
                    for po_line in po_data.get('DocumentLines', []):
                        if po_line.get('ItemCode') == item.item_code:
                            first_warehouse_code = po_line.get(
                                'WarehouseCode') or po_line.get('WhsCode')
                            if first_warehouse_code:
                                break
                    if first_warehouse_code:
                        break

        # Get BusinessPlaceID for the warehouse
        business_place_id = self.get_warehouse_business_place_id(
            first_warehouse_code) if first_warehouse_code else 5

        # Build document lines with exact structure
        document_lines = []
        line_number = 0

        for item in grpo_document.items:
            # Only include QC approved items
            if item.qc_status != 'approved':
                continue

            # Find matching PO line for proper mapping
            po_line_num = None
            po_line_data = None
            for po_line in po_data.get('DocumentLines', []):
                if po_line.get('ItemCode') == item.item_code:
                    po_line_num = po_line.get('LineNum')
                    po_line_data = po_line
                    break

            if po_line_num is None:
                logging.warning(
                    f"PO line not found for item {item.item_code} in PO {grpo_document.po_number}"
                )
                continue  # Skip items not found in PO

            # Get exact warehouse code from PO line instead of bin location
            po_warehouse_code = None
            if po_line_data:
                po_warehouse_code = po_line_data.get(
                    'WarehouseCode') or po_line_data.get('WhsCode')

            # Use PO warehouse code, or fallback to extracted from bin location
            warehouse_code = po_warehouse_code or (item.bin_location.split(
                '-')[0] if '-' in item.bin_location else item.bin_location[:4])

            # Build line with exact SAP B1 structure
            line = {
                "BaseType": 22,  # Constant value for Purchase Order
                "BaseEntry": po_doc_entry,
                "BaseLine": po_line_num,
                "ItemCode": item.item_code,
                "Quantity": item.received_quantity,
                "WarehouseCode": warehouse_code
            }

            # Add batch information in EXACT format as user specified
            if item.batch_number:
                # Format expiry date properly
                expiry_date = doc_date + "T00:00:00Z"  # Default to PO date
                if item.expiration_date:
                    if hasattr(item.expiration_date, 'strftime'):
                        expiry_date = item.expiration_date.strftime(
                            '%Y-%m-%dT%H:%M:%SZ')
                    else:
                        # If it's a string, ensure proper format
                        expiry_date = str(item.expiration_date)
                        if 'T' not in expiry_date:
                            expiry_date += "T00:00:00Z"

                batch_info = {
                    "BatchNumber":
                    item.batch_number,
                    "Quantity":
                    item.received_quantity,
                    "BaseLineNumber":
                    line_number,
                    "ManufacturerSerialNumber":
                    getattr(item, 'manufacturer_serial', None) or "MFG-SN-001",
                    "InternalSerialNumber":
                    getattr(item, 'internal_serial', None) or "INT-SN-001",
                    "ExpiryDate":
                    expiry_date
                }

                line["BatchNumbers"] = [batch_info]

            document_lines.append(line)
            line_number += 1

        if not document_lines:
            return {
                'success':
                False,
                'error':
                'No approved items found for Purchase Delivery Note creation'
            }

        # Build Purchase Delivery Note with EXACT user-specified structure
        pdn_data = {
            "CardCode": card_code,
            "DocDate": doc_date,
            "DocDueDate": doc_due_date,
            "Comments": grpo_document.notes or "Auto-created from PO after QC",
            "NumAtCard": external_ref,
            "BPL_IDAssignedToInvoice": business_place_id,
            "DocumentLines": document_lines
        }

        # Submit to SAP B1
        url = f"{self.base_url}/b1s/v1/PurchaseDeliveryNotes"

        # Log the payload for debugging - Enhanced JSON logging
        import json
        logging.info("=" * 80)
        logging.info("PURCHASE DELIVERY NOTE - JSON PAYLOAD")
        logging.info("=" * 80)
        logging.info(json.dumps(pdn_data, indent=2, default=str))
        logging.info("=" * 80)
        print(pdn_data)
        try:
            response = self.session.post(url, json=pdn_data)
            if response.status_code == 201:
                result = response.json()
                logging.info(
                    f"Successfully created Purchase Delivery Note {result.get('DocNum')} for GRPO {grpo_document.id}"
                )
                return {
                    'success':
                    True,
                    'document_number':
                    result.get('DocNum'),
                    'doc_entry':
                    result.get('DocEntry'),
                    'external_reference':
                    external_ref,
                    'message':
                    f'Purchase Delivery Note {result.get("DocNum")} created successfully with reference {external_ref}'
                }
            else:
                error_msg = f"SAP B1 error creating Purchase Delivery Note: {response.text}"
                logging.error(error_msg)
                return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Error creating Purchase Delivery Note in SAP B1: {str(e)}"
            logging.error(error_msg)
            return {'success': False, 'error': error_msg}

    def post_grpo_to_sap(self, grpo_document):
        """Post approved GRPO to SAP B1 as Purchase Delivery Note"""
        if not self.ensure_logged_in():
            logging.warning("Cannot post GRPO - SAP B1 not available")
            return {'success': False, 'error': 'SAP B1 not available'}

        try:
            # Create Purchase Delivery Note to close PO
            result = self.create_purchase_delivery_note(grpo_document)

            if result.get('success'):
                # Update WMS record with SAP document number
                grpo_document.sap_document_number = str(
                    result.get('document_number'))
                grpo_document.status = 'posted'

                from app import db
                db.session.commit()

                logging.info(
                    f"GRPO posted to SAP B1 with Purchase Delivery Note: {result.get('document_number')}"
                )
                return {
                    'success':
                    True,
                    'sap_document_number':
                    result.get('document_number'),
                    'message':
                    f'GRPO posted to SAP B1 as Purchase Delivery Note {result.get("document_number")}'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error occurred')
                }
        except Exception as e:
            logging.error(f"Error posting GRPO to SAP: {str(e)}")
            return {'success': False, 'error': str(e)}

    def sync_all_master_data(self):
        """Sync all master data from SAP B1"""
        logging.info("Starting full SAP B1 master data synchronization...")

        results = {
            'warehouses': self.sync_warehouses(),
            'bins': self.sync_bins(),
            'business_partners': self.sync_business_partners()
        }

        success_count = sum(1 for result in results.values() if result)
        logging.info(
            f"Master data sync completed: {success_count}/{len(results)} successful"
        )

        return results

    def logout(self):
        """Logout from SAP B1"""
        if self.session_id:
            try:
                logout_url = f"{self.base_url}/b1s/v1/Logout"
                self.session.post(logout_url)
                self.session_id = None
                logging.info("Logged out from SAP B1")
            except Exception as e:
                logging.error(f"Error logging out from SAP B1: {str(e)}")


