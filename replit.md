# Warehouse Management System (WMS)

## Project Overview
A comprehensive warehouse management system with SAP B1 integration, built with Flask and PostgreSQL. This system handles goods receipt, inventory transfers, pick lists, inventory counting, bin scanning, QR code label printing, and quality control operations.

## Architecture
- **Backend**: Flask with SQLAlchemy ORM
- **Database**: PostgreSQL (migrated from MySQL/SQLite for Replit compatibility)
- **Authentication**: Flask-Login with role-based permissions
- **External Integration**: SAP Business One via REST API
- **Frontend**: Jinja2 templates with Bootstrap UI
- **Deployment**: Gunicorn WSGI server on Replit

## Key Features
1. **User Management**: Role-based access control (admin, manager, user, qc)
2. **GRPO (Goods Receipt PO)**: Purchase order receipt processing
3. **Inventory Transfer**: Item movement between locations
4. **Pick List Management**: Order fulfillment operations
5. **Inventory Counting**: Stock count reconciliation
6. **Bin Scanning**: Barcode scanning for warehouse locations
7. **QR Code Labels**: Label generation and printing
8. **Quality Control Dashboard**: QC workflow management
9. **SAP B1 Integration**: Real-time data synchronization

## Database Schema
- **Users**: Authentication and role management
- **Branches**: Multi-location support
- **GRPO Documents**: Purchase receipt records
- **Inventory Transfers**: Stock movement tracking
- **Pick Lists**: Order picking workflows
- **Inventory Counts**: Stock counting operations
- **Bin Scanning Logs**: Location scanning history
- **QR Code Labels**: Label generation tracking

## Security Features
- Password hashing with Werkzeug
- Session-based authentication
- Role-based access control
- SQL injection protection via SQLAlchemy
- CSRF protection ready

## Replit Migration Status
- [x] PostgreSQL database provisioned
- [x] Database configuration updated for Replit
- [x] Gunicorn workflow configured
- [x] Environment variables structured
- [ ] Application testing and validation

## User Preferences
*To be updated based on user interactions*

## Recent Changes
- **2025-08-03**: Fixed inventory transfer cascading dropdowns and manual entry
- **2025-08-03**: Implemented QR/barcode generation with C# ZXing.QRCode compatibility
- **2025-08-03**: Fixed Add Remaining and Edit button functionality with proper JavaScript
- **2025-08-03**: Enhanced SAP B1 integration with exact API endpoints for batch/bin selection
- **2025-08-03**: Added warehouse-based bin loading and item-based batch selection
- **2025-08-03**: Migrated from Replit Agent to standard Replit environment