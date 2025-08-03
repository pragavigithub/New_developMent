#!/usr/bin/env python3
"""
Quick MySQL Schema Fix Script
Adds missing columns to existing MySQL database
"""

import os
import sys
import mysql.connector
from mysql.connector import Error

def fix_mysql_schema():
    """Fix MySQL database schema by adding missing columns"""
    
    # Get database connection details from environment
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
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            print("📝 Adding missing columns to users table...")
            
            # Add missing columns to users table
            missing_user_columns = [
                "ADD COLUMN first_name VARCHAR(80)",
                "ADD COLUMN last_name VARCHAR(80)", 
                "ADD COLUMN branch_name VARCHAR(100)",
                "ADD COLUMN must_change_password BOOLEAN DEFAULT FALSE",
                "ADD COLUMN last_login TIMESTAMP NULL",
                "ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            ]
            
            # Check if we need to rename user_role to role
            cursor.execute("SHOW COLUMNS FROM users LIKE 'role'")
            role_exists = cursor.fetchone()
            
            cursor.execute("SHOW COLUMNS FROM users LIKE 'user_role'")
            user_role_exists = cursor.fetchone()
            
            if user_role_exists and not role_exists:
                print("🔄 Renaming user_role column to role...")
                cursor.execute("ALTER TABLE users CHANGE COLUMN user_role role VARCHAR(20) DEFAULT 'user'")
                print("✅ Renamed user_role to role")
            elif not role_exists and not user_role_exists:
                missing_user_columns.append("ADD COLUMN role VARCHAR(20) DEFAULT 'user'")
                print("➕ Will add role column")
            
            for column_sql in missing_user_columns:
                try:
                    cursor.execute(f"ALTER TABLE users {column_sql}")
                    print(f"✅ Added column: {column_sql}")
                except Error as e:
                    if "Duplicate column name" in str(e):
                        print(f"✓ Column already exists: {column_sql}")
                    else:
                        print(f"⚠️ Error adding column {column_sql}: {e}")
            
            print("📝 Adding missing columns to branches table...")
            
            # Add missing columns to branches table
            missing_branch_columns = [
                "ADD COLUMN description TEXT",
                "ADD COLUMN address TEXT",
                "ADD COLUMN phone VARCHAR(20)",
                "ADD COLUMN email VARCHAR(100)",
                "ADD COLUMN manager_name VARCHAR(100)",
                "ADD COLUMN is_default BOOLEAN DEFAULT FALSE",
                "ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            ]
            
            for column_sql in missing_branch_columns:
                try:
                    cursor.execute(f"ALTER TABLE branches {column_sql}")
                    print(f"✅ Added column: {column_sql}")
                except Error as e:
                    if "Duplicate column name" in str(e):
                        print(f"✓ Column already exists: {column_sql}")
                    else:
                        print(f"⚠️ Error adding column {column_sql}: {e}")
            
            print("📝 Creating document_number_series table if missing...")
            
            # Create document_number_series table
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
                
                # Insert default series
                cursor.execute("""
                    INSERT IGNORE INTO document_number_series (document_type, prefix, current_number, year_suffix)
                    VALUES 
                    ('GRPO', 'GRPO-', 1, TRUE),
                    ('TRANSFER', 'TR-', 1, TRUE),
                    ('PICKLIST', 'PL-', 1, TRUE)
                """)
                print("✅ Default document series created")
                
            except Error as e:
                print(f"⚠️ Error creating document_number_series table: {e}")
            
            print("📝 Creating/updating admin user with proper credentials...")
            
            # Generate proper password hash for 'admin123'
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash('admin123')
            
            # First check if admin exists
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            admin_exists = cursor.fetchone()
            
            if admin_exists:
                # Update existing admin user
                try:
                    cursor.execute("""
                        UPDATE users SET 
                            password_hash = %s,
                            first_name = 'Admin',
                            last_name = 'User',
                            branch_name = 'Head Office',
                            role = 'admin',
                            user_is_active = 1
                        WHERE username = 'admin'
                    """, (password_hash,))
                    print("✅ Admin user updated with new password hash")
                except Error as e:
                    print(f"⚠️ Error updating admin user: {e}")
            else:
                # Create new admin user
                try:
                    cursor.execute("""
                        INSERT INTO users (username, email, password_hash, role, user_is_active, first_name, last_name, branch_name)
                        VALUES ('admin', 'admin@wms.local', %s, 'admin', 1, 'Admin', 'User', 'Head Office')
                    """, (password_hash,))
                    print("✅ New admin user created with proper credentials")
                except Error as e:
                    print(f"⚠️ Error creating admin user: {e}")
            
            # Ensure default branch exists
            try:
                cursor.execute("""
                    INSERT IGNORE INTO branches (id, name, description, is_active)
                    VALUES ('HQ001', 'Head Office', 'Main headquarters branch', TRUE)
                """)
                print("✅ Default branch ensured")
            except Error as e:
                print(f"⚠️ Error creating default branch: {e}")
            
            print("📝 Adding missing columns to grpo_documents table...")
            
            # Add missing columns to grpo_documents table
            missing_grpo_columns = [
                "ADD COLUMN sap_document_number VARCHAR(50)",
                "ADD COLUMN qc_user_id INT",
                "ADD COLUMN qc_notes TEXT",
                "ADD COLUMN draft_or_post VARCHAR(20) DEFAULT 'draft'"
            ]
            
            for column_sql in missing_grpo_columns:
                try:
                    cursor.execute(f"ALTER TABLE grpo_documents {column_sql}")
                    print(f"✅ Added GRPO column: {column_sql}")
                except Error as e:
                    if "Duplicate column name" in str(e):
                        print(f"✓ GRPO column already exists: {column_sql}")
                    else:
                        print(f"⚠️ Error adding GRPO column {column_sql}: {e}")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            print("\n🎉 MySQL schema fix completed successfully!")
            print("✓ Missing columns added to users and branches tables")
            print("✓ Document numbering system configured")
            print("✓ Default data ensured")
            print("\nYou can now restart your Flask application!")
            
            return True
            
    except Error as e:
        print(f"❌ Database connection error: {e}")
        print("\n💡 Make sure your .env file has the correct MySQL credentials:")
        print("MYSQL_HOST=localhost")
        print("MYSQL_PORT=3306") 
        print("MYSQL_USER=root")
        print("MYSQL_PASSWORD=your_password")
        print("MYSQL_DATABASE=wms_db")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("   WMS MySQL Schema Fix Script")
    print("=" * 60)
    print()
    
    # Check if mysql.connector is available
    try:
        import mysql.connector
    except ImportError:
        print("❌ MySQL connector not found. Installing...")
        os.system("pip install mysql-connector-python")
        import mysql.connector
    
    success = fix_mysql_schema()
    
    if success:
        print("\n🚀 Schema fix completed! Your MySQL database is now ready.")
        print("Run 'python main.py' to start your Flask application.")
    else:
        print("\n❌ Schema fix failed. Please check your database connection.")
        sys.exit(1)