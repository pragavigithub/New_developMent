# Warehouse Management System (WMS) - SAP B1 Integration

## Overview

This is a comprehensive Warehouse Management System (WMS) built with Flask that integrates with SAP Business One (B1) for enterprise-level warehouse operations. Designed as a Progressive Web App (PWA) optimized for handheld devices and barcode scanning, it aims to streamline warehouse processes. The system provides core functionalities like Goods Receipt against Purchase Orders (GRPO), inventory transfers, pick lists, and inventory counting, all with real-time SAP B1 integration.

## User Preferences

Preferred communication style: Simple, everyday language.
Database preference: MySQL database for local development with migration scripts.
Mobile technology preference: Native Android Java for mobile applications (switched from React Native).
Module priorities: PickList Module, GRPO Module, Inventory Transfer Module.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with dual database support - SQLite for Replit environment (primary) and MySQL synchronization for local development continuity. Automatic change synchronization ensures data consistency between both databases.
- **Migration Status**: Successfully migrated from Replit Agent to Replit environment on August 1, 2025. Enhanced SAP B1 API integration with correct field mappings for BinLocations, Warehouses, and BatchNumberDetails APIs based on actual API response analysis.
- **Authentication**: Flask-Login for user session management with role-based access control and branch-specific access.
- **SAP Integration**: Custom SAP B1 Service Layer integration via REST API for real-time data synchronization of POs, inventory, documents, and master data (warehouses, bins, business partners).
- **Security**: Password hashing with Werkzeug utilities, CSRF protection, and environment-based configuration.
- **Modularity**: Structured into distinct modules (e.g., GRPO, Inventory Transfer) with dedicated route controllers and blueprints for separation of concerns.

### Frontend Architecture
- **UI Framework**: Bootstrap 5 for responsive design.
- **PWA Features**: Service worker for caching, manifest.json for mobile installation, offline capabilities, and mobile optimization for handheld devices.
- **Barcode Scanning**: QuaggaJS and QR Scanner libraries with camera integration, supporting multiple barcode types and QR code generation for items.
- **Icons**: Feather Icons for consistent UI elements.
- **JavaScript**: Vanilla JS with class-based architecture, incorporating cascading dropdowns for item entry, warehouse, bin, and batch selection.
- **UI/UX Decisions**: Optimized for warehouse workers, including features like "Preview JSON" for SAP B1 payload inspection, clear status indicators, and enhanced UOM display.

### Key Features and Technical Implementations
- **Authentication System**: User login, role-based permissions, branch-specific access, session management.
- **SAP B1 Integration**: Session-based connection, real-time data sync, comprehensive error handling, automatic document numbering, and precise JSON structuring for SAP B1 API calls (e.g., Purchase Delivery Notes, Stock Transfers). Includes BusinessPlaceID lookup and accurate batch/serial number handling.
- **Warehouse Operations**:
    - **GRPO**: Scan POs, validate items, record receipts with quantity validation (no over-receipt), generate/reprint labels, auto-generate GRPO numbers. Supports partial receipts and QC approval workflows.
    - **Inventory Transfer**: Inter-warehouse and bin-to-bin transfers, partial transfer support, QC workflow (draft → submitted → qc_approved/rejected → posted), batch number dropdowns with real-time stock/expiry data.
    - **Pick Lists**: Sales order-based picking with priority and status filtering.
    - **Inventory Counting**: Cycle counting and physical inventory tasks.
    - **Bin Scanning**: Display all items in a specific bin location with real-time SAP data (OnHand/OnStock quantities, batch info).
- **Barcode Management**: Generation for various formats (standard, custom), QR code generation with detailed item/document data (PO/Transfer number), and label reprinting.
- **QR Code Generation**: Enhanced QR code functionality for GRN items with multiple format support (TEXT, JSON, CSV). Generates scannable QR codes containing item information (Item Code, Name, PO Number, Batch Number) that can be read by any QR scanner application. Includes QR code history tracking and database storage with dual MySQL migration support.
- **Mobile Application (Native Android Java)**: Developed as a native Android app eliminating React Native dependencies. Features include offline-first architecture with local SQLite database, background synchronization, Material Design 3 UI, ZXing barcode scanning, Retrofit API integration, and Room database support. Implements GRPO, Inventory Transfer, and Pick List modules with full CRUD and QC approval workflows.

## External Dependencies

- **SAP B1 Integration**:
    - Service Layer URL (Configured via `SAP_B1_SERVER` environment variable)
    - SAP B1 Username/Password (`SAP_B1_USERNAME`, `SAP_B1_PASSWORD`)
    - SAP B1 Company Database Name (`SAP_B1_COMPANY_DB`)

- **Third-Party Libraries**:
    - Bootstrap 5 (UI framework)
    - QuaggaJS (Barcode scanning library)
    - QR Scanner (QR code scanning functionality)
    - Feather Icons (Icon library)
    - jQuery (JavaScript utilities)
    - SQLAlchemy (ORM)
    - Flask-Login (Authentication)
    - Werkzeug (Security utilities)
    - PyMySQL (for MySQL database connectivity)
    - MySQL Connector (for MySQL database connectivity)
    - psycopg2 (for PostgreSQL database connectivity)
    - pyodbc (for SQL Server connectivity)

- **Environment Configuration Variables**:
    - `DATABASE_URL`: PostgreSQL connection string (for Replit)
    - `SESSION_SECRET`: Flask session encryption key
    - `SAP_B1_SERVER`: SAP B1 Service Layer endpoint
    - `SAP_B1_USERNAME`: SAP B1 user credentials
    - `SAP_B1_PASSWORD`: SAP B1 user password
    - `SAP_B1_COMPANY_DB`: SAP B1 company database name
    - `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` (for local MySQL development)