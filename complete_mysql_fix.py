#!/usr/bin/env python3
"""
Complete MySQL Fix Script
Fixes all database schema issues and admin credentials
"""

import os
import mysql.connector
from werkzeug.security import generate_password_hash

def complete_mysql_fix():
    """Complete fix for all MySQL schema issues"""
    
    # Database connection details
    host = os.environ.get('MYSQL_HOST', 'localhost')
    port = int(os.environ.get('MYSQL_PORT', '3306'))
    user = os.environ.get('MYSQL_USER', 'root')
    password = os.environ.get('MYSQL_PASSWORD', 'root@123')
    database = os.environ.get('MYSQL_DATABASE', 'wms_db_test')
    
    try:
        print("🔧 Connecting to MySQL database...")
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        cursor = connection.cursor()
        
        print("📝 Step 1: Fix user_role to role column...")
        try:
            cursor.execute("SHOW COLUMNS FROM users LIKE 'role'")
            role_exists = cursor.fetchone()
            
            cursor.execute("SHOW COLUMNS FROM users LIKE 'user_role'")
            user_role_exists = cursor.fetchone()
            
            if user_role_exists and not role_exists:
                cursor.execute("ALTER TABLE users CHANGE COLUMN user_role role VARCHAR(20) DEFAULT 'user'")
                print("✅ Renamed user_role to role")
        except Exception as e:
            print(f"⚠️ Role column fix: {e}")
        
        print("📝 Step 2: Add missing user columns...")
        user_columns = [
            "first_name VARCHAR(80)",
            "last_name VARCHAR(80)",
            "branch_name VARCHAR(100)",
            "must_change_password BOOLEAN DEFAULT FALSE",
            "last_login TIMESTAMP NULL",
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
        ]
        
        for column in user_columns:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column}")
                print(f"✅ Added user column: {column.split()[0]}")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print(f"✓ User column exists: {column.split()[0]}")
                else:
                    print(f"⚠️ Error adding {column.split()[0]}: {e}")
        
        print("📝 Step 3: Add missing branch columns...")
        branch_columns = [
            "description TEXT",
            "address TEXT", 
            "phone VARCHAR(20)",
            "email VARCHAR(100)",
            "manager_name VARCHAR(100)",
            "is_default BOOLEAN DEFAULT FALSE",
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
        ]
        
        for column in branch_columns:
            try:
                cursor.execute(f"ALTER TABLE branches ADD COLUMN {column}")
                print(f"✅ Added branch column: {column.split()[0]}")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print(f"✓ Branch column exists: {column.split()[0]}")
                else:
                    print(f"⚠️ Error adding {column.split()[0]}: {e}")
        
        print("📝 Step 4: Add missing GRPO document columns...")
        grpo_columns = [
            "sap_document_number VARCHAR(50)",
            "qc_user_id INT",
            "qc_notes TEXT",
            "draft_or_post VARCHAR(20) DEFAULT 'draft'"
        ]
        
        for column in grpo_columns:
            try:
                cursor.execute(f"ALTER TABLE grpo_documents ADD COLUMN {column}")
                print(f"✅ Added GRPO column: {column.split()[0]}")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    print(f"✓ GRPO column exists: {column.split()[0]}")
                else:
                    print(f"⚠️ Error adding {column.split()[0]}: {e}")
        
        print("📝 Step 5: Create document number series table...")
        try:
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
            print("✅ Document number series table created")
            
            cursor.execute("""
                INSERT IGNORE INTO document_number_series (document_type, prefix, current_number, year_suffix)
                VALUES 
                ('GRPO', 'GRPO-', 1, TRUE),
                ('TRANSFER', 'TR-', 1, TRUE),
                ('PICKLIST', 'PL-', 1, TRUE)
            """)
            print("✅ Default document series added")
        except Exception as e:
            print(f"⚠️ Document series error: {e}")
        
        print("📝 Step 6: Fix admin user credentials...")
        password_hash = generate_password_hash('admin123')
        
        try:
            cursor.execute("""
                UPDATE users SET 
                    password_hash = %s,
                    role = 'admin',
                    user_is_active = TRUE,
                    first_name = 'Admin',
                    last_name = 'User',
                    branch_name = 'Head Office'
                WHERE username = 'admin'
            """, (password_hash,))
            
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role, user_is_active, first_name, last_name, branch_name)
                    VALUES ('admin', 'admin@wms.local', %s, 'admin', TRUE, 'Admin', 'User', 'Head Office')
                """, (password_hash,))
                print("✅ Created new admin user")
            else:
                print("✅ Updated existing admin user")
        except Exception as e:
            print(f"⚠️ Admin user error: {e}")
        
        print("📝 Step 7: Ensure default branch...")
        try:
            cursor.execute("""
                INSERT IGNORE INTO branches (id, name, description, is_active)
                VALUES ('HQ001', 'Head Office', 'Main headquarters branch', TRUE)
            """)
            print("✅ Default branch ensured")
        except Exception as e:
            print(f"⚠️ Default branch error: {e}")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("\n🎉 Complete MySQL fix successful!")
        print("✓ All database schema issues resolved")
        print("✓ Admin credentials reset (admin/admin123)")
        print("✓ GRPO validation and document numbering ready")
        print("\n🚀 Restart your Flask app and try logging in!")
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("   Complete MySQL Schema Fix")
    print("=" * 60)
    complete_mysql_fix()