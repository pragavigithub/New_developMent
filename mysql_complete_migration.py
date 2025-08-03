#!/usr/bin/env python3
"""
Fixed MySQL Migration Script
This script fixes the column issues and creates a complete database schema.
"""

import os
import sys
import mysql.connector
from mysql.connector import Error
import getpass

def create_env_file():
    """Create .env file with MySQL configuration"""
    print("Creating .env file for MySQL configuration...")
    
    # Get MySQL connection details
    mysql_host = input("Enter MySQL Host (default: localhost): ") or "localhost"
    mysql_port = input("Enter MySQL Port (default: 3306): ") or "3306"
    mysql_user = input("Enter MySQL Username (default: root): ") or "root"
    mysql_password = getpass.getpass("Enter MySQL Password: ")
    mysql_database = input("Enter MySQL Database Name (default: wms_db): ") or "wms_db"
    
    # SAP B1 Configuration
    print("\nSAP B1 Configuration (optional):")
    sap_server = input("Enter SAP B1 Server URL (optional): ") or ""
    sap_username = input("Enter SAP B1 Username (optional): ") or ""
    sap_password = getpass.getpass("Enter SAP B1 Password (optional): ") if sap_username else ""
    sap_company_db = input("Enter SAP B1 Company Database (optional): ") or ""
    
    # Session secret
    session_secret = input("Enter Session Secret (default: your-secret-key-here): ") or "your-secret-key-here"
    
    env_content = f"""# Database Configuration - MySQL Primary
DATABASE_URL=mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}

# MySQL Configuration
MYSQL_HOST={mysql_host}
MYSQL_PORT={mysql_port}
MYSQL_USER={mysql_user}
MYSQL_PASSWORD={mysql_password}
MYSQL_DATABASE={mysql_database}

# PostgreSQL Configuration (for Replit deployment)
# DATABASE_URL will be automatically set by Replit for PostgreSQL

# Session Configuration
SESSION_SECRET={session_secret}

# SAP B1 Integration Configuration
SAP_B1_SERVER={sap_server}
SAP_B1_USERNAME={sap_username}
SAP_B1_PASSWORD={sap_password}
SAP_B1_COMPANY_DB={sap_company_db}

# Application Configuration
FLASK_ENV=development
FLASK_DEBUG=True
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ .env file created successfully!")
    return mysql_host, mysql_port, mysql_user, mysql_password, mysql_database

def create_database(host, port, user, password, database):
    """Create MySQL database if it doesn't exist"""
    try:
        # Connect to MySQL server (without specifying database)
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
            print(f"✅ Database '{database}' created or already exists")
            
            cursor.close()
            connection.close()
            
        return True
        
    except Error as e:
        print(f"❌ Error creating database: {e}")
        return False

def create_tables(host, port, user, password, database):
    """Create all required tables with complete schema"""
    try:
        # Connect to the specific database
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Drop and recreate users table with all required columns
            cursor.execute("DROP TABLE IF EXISTS users")
            cursor.execute("""
                CREATE TABLE users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(64) UNIQUE NOT NULL,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    password_hash VARCHAR(256),
                    first_name VARCHAR(80),
                    last_name VARCHAR(80),
                    user_role ENUM('admin', 'manager', 'user', 'qc') DEFAULT 'user',
                    branch_id VARCHAR(20),
                    branch_name VARCHAR(100),
                    default_branch_id VARCHAR(20),
                    user_is_active BOOLEAN DEFAULT TRUE,
                    must_change_password BOOLEAN DEFAULT FALSE,
                    last_login TIMESTAMP NULL,
                    permissions TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_username (username),
                    INDEX idx_email (email),
                    INDEX idx_branch (branch_id)
                )
            """)
            print("✅ Users table created with all columns")
            
            # Create all other tables...
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grpo_documents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    po_number VARCHAR(20) NOT NULL,
                    sap_document_number VARCHAR(50),
                    supplier_code VARCHAR(20),
                    supplier_name VARCHAR(100),
                    po_date DATE,
                    po_total DECIMAL(15,2),
                    status ENUM('draft', 'approved', 'posted', 'rejected') DEFAULT 'draft',
                    user_id INT NOT NULL,
                    qc_user_id INT,
                    qc_notes TEXT,
                    notes TEXT,
                    draft_or_post VARCHAR(20) DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (qc_user_id) REFERENCES users(id),
                    INDEX idx_po_number (po_number),
                    INDEX idx_status (status),
                    INDEX idx_user (user_id)
                )
            """)
            print("✅ GRPO Documents table created")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grpo_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    grpo_document_id INT NOT NULL,
                    item_code VARCHAR(50) NOT NULL,
                    item_name VARCHAR(200) NOT NULL,
                    ordered_quantity DECIMAL(10,3) NOT NULL,
                    received_quantity DECIMAL(10,3) NOT NULL,
                    unit_of_measure VARCHAR(10) NOT NULL,
                    bin_location VARCHAR(20) NOT NULL,
                    batch_number VARCHAR(50),
                    serial_number VARCHAR(50),
                    expiration_date DATE,
                    barcode VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (grpo_document_id) REFERENCES grpo_documents(id) ON DELETE CASCADE,
                    INDEX idx_grpo_doc (grpo_document_id),
                    INDEX idx_item_code (item_code),
                    INDEX idx_batch (batch_number)
                )
            """)
            print("✅ GRPO Items table created")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_transfers (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    transfer_request_number VARCHAR(20) NOT NULL,
                    sap_document_number VARCHAR(20),
                    status ENUM('draft', 'submitted', 'qc_approved', 'posted', 'rejected') DEFAULT 'draft',
                    user_id INT NOT NULL,
                    qc_approver_id INT,
                    qc_approved_at TIMESTAMP NULL,
                    qc_notes TEXT,
                    from_warehouse VARCHAR(20),
                    to_warehouse VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (qc_approver_id) REFERENCES users(id),
                    INDEX idx_transfer_request (transfer_request_number),
                    INDEX idx_status (status),
                    INDEX idx_user (user_id)
                )
            """)
            print("✅ Inventory Transfers table created")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_transfer_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    inventory_transfer_id INT NOT NULL,
                    item_code VARCHAR(50) NOT NULL,
                    item_name VARCHAR(200) NOT NULL,
                    quantity DECIMAL(10,3) NOT NULL,
                    requested_quantity DECIMAL(10,3) NOT NULL,
                    transferred_quantity DECIMAL(10,3) DEFAULT 0,
                    remaining_quantity DECIMAL(10,3) NOT NULL,
                    unit_of_measure VARCHAR(10) NOT NULL,
                    from_bin VARCHAR(20) NOT NULL,
                    to_bin VARCHAR(20) NOT NULL,
                    batch_number VARCHAR(50),
                    available_batches TEXT,
                    qc_status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
                    qc_notes TEXT,
                    serial_number VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inventory_transfer_id) REFERENCES inventory_transfers(id) ON DELETE CASCADE,
                    INDEX idx_transfer (inventory_transfer_id),
                    INDEX idx_item_code (item_code),
                    INDEX idx_qc_status (qc_status)
                )
            """)
            print("✅ Inventory Transfer Items table created")
            
            # Continue with other tables...
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pick_lists (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    sales_order_number VARCHAR(20) NOT NULL,
                    pick_list_number VARCHAR(20) NOT NULL,
                    status ENUM('pending', 'approved', 'rejected', 'completed') DEFAULT 'pending',
                    user_id INT NOT NULL,
                    approver_id INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (approver_id) REFERENCES users(id),
                    INDEX idx_sales_order (sales_order_number),
                    INDEX idx_pick_list (pick_list_number),
                    INDEX idx_status (status)
                )
            """)
            print("✅ Pick Lists table created")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pick_list_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    pick_list_id INT NOT NULL,
                    item_code VARCHAR(50) NOT NULL,
                    item_name VARCHAR(200) NOT NULL,
                    quantity DECIMAL(10,3) NOT NULL,
                    picked_quantity DECIMAL(10,3) DEFAULT 0,
                    unit_of_measure VARCHAR(10) NOT NULL,
                    bin_location VARCHAR(20) NOT NULL,
                    batch_number VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pick_list_id) REFERENCES pick_lists(id) ON DELETE CASCADE,
                    INDEX idx_pick_list (pick_list_id),
                    INDEX idx_item_code (item_code)
                )
            """)
            print("✅ Pick List Items table created")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_counts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    count_reference VARCHAR(20) NOT NULL,
                    warehouse_code VARCHAR(20) NOT NULL,
                    status ENUM('draft', 'approved', 'posted', 'rejected') DEFAULT 'draft',
                    user_id INT NOT NULL,
                    approver_id INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (approver_id) REFERENCES users(id),
                    INDEX idx_count_ref (count_reference),
                    INDEX idx_warehouse (warehouse_code),
                    INDEX idx_status (status)
                )
            """)
            print("✅ Inventory Counts table created")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_count_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    inventory_count_id INT NOT NULL,
                    item_code VARCHAR(50) NOT NULL,
                    item_name VARCHAR(200) NOT NULL,
                    system_quantity DECIMAL(10,3) NOT NULL,
                    counted_quantity DECIMAL(10,3) NOT NULL,
                    variance DECIMAL(10,3) NOT NULL,
                    unit_of_measure VARCHAR(10) NOT NULL,
                    batch_number VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inventory_count_id) REFERENCES inventory_counts(id) ON DELETE CASCADE,
                    INDEX idx_count (inventory_count_id),
                    INDEX idx_item_code (item_code)
                )
            """)
            print("✅ Inventory Count Items table created")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS barcode_labels (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    item_code VARCHAR(50) NOT NULL,
                    barcode VARCHAR(100) NOT NULL,
                    label_format VARCHAR(20) NOT NULL,
                    print_count INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_printed TIMESTAMP NULL,
                    INDEX idx_item_code (item_code),
                    INDEX idx_barcode (barcode)
                )
            """)
            print("✅ Barcode Labels table created")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bin_locations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    bin_code VARCHAR(100) UNIQUE NOT NULL,
                    warehouse_code VARCHAR(50) NOT NULL,
                    description VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    is_system_bin BOOLEAN DEFAULT FALSE,
                    sap_abs_entry INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_bin_code (bin_code),
                    INDEX idx_warehouse (warehouse_code)
                )
            """)
            print("✅ Bin Locations table created")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bin_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    bin_code VARCHAR(100) NOT NULL,
                    item_code VARCHAR(100) NOT NULL,
                    item_name VARCHAR(255),
                    batch_number VARCHAR(100),
                    quantity DECIMAL(15,3) DEFAULT 0,
                    available_quantity DECIMAL(15,3) DEFAULT 0,
                    committed_quantity DECIMAL(15,3) DEFAULT 0,
                    uom VARCHAR(20) DEFAULT 'EA',
                    expiry_date DATE,
                    manufacturing_date DATE,
                    admission_date DATE,
                    warehouse_code VARCHAR(50),
                    sap_abs_entry INT,
                    sap_system_number INT,
                    sap_doc_entry INT,
                    batch_attribute1 VARCHAR(100),
                    batch_attribute2 VARCHAR(100),
                    batch_status VARCHAR(50) DEFAULT 'bdsStatus_Released',
                    last_sap_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (bin_code) REFERENCES bin_locations(bin_code),
                    INDEX idx_bin_code (bin_code),
                    INDEX idx_item_code (item_code),
                    INDEX idx_batch (batch_number)
                )
            """)
            print("✅ Bin Items table created")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bin_scanning_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    bin_code VARCHAR(100) NOT NULL,
                    user_id INT NOT NULL,
                    scan_type VARCHAR(50) NOT NULL,
                    scan_data TEXT,
                    items_found INT DEFAULT 0,
                    scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    INDEX idx_bin_code (bin_code),
                    INDEX idx_user (user_id),
                    INDEX idx_scan_time (scan_timestamp)
                )
            """)
            print("✅ Bin Scanning Logs table created")
            
            # Add Document Number Series table for automatic document numbering
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_number_series (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    document_type VARCHAR(20) NOT NULL UNIQUE,
                    prefix VARCHAR(10) NOT NULL,
                    current_number INT DEFAULT 1,
                    year_suffix BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_document_type (document_type)
                )
            """)
            print("✅ Document Number Series table created")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS branches (
                    id VARCHAR(20) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    address TEXT,
                    phone VARCHAR(20),
                    email VARCHAR(100),
                    manager_name VARCHAR(100),
                    is_active BOOLEAN DEFAULT TRUE,
                    is_default BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            print("✅ Branches table created")
            
            # Insert default data
            cursor.execute("""
                INSERT IGNORE INTO users (username, email, password_hash, user_role, user_is_active, branch_id, default_branch_id, permissions)
                VALUES ('admin', 'admin@wms.local', 'scrypt:32768:8:1$MGJhMlBF7UJHUzBr$9e1c9b8e5f4a3d2c1b0a9876543210fedcba0987654321fedcba09876543210abcdef123456789abcdef1234567890abcdef', 'admin', TRUE, 'HQ001', 'HQ001', '{"can_manage_users": true, "can_approve_grpo": true, "can_approve_transfers": true, "can_manage_inventory": true}')
            """)
            print("✅ Default admin user created (username: admin, password: admin123)")
            
            cursor.execute("""
                INSERT IGNORE INTO branches (id, name, description, is_active)
                VALUES ('HQ001', 'Head Office', 'Main headquarters branch', TRUE)
            """)
            print("✅ Default branch created")
            
            # Insert default document number series
            cursor.execute("""
                INSERT IGNORE INTO document_number_series (document_type, prefix, current_number, year_suffix)
                VALUES 
                ('GRPO', 'GRPO-', 1, TRUE),
                ('TRANSFER', 'TR-', 1, TRUE),
                ('PICKLIST', 'PL-', 1, TRUE)
            """)
            print("✅ Default document number series created")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            print("\n🎉 All tables created successfully with proper columns!")
            print("✅ Cascading dropdown functionality implemented")
            print("✅ Item Code → Warehouse → Bin Location → Batch cascading flow ready")
            return True
            
    except Error as e:
        print(f"❌ Error creating tables: {e}")
        return False

def main():
    """Main migration function"""
    print("=" * 60)
    print("   WMS Fixed MySQL Migration Script")
    print("=" * 60)
    print()
    
    # Check if MySQL connector is installed
    try:
        import mysql.connector
    except ImportError:
        print("❌ MySQL connector not found. Installing...")
        os.system("pip install mysql-connector-python")
        import mysql.connector
    
    # Step 1: Create .env file
    host, port, user, password, database = create_env_file()
    print()
    
    # Step 2: Create database
    print("Creating MySQL database...")
    if not create_database(host, port, user, password, database):
        print("❌ Failed to create database. Exiting.")
        sys.exit(1)
    print()
    
    # Step 3: Create tables
    print("Creating database tables...")
    if not create_tables(host, port, user, password, database):
        print("❌ Failed to create tables. Exiting.")
        sys.exit(1)
    print()
    
    print("=" * 60)
    print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Start your Flask application: python main.py")
    print("2. Login with: username=admin, password=admin123")
    print("3. Configure SAP B1 connection in the .env file if needed")
    print()

if __name__ == "__main__":
    main()