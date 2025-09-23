# Data Model Design

## Feature: GST Compliant Service Center Management System

This document defines the data entities, relationships, and validation rules for the service center management system.

## Core Entities

### Inventory Item

**Purpose**: Central catalog of all products and parts managed by the service center

**Fields**:

- `id`: UUID (Primary Key)
- `product_code`: String (Unique, indexed) - Internal product identifier
- `description`: String (Required) - Human-readable product description
- `hsn_code`: String (Required) - Harmonized System of Nomenclature code for GST
- `gst_rate`: Decimal (Required) - GST percentage (5, 12, 18, 28)
- `current_stock`: Integer (Default: 0) - Current available quantity
- `minimum_stock_level`: Integer (Default: 0) - Reorder threshold
- `purchase_price`: Decimal (2 decimal places) - Cost price from supplier
- `selling_price`: Decimal (2 decimal places) - Retail price to customer
- `supplier_id`: UUID (Foreign Key to Supplier)
- `category`: Enum (pump, motor, spare_part, service) - Product classification
- `is_active`: Boolean (Default: True) - Product availability status
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Validation Rules**:

- GST rate must be valid Indian GST rate (0, 5, 12, 18, 28)
- Purchase price must be positive
- Selling price must be >= purchase price
- HSN code must follow Indian GST format

**Relationships**:

- Many-to-One: Supplier
- One-to-Many: Stock Movements
- Many-to-Many: Service Orders (through line items)

### Customer

**Purpose**: Customer information for billing and service tracking

**Fields**:

- `id`: UUID (Primary Key)
- `name`: String (Required) - Customer name
- `contact_phone`: String (Required) - Primary contact number
- `contact_email`: String (Optional) - Email address
- `gstin`: String (Optional) - GST Identification Number for B2B customers
- `address_line1`: String (Required) - Street address
- `address_line2`: String (Optional) - Additional address details
- `city`: String (Required) - City name
- `state`: String (Required) - State for GST calculation
- `pincode`: String (Required) - Postal code
- `customer_type`: Enum (individual, business) - Customer classification
- `payment_terms`: Integer (Default: 0) - Payment due days
- `credit_limit`: Decimal (Default: 0) - Maximum outstanding amount
- `is_active`: Boolean (Default: True) - Customer status
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Validation Rules**:

- Phone number must be valid Indian format
- GSTIN must be valid format if provided (15 characters)
- State must be valid Indian state for tax calculation
- Credit limit must be non-negative

**Relationships**:

- One-to-Many: Service Orders
- One-to-Many: Invoices

### Service Order

**Purpose**: Work orders for services and parts installation

**Fields**:

- `id`: UUID (Primary Key)
- `order_number`: String (Unique, auto-generated) - Human-readable order reference
- `customer_id`: UUID (Foreign Key, Required) - Associated customer
- `service_date`: Date (Required) - Scheduled or completed service date
- `status`: Enum (pending, in_progress, completed, cancelled) - Order status
- `description`: Text (Required) - Service description or work details
- `labor_charges`: Decimal (Default: 0) - Service charges before tax
- `discount_percentage`: Decimal (Default: 0) - Discount applied
- `total_amount`: Decimal (Calculated) - Total including parts and labor
- `gst_amount`: Decimal (Calculated) - Total GST amount
- `final_amount`: Decimal (Calculated) - Final payable amount
- `payment_status`: Enum (pending, partial, paid) - Payment tracking
- `notes`: Text (Optional) - Additional remarks
- `technician_id`: UUID (Optional) - Assigned technician
- `created_by`: UUID (Foreign Key to User) - Order creator
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Validation Rules**:

- Service date cannot be in the past (except for updates)
- Labor charges must be non-negative
- Discount percentage must be between 0-100
- Status transitions must follow business rules

**Relationships**:

- Many-to-One: Customer
- Many-to-One: User (creator)
- One-to-Many: Service Order Line Items
- One-to-One: Invoice (when completed)

### Service Order Line Item

**Purpose**: Individual parts/items used in a service order

**Fields**:

- `id`: UUID (Primary Key)
- `service_order_id`: UUID (Foreign Key, Required)
- `inventory_item_id`: UUID (Foreign Key, Required)
- `quantity`: Integer (Required) - Quantity used
- `unit_price`: Decimal (Required) - Price per unit at time of order
- `line_total`: Decimal (Calculated) - Quantity × unit_price
- `gst_rate`: Decimal (Required) - GST rate at time of order
- `gst_amount`: Decimal (Calculated) - GST for this line item
- `created_at`: Timestamp

**Validation Rules**:

- Quantity must be positive
- Unit price must be positive
- Available stock must be sufficient for quantity

**Relationships**:

- Many-to-One: Service Order
- Many-to-One: Inventory Item

### Invoice

**Purpose**: GST-compliant billing documents

**Fields**:

- `id`: UUID (Primary Key)
- `invoice_number`: String (Unique, sequential) - Legal invoice number
- `invoice_date`: Date (Required) - Invoice generation date
- `customer_id`: UUID (Foreign Key, Required)
- `service_order_id`: UUID (Foreign Key, Optional) - Associated service order
- `customer_gstin`: String (Optional) - Customer GSTIN at time of invoice
- `place_of_supply`: String (Required) - State for GST calculation
- `subtotal`: Decimal (Required) - Amount before taxes
- `discount_amount`: Decimal (Default: 0) - Total discount applied
- `cgst_amount`: Decimal (Default: 0) - Central GST amount
- `sgst_amount`: Decimal (Default: 0) - State GST amount
- `igst_amount`: Decimal (Default: 0) - Integrated GST amount
- `total_tax_amount`: Decimal (Calculated) - Sum of all taxes
- `total_amount`: Decimal (Calculated) - Final invoice amount
- `payment_method`: Enum (cash, card, upi, bank_transfer) - Payment mode
- `payment_status`: Enum (pending, partial, paid) - Payment status
- `payment_date`: Date (Optional) - Date of full payment
- `due_date`: Date (Required) - Payment due date
- `terms_and_conditions`: Text (Optional) - Invoice terms
- `is_cancelled`: Boolean (Default: False) - Cancellation status
- `cancellation_reason`: Text (Optional) - Reason for cancellation
- `created_by`: UUID (Foreign Key to User)
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Validation Rules**:

- Invoice number must be sequential and unique
- Payment date cannot be before invoice date
- Tax amounts must be correctly calculated based on location
- Cannot be modified after being paid (except cancellation)

**Relationships**:

- Many-to-One: Customer
- Many-to-One: Service Order (optional)
- Many-to-One: User (creator)
- One-to-Many: Invoice Line Items

### Supplier

**Purpose**: Vendor management for inventory purchases

**Fields**:

- `id`: UUID (Primary Key)
- `name`: String (Required) - Supplier company name
- `contact_person`: String (Optional) - Primary contact name
- `phone`: String (Required) - Contact phone number
- `email`: String (Optional) - Email address
- `gstin`: String (Optional) - Supplier GSTIN
- `address`: Text (Required) - Complete address
- `city`: String (Required)
- `state`: String (Required)
- `pincode`: String (Required)
- `payment_terms`: Integer (Default: 30) - Payment due days
- `is_active`: Boolean (Default: True)
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Validation Rules**:

- GSTIN must be valid format if provided
- Phone number must be valid
- Payment terms must be positive

**Relationships**:

- One-to-Many: Inventory Items
- One-to-Many: Stock Movements (purchases)

### Stock Movement

**Purpose**: Audit trail for all inventory changes

**Fields**:

- `id`: UUID (Primary Key)
- `inventory_item_id`: UUID (Foreign Key, Required)
- `movement_type`: Enum (purchase, sale, adjustment, return) - Transaction type
- `quantity`: Integer (Required) - Positive for inbound, negative for outbound
- `unit_price`: Decimal (Optional) - Price per unit for purchases/sales
- `reference_document`: String (Optional) - Invoice/PO number
- `reference_id`: UUID (Optional) - Related order/purchase ID
- `running_balance`: Integer (Required) - Stock level after this movement
- `reason`: String (Optional) - Adjustment reason
- `movement_date`: Date (Required) - Date of movement
- `created_by`: UUID (Foreign Key to User)
- `created_at`: Timestamp

**Validation Rules**:

- Running balance cannot be negative
- Movement date cannot be in the future
- Quantity cannot be zero

**Relationships**:

- Many-to-One: Inventory Item
- Many-to-One: User (creator)

### Tax Configuration

**Purpose**: GST rate management and tax calculation rules

**Fields**:

- `id`: UUID (Primary Key)
- `hsn_code`: String (Required, Unique) - HSN code
- `description`: String (Required) - Product category description
- `gst_rate`: Decimal (Required) - Applicable GST rate
- `effective_from`: Date (Required) - Rate effective date
- `effective_until`: Date (Optional) - Rate expiry date
- `is_active`: Boolean (Default: True)
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Validation Rules**:

- GST rate must be valid (0, 5, 12, 18, 28)
- Effective dates must be logical
- HSN code must be valid format

### User Account

**Purpose**: System user management and access control

**Fields**:

- `id`: UUID (Primary Key)
- `username`: String (Unique, Required) - Login username
- `email`: String (Unique, Required) - Email address
- `password_hash`: String (Required) - Hashed password
- `full_name`: String (Required) - Display name
- `role`: Enum (admin, operator, viewer) - Access level
- `gst_preference`: Boolean (Default: True) - Enable GST features
- `is_active`: Boolean (Default: True) - Account status
- `last_login`: Timestamp (Optional)
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Validation Rules**:

- Username must be alphanumeric
- Email must be valid format
- Password must meet security requirements

**Relationships**:

- One-to-Many: Service Orders (created)
- One-to-Many: Invoices (created)
- One-to-Many: Stock Movements (created)

## Entity Relationships Summary

```
Customer ||--o{ ServiceOrder : places
ServiceOrder ||--o{ ServiceOrderLineItem : contains
ServiceOrder ||--o| Invoice : generates
InventoryItem ||--o{ ServiceOrderLineItem : used_in
InventoryItem ||--o{ StockMovement : tracks_changes
Supplier ||--o{ InventoryItem : supplies
User ||--o{ ServiceOrder : creates
User ||--o{ Invoice : creates
User ||--o{ StockMovement : records
TaxConfiguration ||--o{ InventoryItem : defines_rates
```

## Data Integrity Rules

1. **Financial Consistency**: All calculated amounts must match sum of components
2. **Stock Consistency**: Stock movements must maintain accurate running balances
3. **GST Compliance**: Tax calculations must follow Indian GST rules
4. **Audit Trail**: All financial transactions must be traceable
5. **Referential Integrity**: Foreign key relationships must be maintained

## Performance Considerations

1. **Indexing Strategy**:

   - Primary keys (UUID) - B-tree indexes
   - Foreign keys - B-tree indexes
   - Search fields (product_code, invoice_number) - Unique indexes
   - Date ranges (invoice_date, service_date) - B-tree indexes

2. **Query Optimization**:

   - Inventory queries by category and active status
   - Customer search by name and phone
   - Invoice queries by date range and status
   - Stock movement queries by item and date range

3. **Data Archival**:
   - Archive completed orders older than 2 years
   - Maintain GST compliance data for 6 years
   - Regular cleanup of cancelled/void transactions

This data model supports all constitutional requirements for testing, performance, and observability while ensuring GST compliance and business rule enforcement.
