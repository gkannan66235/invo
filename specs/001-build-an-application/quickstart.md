# Quickstart Guide

## GST Compliant Service Center Management System

This guide provides test scenarios and validation steps to verify system functionality and constitutional compliance.

## Prerequisites

Before running test scenarios, ensure:

- System is deployed and accessible
- Database is initialized with schema
- Authentication is configured
- Test data is loaded (optional for automated tests)

## Core Test Scenarios

### Scenario 1: User Authentication and Access Control

**Objective**: Verify secure user authentication and role-based access

**Test Steps**:

1. **Login with valid credentials**

   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "username": "test_admin",
       "password": "secure_password"
     }'
   ```

   **Expected**: HTTP 200, JWT token returned, user profile included

2. **Access protected endpoint with token**

   ```bash
   curl -X GET http://localhost:8000/api/v1/inventory/items \
     -H "Authorization: Bearer {jwt_token}"
   ```

   **Expected**: HTTP 200, inventory data returned

3. **Access with invalid token**

   ```bash
   curl -X GET http://localhost:8000/api/v1/inventory/items \
     -H "Authorization: Bearer invalid_token"
   ```

   **Expected**: HTTP 401, error response

**Performance Target**: Login <200ms, API access <200ms  
**Constitutional Check**: ✅ Authentication, security, performance

### Scenario 2: Inventory Management Workflow

**Objective**: Test complete inventory lifecycle with stock tracking

**Test Steps**:

1. **Create new inventory item**

   ```bash
   curl -X POST http://localhost:8000/api/v1/inventory/items \
     -H "Authorization: Bearer {jwt_token}" \
     -H "Content-Type: application/json" \
     -d '{
       "product_code": "PUMP001",
       "description": "Water Pump 1HP",
       "hsn_code": "84137090",
       "gst_rate": 18.0,
       "minimum_stock_level": 5,
       "purchase_price": 4000.00,
       "selling_price": 5000.00,
       "supplier_id": "{supplier_uuid}",
       "category": "pump"
     }'
   ```

   **Expected**: HTTP 201, item created with UUID

2. **Add initial stock**

   ```bash
   curl -X POST http://localhost:8000/api/v1/inventory/items/{item_id}/stock-adjustment \
     -H "Authorization: Bearer {jwt_token}" \
     -H "Content-Type: application/json" \
     -d '{
       "quantity": 10,
       "reason": "Initial stock entry",
       "movement_type": "adjustment"
     }'
   ```

   **Expected**: Stock movement recorded, balance updated

3. **Verify stock levels**

   ```bash
   curl -X GET http://localhost:8000/api/v1/inventory/items/{item_id} \
     -H "Authorization: Bearer {jwt_token}"
   ```

   **Expected**: Current stock = 10, recent movements visible

**Data Integrity Check**: Stock movements must maintain accurate running balance  
**Constitutional Check**: ✅ Testing coverage, data consistency

### Scenario 3: GST-Compliant Service Order and Billing

**Objective**: Verify end-to-end billing workflow with GST calculations

**Test Steps**:

1. **Create customer (B2B with GSTIN)**

   ```bash
   curl -X POST http://localhost:8000/api/v1/customers \
     -H "Authorization: Bearer {jwt_token}" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "ABC Motors Pvt Ltd",
       "contact_phone": "+91-9876543210",
       "contact_email": "contact@abcmotors.com",
       "gstin": "07AAACG2115R1ZN",
       "address_line1": "123 Industrial Area",
       "city": "Delhi",
       "state": "Delhi",
       "pincode": "110001",
       "customer_type": "business",
       "payment_terms": 30,
       "credit_limit": 100000.00
     }'
   ```

2. **Create service order with parts**

   ```bash
   curl -X POST http://localhost:8000/api/v1/service-orders \
     -H "Authorization: Bearer {jwt_token}" \
     -H "Content-Type: application/json" \
     -d '{
       "customer_id": "{customer_uuid}",
       "service_date": "2024-01-15",
       "description": "Pump installation and maintenance",
       "labor_charges": 1000.00,
       "discount_percentage": 5.0,
       "line_items": [
         {
           "inventory_item_id": "{pump_item_uuid}",
           "quantity": 1,
           "unit_price": 5000.00
         }
       ],
       "notes": "Customer site installation"
     }'
   ```

   **Expected**: Order created, stock reduced, totals calculated

3. **Generate GST-compliant invoice**

   ```bash
   curl -X POST http://localhost:8000/api/v1/service-orders/{order_id}/generate-invoice \
     -H "Authorization: Bearer {jwt_token}"
   ```

   **Expected**: Invoice with correct CGST/SGST split (9% each for Delhi)

4. **Verify GST calculations**
   - Subtotal: 5000 + 1000 = 6000
   - Discount (5%): 300
   - Taxable amount: 5700
   - CGST (9%): 513
   - SGST (9%): 513
   - Total: 6726

**GST Compliance Check**: Tax calculations must follow Indian GST rules  
**Constitutional Check**: ✅ Accuracy, compliance, observability

### Scenario 4: Inter-State Transaction (IGST)

**Objective**: Verify IGST calculation for inter-state sales

**Test Steps**:

1. **Create customer in different state**

   ```bash
   curl -X POST http://localhost:8000/api/v1/customers \
     -H "Authorization: Bearer {jwt_token}" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "XYZ Engineering",
       "contact_phone": "+91-9876543211",
       "gstin": "19AAACX2115R1ZN",
       "address_line1": "456 Tech Park",
       "city": "Pune",
       "state": "Maharashtra",
       "pincode": "411001",
       "customer_type": "business"
     }'
   ```

2. **Create invoice for inter-state sale**

   ```bash
   curl -X POST http://localhost:8000/api/v1/invoices \
     -H "Authorization: Bearer {jwt_token}" \
     -H "Content-Type: application/json" \
     -d '{
       "customer_id": "{maharashtra_customer_uuid}",
       "line_items": [
         {
           "description": "Water pump 1HP",
           "hsn_code": "84137090",
           "quantity": 1,
           "unit_price": 5000.00,
           "gst_rate": 18.0
         }
       ],
       "payment_method": "bank_transfer",
       "due_date": "2024-02-15"
     }'
   ```

3. **Verify IGST calculation**
   - Expected: IGST = 18% (900), CGST = 0, SGST = 0
   - Total: 5900

**Constitutional Check**: ✅ Cross-state compliance, accurate calculations

### Scenario 5: Performance and Load Testing

**Objective**: Verify system meets performance requirements

**Test Steps**:

1. **API Response Time Test**

   ```bash
   # Use Apache Bench for load testing
   ab -n 100 -c 10 -H "Authorization: Bearer {jwt_token}" \
     http://localhost:8000/api/v1/inventory/items
   ```

   **Expected**: 95th percentile < 200ms

2. **Database Query Performance**

   ```bash
   curl -X GET "http://localhost:8000/api/v1/invoices?date_from=2024-01-01&date_to=2024-12-31" \
     -H "Authorization: Bearer {jwt_token}" \
     -w "Time: %{time_total}s\n"
   ```

   **Expected**: Response time < 200ms even with large date ranges

3. **Concurrent User Simulation**

   ```bash
   # Simulate 50 concurrent users for 5 minutes
   ab -n 1000 -c 50 -t 300 -H "Authorization: Bearer {jwt_token}" \
     http://localhost:8000/api/v1/health
   ```

   **Expected**: No failures, stable response times

**Constitutional Check**: ✅ Performance requirements met

### Scenario 6: Offline Operation and Data Sync

**Objective**: Test offline capability and data synchronization

**Test Steps**:

1. **Create transactions while online**

   - Create service orders
   - Record stock movements
   - Generate invoices

2. **Simulate network disconnection**

   - Block external network access
   - Continue creating local transactions

3. **Verify offline operation**

   - Local database operations continue
   - Data cached locally
   - UI feedback remains responsive (<100ms)

4. **Restore connectivity and sync**
   - Re-enable network
   - Verify automatic sync process
   - Check data consistency

**Constitutional Check**: ✅ Reliability, user experience

## Health Check and Monitoring Validation

### System Health

```bash
curl -X GET http://localhost:8000/api/v1/health
```

**Expected Response**:

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

### Metrics Collection

```bash
curl -X GET http://localhost:8000/metrics
```

**Expected**: Prometheus metrics format with:

- Request count and duration
- Database connection pool stats
- Error rates by endpoint
- Custom business metrics (orders, invoices)

## Error Handling Validation

### Validation Errors

```bash
# Test invalid input
curl -X POST http://localhost:8000/api/v1/inventory/items \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "product_code": "",
    "gst_rate": 25.0
  }'
```

**Expected**: HTTP 400 with clear error messages

### Business Logic Errors

```bash
# Test insufficient stock
curl -X POST http://localhost:8000/api/v1/service-orders \
  -H "Authorization: Bearer {jwt_token}" \
  -d '{
    "line_items": [
      {
        "inventory_item_id": "{item_uuid}",
        "quantity": 999999
      }
    ]
  }'
```

**Expected**: HTTP 409 with INSUFFICIENT_STOCK error

## Automated Test Execution

### Unit Tests

```bash
# Run all unit tests with coverage
pytest tests/unit/ --cov=src --cov-report=html --cov-fail-under=80
```

**Constitutional Requirement**: 80% line coverage minimum

### Integration Tests

```bash
# Run end-to-end workflow tests
pytest tests/integration/ --verbose
```

**Constitutional Requirement**: 90% critical path coverage

### Contract Tests

```bash
# Validate API contracts
pytest tests/contract/ --api-spec=contracts/api-specification.md
```

**Constitutional Requirement**: All endpoints match specification

## Security Testing

### Authentication Tests

- Invalid credentials rejection
- Token expiration handling
- Role-based access control
- Password security requirements

### Data Protection Tests

- Sensitive data encryption
- SQL injection prevention
- Input validation
- Output sanitization

## Compliance Validation

### GST Compliance

- Tax calculation accuracy
- Invoice format compliance
- HSN code validation
- Audit trail completeness

### Data Retention

- 6-year GST data retention
- Backup verification
- Recovery testing
- Archive process validation

## Performance Benchmarks

| Metric                  | Target  | Test Method    |
| ----------------------- | ------- | -------------- |
| API Response Time (p95) | <200ms  | Load testing   |
| UI Feedback             | <100ms  | Manual testing |
| Database Queries        | <100ms  | Query analysis |
| Concurrent Users        | 50+     | Stress testing |
| Monthly Transactions    | 10K-50K | Volume testing |

## Constitutional Compliance Checklist

- ✅ **Code Quality**: Type hints, linting, formatting
- ✅ **Testing**: 80% line, 90% critical path coverage
- ✅ **Performance**: <200ms API, <100ms UI feedback
- ✅ **User Experience**: Consistent error handling, accessibility
- ✅ **Observability**: Logging, metrics, health checks

This quickstart guide ensures comprehensive testing of all system functionality while validating constitutional requirements and business compliance needs.
