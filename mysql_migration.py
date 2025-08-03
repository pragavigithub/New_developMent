"""
Complete MySQL Database Migration Script for WMS System
This script creates all tables and inserts default admin user.
"""

import os
import mysql.connector
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_mysql_database():
    """Create complete MySQL database with all tables and default data"""
    
    # MySQL connection configuration
    config = {
        'host': input("MySQL Host (default: localhost): ").strip() or 'localhost',
        'port': int(input("MySQL Port (default: 3306): ").strip() or '3306'),
        'user': input("MySQL Username: ").strip(),
        'password': input("MySQL Password: ").strip(),
        'database': input("MySQL Database Name: ").strip(),
        'autocommit': True
    }
    
    try:
        # Connect to MySQL
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        print(f"✅ Connected to MySQL database: {config['database']}")
        
        # Create .env file
        env_content = f"""# Database Configuration for MySQL
DATABASE_URL=mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}

# SAP B1 Configuration
SAP_B1_SERVER=https://192.168.154.173:50000
SAP_B1_USERNAME=manager
SAP_B1_PASSWORD=1422
SAP_B1_COMPANY_DB=EINV-TESTDB-LIVE-HUST

# Session Secret (change in production)
SESSION_SECRET=your-secret-key-here-change-in-production
"""
        
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file with MySQL configuration")
        
        # Drop existing tables to recreate fresh

        

        # Create all tables
        create_tables_sql = """
        -- Users table
        CREATE TABLE users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(256) NOT NULL,
            first_name VARCHAR(80),
            last_name VARCHAR(80),
            role VARCHAR(20) NOT NULL DEFAULT 'user',
            branch_id VARCHAR(10),
            branch_name VARCHAR(100),
            default_branch_id VARCHAR(10),
            user_is_active BOOLEAN DEFAULT TRUE,
            must_change_password BOOLEAN DEFAULT FALSE,
            last_login DATETIME,
            permissions TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );

        -- Branches table
        CREATE TABLE branches (
            id VARCHAR(10) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            address TEXT,
            phone VARCHAR(20),
            email VARCHAR(100),
            manager_name VARCHAR(100),
            is_active BOOLEAN DEFAULT TRUE,
            is_default BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );

        

        -- GRN Documents table
        CREATE TABLE grn_documents (
            id INT AUTO_INCREMENT PRIMARY KEY,
            grn_number VARCHAR(50) UNIQUE,
            po_number VARCHAR(20) NOT NULL,
            sap_document_number VARCHAR(20),
            supplier_code VARCHAR(50),
            supplier_name VARCHAR(200),
            po_date DATETIME,
            po_total DECIMAL(15,2),
            status VARCHAR(20) DEFAULT 'draft',
            user_id INT NOT NULL,
            qc_approver_id INT,
            qc_approved_at DATETIME,
            qc_notes TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (qc_approver_id) REFERENCES users(id)
        );

        -- GRN Items table
        CREATE TABLE grn_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            grn_document_id INT NOT NULL,
            item_code VARCHAR(50) NOT NULL,
            item_name VARCHAR(200),
            received_quantity DECIMAL(15,3) DEFAULT 0,
            ordered_quantity DECIMAL(15,3) DEFAULT 0,
            unit_of_measure VARCHAR(10),
            bin_location VARCHAR(100),
            batch_number VARCHAR(50),
            serial_number VARCHAR(50),
            expiration_date DATE,
            notes TEXT,
            warehouse_code VARCHAR(20),
            qc_status VARCHAR(20) DEFAULT 'pending',
            qc_notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (grn_document_id) REFERENCES grn_documents(id) ON DELETE CASCADE
        );

        -- Inventory Transfers table
        CREATE TABLE inventory_transfers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            transfer_number VARCHAR(50) UNIQUE,
            transfer_request_number VARCHAR(50),
            from_warehouse VARCHAR(20),
            to_warehouse VARCHAR(20),
            status VARCHAR(20) DEFAULT 'draft',
            user_id INT NOT NULL,
            qc_approver_id INT,
            qc_approved_at DATETIME,
            qc_notes TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (qc_approver_id) REFERENCES users(id)
        );

        -- Inventory Transfer Items table
        CREATE TABLE inventory_transfer_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            transfer_id INT NOT NULL,
            item_code VARCHAR(50) NOT NULL,
            item_name VARCHAR(200),
            requested_quantity DECIMAL(15,3) DEFAULT 0,
            transferred_quantity DECIMAL(15,3) DEFAULT 0,
            unit_of_measure VARCHAR(10),
            from_bin_location VARCHAR(100),
            to_bin_location VARCHAR(100),
            batch_number VARCHAR(50),
            serial_number VARCHAR(50),
            notes TEXT,
            qc_status VARCHAR(20) DEFAULT 'pending',
            qc_notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (transfer_id) REFERENCES inventory_transfers(id) ON DELETE CASCADE
        );

        -- Pick Lists table
        CREATE TABLE pick_lists (
            id INT AUTO_INCREMENT PRIMARY KEY,
            pick_list_number VARCHAR(50) UNIQUE,
            sales_order_number VARCHAR(50),
            customer_code VARCHAR(50),
            customer_name VARCHAR(200),
            status VARCHAR(20) DEFAULT 'draft',
            priority VARCHAR(20) DEFAULT 'normal',
            user_id INT NOT NULL,
            completed_at DATETIME,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- Pick List Items table
        CREATE TABLE pick_list_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            pick_list_id INT NOT NULL,
            item_code VARCHAR(50) NOT NULL,
            item_name VARCHAR(200),
            ordered_quantity DECIMAL(15,3) DEFAULT 0,
            picked_quantity DECIMAL(15,3) DEFAULT 0,
            unit_of_measure VARCHAR(10),
            bin_location VARCHAR(100),
            batch_number VARCHAR(50),
            serial_number VARCHAR(50),
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (pick_list_id) REFERENCES pick_lists(id) ON DELETE CASCADE
        );

        -- Inventory Counts table
        CREATE TABLE inventory_counts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            count_number VARCHAR(50) UNIQUE,
            warehouse_code VARCHAR(20),
            status VARCHAR(20) DEFAULT 'draft',
            user_id INT NOT NULL,
            completed_at DATETIME,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- Inventory Count Items table
        CREATE TABLE inventory_count_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            count_id INT NOT NULL,
            item_code VARCHAR(50) NOT NULL,
            item_name VARCHAR(200),
            bin_location VARCHAR(100),
            batch_number VARCHAR(50),
            system_quantity DECIMAL(15,3) DEFAULT 0,
            counted_quantity DECIMAL(15,3) DEFAULT 0,
            variance DECIMAL(15,3) DEFAULT 0,
            unit_of_measure VARCHAR(10),
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (count_id) REFERENCES inventory_counts(id) ON DELETE CASCADE
        );

        -- Barcode Labels table
        CREATE TABLE barcode_labels (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item_code VARCHAR(50) NOT NULL,
            item_name VARCHAR(200),
            batch_number VARCHAR(50),
            barcode VARCHAR(100) UNIQUE NOT NULL,
            label_format VARCHAR(20) DEFAULT 'standard',
            printed_by INT,
            printed_at DATETIME,
            reprint_count INT DEFAULT 0,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (printed_by) REFERENCES users(id)
        );

        -- Bin Scanning Logs table
        CREATE TABLE bin_scanning_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            bin_code VARCHAR(50) NOT NULL,
            warehouse_code VARCHAR(20),
            scanned_by INT NOT NULL,
            scan_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            items_found INT DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (scanned_by) REFERENCES users(id)
        );

        -- User Sessions table
        CREATE TABLE user_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            session_token VARCHAR(256) NOT NULL,
            branch_id VARCHAR(10),
            login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            logout_time DATETIME,
            ip_address VARCHAR(45),
            user_agent TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- Password Reset Tokens table
        CREATE TABLE password_reset_tokens (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            token VARCHAR(256) UNIQUE NOT NULL,
            expires_at DATETIME NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_by INT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );
        """
        
        # Execute table creation
        for statement in create_tables_sql.split(';'):
            if statement.strip():
                cursor.execute(statement)
        print("✅ Created all database tables")
        
        # Insert default branch
        cursor.execute("""
            INSERT INTO branches (id, name, description, address, phone, email, manager_name, is_active, is_default)
            VALUES ('BR001', 'Main Branch', 'Head Office Branch', 'Main Office Address', '+1234567890', 'admin@company.com', 'System Administrator', TRUE, TRUE)
        """)
        print("✅ Created default branch")
        
        # Insert document number series
        document_series = [
            ('GRN', 'GRN-', 0, True),
            ('TRANSFER', 'TRF-', 0, True),
            ('PICKLIST', 'PL-', 0, True),
            ('COUNT', 'CNT-', 0, True)
        ]
        

        # Create default admin user
        admin_password_hash = generate_password_hash('admin123')
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, first_name, last_name, role, branch_id, default_branch_id, user_is_active)
            VALUES ('admin', 'admin@company.com', %s, 'System', 'Administrator', 'admin', 'BR001', 'BR001', TRUE)
        """, (admin_password_hash,))
        print("✅ Created default admin user (admin/admin123)")
        
        connection.close()
        print("\n🎉 MySQL database migration completed successfully!")
        print("\nDefault Login Credentials:")
        print("Username: admin")
        print("Password: admin123")
        print("\n⚠️ Remember to change the default password after first login!")
        
    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 WMS MySQL Database Migration Script")
    print("=" * 50)
    print("This script will create all tables and default admin user.")
    print("Make sure MySQL server is running and you have the credentials ready.")
    print()
    
    if input("Continue? (y/n): ").lower().strip() == 'y':
        create_mysql_database()
    else:
        print("Migration cancelled.")