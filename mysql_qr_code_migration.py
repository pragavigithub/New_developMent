#!/usr/bin/env python3
"""
MySQL QR Code Migration Script
Creates QR code labels table in MySQL database to maintain dual database support
"""

import os
import pymysql
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_mysql_connection():
    """Get MySQL database connection"""
    try:
        connection = pymysql.connect(
            host=os.environ.get('MYSQL_HOST', 'localhost'),
            user=os.environ.get('MYSQL_USER', 'root'),
            password=os.environ.get('MYSQL_PASSWORD', ''),
            database=os.environ.get('MYSQL_DATABASE', 'wms_db'),
            charset='utf8mb4'
        )
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to MySQL: {e}")
        return None

def create_qr_code_table_mysql():
    """Create QR code labels table in MySQL"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS qr_code_labels (
        id INT AUTO_INCREMENT PRIMARY KEY,
        label_type VARCHAR(50) NOT NULL,
        item_code VARCHAR(100) NOT NULL,
        item_name VARCHAR(200),
        po_number VARCHAR(100),
        batch_number VARCHAR(100),
        warehouse_code VARCHAR(50),
        bin_code VARCHAR(100),
        quantity DECIMAL(15, 4),
        uom VARCHAR(20),
        expiry_date DATE,
        qr_content TEXT NOT NULL,
        qr_format VARCHAR(20) DEFAULT 'TEXT',
        grpo_item_id INT,
        inventory_transfer_item_id INT,
        user_id INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_qr_code_labels_item_code (item_code),
        INDEX idx_qr_code_labels_po_number (po_number),
        INDEX idx_qr_code_labels_label_type (label_type),
        INDEX idx_qr_code_labels_user_id (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    connection = get_mysql_connection()
    if not connection:
        logger.error("Cannot create QR code table - no MySQL connection")
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute(create_table_sql)
        connection.commit()
        cursor.close()
        connection.close()
        
        logger.info("✅ QR code labels table created successfully in MySQL")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create QR code table in MySQL: {e}")
        return False

def add_sample_qr_data_mysql():
    """Add sample QR code data to MySQL"""
    
    connection = get_mysql_connection()
    if not connection:
        return False
    
    sample_data = [
        {
            'label_type': 'GRN_ITEM',
            'item_code': '3M T-151',
            'item_name': '3M T-151',
            'po_number': '232430693',
            'batch_number': 'BATCH001',
            'warehouse_code': 'ORBS',
            'qr_content': "Item Code: 3M T-151\nItem Name: 3M T-151\nPO Number: 232430693\nBatch Number: BATCH001",
            'qr_format': 'TEXT',
            'user_id': 1
        }
    ]
    
    insert_sql = """
    INSERT INTO qr_code_labels 
    (label_type, item_code, item_name, po_number, batch_number, warehouse_code, qr_content, qr_format, user_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    qr_content = VALUES(qr_content),
    updated_at = CURRENT_TIMESTAMP
    """
    
    try:
        cursor = connection.cursor()
        
        for sample in sample_data:
            values = (
                sample['label_type'],
                sample['item_code'],
                sample['item_name'],
                sample['po_number'],
                sample['batch_number'],
                sample['warehouse_code'],
                sample['qr_content'],
                sample['qr_format'],
                sample['user_id']
            )
            
            cursor.execute(insert_sql, values)
        
        connection.commit()
        cursor.close()
        connection.close()
        
        logger.info("✅ Sample QR code data added to MySQL")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to add sample QR code data to MySQL: {e}")
        return False

def main():
    """Run MySQL QR code migration"""
    print("🚀 Starting MySQL QR Code Migration")
    print("=" * 50)
    
    if create_qr_code_table_mysql():
        print("✅ QR code table created in MySQL")
        
        if add_sample_qr_data_mysql():
            print("✅ Sample data added to MySQL")
        
        print("\n🎯 MySQL QR code migration completed!")
        return True
    else:
        print("❌ MySQL QR code migration failed")
        return False

if __name__ == "__main__":
    main()