# API Contracts
## GST Compliant Service Center Management System

This document defines the REST API contracts for all service endpoints.

## Base Configuration

**Base URL**: `/api/v1`  
**Authentication**: Bearer JWT token  
**Content-Type**: `application/json`  
**Response Format**: JSON with consistent error structure

## Common Response Formats

### Success Response
```json
{
  "status": "success",
  "data": { /* response data */ },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": { /* additional error context */ }
  }
}
```

### Pagination Response
```json
{
  "status": "success",
  "data": {
    "items": [ /* array of items */ ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 150,
      "total_pages": 8,
      "has_next": true,
      "has_previous": false
    }
  }
}
```

## Authentication Endpoints

### POST /auth/login
**Purpose**: User authentication and JWT token generation

**Request**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response (200)**:
```json
{
  "status": "success",
  "data": {
    "access_token": "jwt_token_string",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": "uuid",
      "username": "string",
      "full_name": "string",
      "role": "admin|operator|viewer",
      "gst_preference": true
    }
  }
}
```

### POST /auth/refresh
**Purpose**: Refresh expired JWT tokens

**Request**:
```json
{
  "refresh_token": "string"
}
```

### POST /auth/logout
**Purpose**: Invalidate current session

## Inventory Management

### GET /inventory/items
**Purpose**: List inventory items with filtering and pagination

**Query Parameters**:
- `page`: int (default: 1)
- `page_size`: int (default: 20, max: 100)
- `category`: string (pump|motor|spare_part|service)
- `search`: string (search in product_code, description)
- `low_stock`: boolean (items below minimum level)
- `active_only`: boolean (default: true)

**Response (200)**:
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": "uuid",
        "product_code": "string",
        "description": "string",
        "hsn_code": "string",
        "gst_rate": 18.0,
        "current_stock": 25,
        "minimum_stock_level": 10,
        "purchase_price": 1500.00,
        "selling_price": 2000.00,
        "category": "pump",
        "supplier": {
          "id": "uuid",
          "name": "string"
        },
        "is_active": true,
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-01T10:00:00Z"
      }
    ],
    "pagination": { /* pagination object */ }
  }
}
```

### POST /inventory/items
**Purpose**: Create new inventory item

**Request**:
```json
{
  "product_code": "string",
  "description": "string",
  "hsn_code": "string",
  "gst_rate": 18.0,
  "minimum_stock_level": 10,
  "purchase_price": 1500.00,
  "selling_price": 2000.00,
  "supplier_id": "uuid",
  "category": "pump"
}
```

**Response (201)**:
```json
{
  "status": "success",
  "data": {
    "id": "uuid",
    /* full item object */
  },
  "message": "Inventory item created successfully"
}
```

### GET /inventory/items/{item_id}
**Purpose**: Get inventory item details

**Response (200)**:
```json
{
  "status": "success",
  "data": {
    "id": "uuid",
    /* full item object with stock movements */
    "recent_movements": [
      {
        "id": "uuid",
        "movement_type": "sale",
        "quantity": -2,
        "movement_date": "2024-01-01",
        "reference_document": "INV-001",
        "running_balance": 23
      }
    ]
  }
}
```

### PUT /inventory/items/{item_id}
**Purpose**: Update inventory item

**Request**: Same as POST with updated fields

### DELETE /inventory/items/{item_id}
**Purpose**: Deactivate inventory item (soft delete)

### POST /inventory/items/{item_id}/stock-adjustment
**Purpose**: Adjust stock levels

**Request**:
```json
{
  "quantity": 10,
  "reason": "Physical stock verification",
  "movement_type": "adjustment"
}
```

## Customer Management

### GET /customers
**Purpose**: List customers with search and pagination

**Query Parameters**:
- `page`, `page_size`: pagination
- `search`: string (name, phone, gstin)
- `customer_type`: string (individual|business)
- `active_only`: boolean

**Response (200)**:
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": "uuid",
        "name": "string",
        "contact_phone": "string",
        "contact_email": "string",
        "gstin": "string",
        "address": {
          "line1": "string",
          "line2": "string",
          "city": "string",
          "state": "string",
          "pincode": "string"
        },
        "customer_type": "business",
        "payment_terms": 30,
        "credit_limit": 50000.00,
        "outstanding_amount": 15000.00,
        "is_active": true
      }
    ],
    "pagination": { /* pagination object */ }
  }
}
```

### POST /customers
**Purpose**: Create new customer

**Request**:
```json
{
  "name": "string",
  "contact_phone": "string",
  "contact_email": "string",
  "gstin": "string",
  "address_line1": "string",
  "address_line2": "string",
  "city": "string",
  "state": "string",
  "pincode": "string",
  "customer_type": "business",
  "payment_terms": 30,
  "credit_limit": 50000.00
}
```

### GET /customers/{customer_id}
**Purpose**: Get customer details with transaction history

### PUT /customers/{customer_id}
**Purpose**: Update customer information

## Service Order Management

### GET /service-orders
**Purpose**: List service orders with filtering

**Query Parameters**:
- `page`, `page_size`: pagination
- `status`: string (pending|in_progress|completed|cancelled)
- `customer_id`: uuid
- `date_from`, `date_to`: date range
- `search`: string (order_number, customer_name)

**Response (200)**:
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": "uuid",
        "order_number": "SO-001",
        "customer": {
          "id": "uuid",
          "name": "string",
          "contact_phone": "string"
        },
        "service_date": "2024-01-15",
        "status": "completed",
        "description": "Pump repair and maintenance",
        "labor_charges": 500.00,
        "parts_total": 1500.00,
        "total_amount": 2000.00,
        "gst_amount": 360.00,
        "final_amount": 2360.00,
        "payment_status": "paid",
        "created_at": "2024-01-01T10:00:00Z"
      }
    ],
    "pagination": { /* pagination object */ }
  }
}
```

### POST /service-orders
**Purpose**: Create new service order

**Request**:
```json
{
  "customer_id": "uuid",
  "service_date": "2024-01-15",
  "description": "Pump repair and maintenance",
  "labor_charges": 500.00,
  "discount_percentage": 5.0,
  "line_items": [
    {
      "inventory_item_id": "uuid",
      "quantity": 2,
      "unit_price": 750.00
    }
  ],
  "notes": "Customer requested urgent repair"
}
```

**Response (201)**:
```json
{
  "status": "success",
  "data": {
    "id": "uuid",
    "order_number": "SO-002",
    /* full order object */
  }
}
```

### GET /service-orders/{order_id}
**Purpose**: Get detailed service order with line items

### PUT /service-orders/{order_id}
**Purpose**: Update service order (only if not completed)

### PUT /service-orders/{order_id}/status
**Purpose**: Update order status

**Request**:
```json
{
  "status": "completed",
  "notes": "Work completed successfully"
}
```

### POST /service-orders/{order_id}/generate-invoice
**Purpose**: Generate invoice for completed service order

## Invoice Management

### GET /invoices
**Purpose**: List invoices with filtering

**Query Parameters**:
- `page`, `page_size`: pagination
- `customer_id`: uuid
- `date_from`, `date_to`: date range
- `payment_status`: string (pending|partial|paid)
- `search`: string (invoice_number, customer_name)

**Response (200)**:
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": "uuid",
        "invoice_number": "INV-001",
        "invoice_date": "2024-01-15",
        "customer": {
          "id": "uuid",
          "name": "string",
          "gstin": "string"
        },
        "subtotal": 2000.00,
        "discount_amount": 100.00,
        "cgst_amount": 171.00,
        "sgst_amount": 171.00,
        "igst_amount": 0.00,
        "total_tax_amount": 342.00,
        "total_amount": 2242.00,
        "payment_status": "paid",
        "payment_method": "upi",
        "due_date": "2024-01-30"
      }
    ],
    "pagination": { /* pagination object */ }
  }
}
```

### POST /invoices
**Purpose**: Create new invoice (manual billing)

**Request**:
```json
{
  "customer_id": "uuid",
  "service_order_id": "uuid", // optional
  "line_items": [
    {
      "description": "Water pump 1HP",
      "hsn_code": "84137090",
      "quantity": 1,
      "unit_price": 5000.00,
      "gst_rate": 18.0
    }
  ],
  "discount_amount": 0.00,
  "payment_method": "cash",
  "due_date": "2024-01-30"
}
```

### GET /invoices/{invoice_id}
**Purpose**: Get detailed invoice with line items

### GET /invoices/{invoice_id}/pdf
**Purpose**: Generate PDF invoice

**Response**: PDF file download

### PUT /invoices/{invoice_id}/payment
**Purpose**: Record payment

**Request**:
```json
{
  "payment_amount": 2242.00,
  "payment_date": "2024-01-16",
  "payment_method": "bank_transfer",
  "reference_number": "TXN123456"
}
```

## Reporting Endpoints

### GET /reports/gst-summary
**Purpose**: GST summary report for filing

**Query Parameters**:
- `month`: int (1-12)
- `year`: int
- `format`: string (json|pdf)

**Response (200)**:
```json
{
  "status": "success",
  "data": {
    "period": "2024-01",
    "total_sales": 100000.00,
    "cgst_collected": 9000.00,
    "sgst_collected": 9000.00,
    "igst_collected": 0.00,
    "total_tax_collected": 18000.00,
    "hsn_wise_summary": [
      {
        "hsn_code": "84137090",
        "description": "Water pumps",
        "total_amount": 50000.00,
        "tax_amount": 9000.00,
        "gst_rate": 18.0
      }
    ]
  }
}
```

### GET /reports/inventory-valuation
**Purpose**: Current inventory valuation report

### GET /reports/sales-summary
**Purpose**: Sales summary by period

**Query Parameters**:
- `date_from`, `date_to`: date range
- `group_by`: string (day|week|month)

## Health Check and Monitoring

### GET /health
**Purpose**: System health check

**Response (200)**:
```json
{
  "status": "success",
  "data": {
    "service": "healthy",
    "database": "healthy",
    "timestamp": "2024-01-01T10:00:00Z",
    "version": "1.0.0"
  }
}
```

### GET /metrics
**Purpose**: Prometheus metrics endpoint

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Request validation failed |
| UNAUTHORIZED | 401 | Authentication required |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| CONFLICT | 409 | Resource already exists |
| INSUFFICIENT_STOCK | 409 | Not enough inventory |
| INVALID_GST_CONFIG | 422 | GST configuration error |
| CALCULATION_ERROR | 422 | Tax calculation failed |
| INTERNAL_ERROR | 500 | Server error |

## Rate Limiting

- Authentication endpoints: 10 requests per minute per IP
- API endpoints: 100 requests per minute per user
- Report generation: 5 requests per minute per user

## Constitutional Compliance

This API design ensures:
- **Performance**: All endpoints designed for <200ms response time
- **Testing**: Complete contract testing with example requests/responses
- **Observability**: Health checks, metrics, and structured error responses
- **Quality**: Consistent patterns, validation, and error handling