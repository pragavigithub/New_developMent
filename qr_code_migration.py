#!/usr/bin/env python3
"""
QR Code Labels Database Migration
Creates qr_code_labels table with MySQL dual database support
"""

import os
import logging
from datetime import datetime
from db_dual_support import get_database_connections

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_qr_code_labels_table():
    """Create qr_code_labels table in both SQLite and MySQL databases"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS qr_code_labels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        grpo_item_id INTEGER,
        inventory_transfer_item_id INTEGER,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (grpo_item_id) REFERENCES grpo_items(id),
        FOREIGN KEY (inventory_transfer_item_id) REFERENCES inventory_transfer_items(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """
    
    # MySQL specific version
    mysql_create_table_sql = """
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
        FOREIGN KEY (grpo_item_id) REFERENCES grpo_items(id),
        FOREIGN KEY (inventory_transfer_item_id) REFERENCES inventory_transfer_items(id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        INDEX idx_qr_code_labels_item_code (item_code),
        INDEX idx_qr_code_labels_po_number (po_number),
        INDEX idx_qr_code_labels_label_type (label_type),
        INDEX idx_qr_code_labels_user_id (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    success_count = 0
    
    try:
        connections = get_database_connections()
        
        for db_name, conn in connections.items():
            if conn:
                try:
                    cursor = conn.cursor()
                    
                    # Use appropriate SQL for each database type
                    if 'mysql' in db_name.lower():
                        cursor.execute(mysql_create_table_sql)
                        logger.info(f"✅ Created qr_code_labels table in {db_name}")
                    else:
                        cursor.execute(create_table_sql)
                        logger.info(f"✅ Created qr_code_labels table in {db_name}")
                    
                    conn.commit()
                    cursor.close()
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to create qr_code_labels table in {db_name}: {e}")
            else:
                logger.warning(f"⚠️ No connection available for {db_name}")
                
    except Exception as e:
        logger.error(f"❌ Error getting database connections: {e}")
    
    return success_count > 0

def add_sample_qr_codes():
    """Add sample QR code data for testing"""
    
    sample_data = [
        {
            'label_type': 'GRN_ITEM',
            'item_code': '3M T-151',
            'item_name': '3M T-151',
            'po_number': '232430693',
            'batch_number': None,
            'warehouse_code': 'ORBS',
            'qr_content': "Item Code: 3M T-151\nItem Name: 3M T-151\nPO Number: 232430693",
            'qr_format': 'TEXT',
            'user_id': 1
        }
    ]
    
    insert_sql = """
    INSERT INTO qr_code_labels 
    (label_type, item_code, item_name, po_number, batch_number, warehouse_code, qr_content, qr_format, user_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    mysql_insert_sql = """
    INSERT INTO qr_code_labels 
    (label_type, item_code, item_name, po_number, batch_number, warehouse_code, qr_content, qr_format, user_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        connections = get_database_connections()
        
        for db_name, conn in connections.items():
            if conn:
                try:
                    cursor = conn.cursor()
                    
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
                        
                        if 'mysql' in db_name.lower():
                            cursor.execute(mysql_insert_sql, values)
                        else:
                            cursor.execute(insert_sql, values)
                    
                    conn.commit()
                    cursor.close()
                    logger.info(f"✅ Added sample QR code data to {db_name}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to add sample data to {db_name}: {e}")
                    
    except Exception as e:
        logger.error(f"❌ Error adding sample QR code data: {e}")

def main():
    """Run QR code migration"""
    print("🚀 Starting QR Code Labels Migration")
    print("=" * 50)
    
    # Create the table
    if create_qr_code_labels_table():
        print("✅ QR Code Labels table created successfully")
        
        # Add sample data
        print("\n📝 Adding sample QR code data...")
        add_sample_qr_codes()
        
        print("\n🎯 QR Code migration completed successfully!")
    else:
        print("❌ Failed to create QR Code Labels table")
        return False
    
    return True

if __name__ == "__main__":
    main()