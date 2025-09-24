"""
Performance monitoring and benchmarking tools for GST Service Center Management System.
Ensures constitutional compliance with <200ms API response times and load capacity.
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from contextlib import asynccontextmanager

import httpx
import pytest
from locust import HttpUser, task, between


@dataclass
class PerformanceMetrics:
    """Data class for storing performance test results."""
    endpoint: str
    method: str
    response_times: List[float]
    success_rate: float
    error_count: int
    p50: float
    p95: float
    p99: float
    max_response_time: float
    constitutional_compliance: bool  # <200ms p95 requirement


class APIPerformanceTester:
    """
    Performance testing utility for API endpoints.
    Validates constitutional requirement of <200ms p95 response times.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)

    async def test_endpoint_performance(
        self,
        endpoint: str,
        method: str = "GET",
        payload: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        iterations: int = 100,
        concurrent_requests: int = 10
    ) -> PerformanceMetrics:
        """
        Test API endpoint performance with concurrent requests.

        Args:
            endpoint: API endpoint to test
            method: HTTP method
            payload: Request payload for POST/PUT requests
            headers: Request headers
            iterations: Total number of requests to make
            concurrent_requests: Number of concurrent requests

        Returns:
            PerformanceMetrics with timing data and constitutional compliance
        """
        response_times = []
        error_count = 0

        async def make_request() -> Tuple[float, bool]:
            """Make a single request and return (response_time, success)."""
            start_time = time.time()
            try:
                if method.upper() == "GET":
                    response = await self.client.get(endpoint, headers=headers)
                elif method.upper() == "POST":
                    response = await self.client.post(endpoint, json=payload, headers=headers)
                elif method.upper() == "PUT":
                    response = await self.client.put(endpoint, json=payload, headers=headers)
                elif method.upper() == "DELETE":
                    response = await self.client.delete(endpoint, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response_time = (time.time() - start_time) * \
                    1000  # Convert to milliseconds
                return response_time, response.status_code < 400
            except Exception:
                response_time = (time.time() - start_time) * 1000
                return response_time, False

        # Execute requests in batches of concurrent_requests
        for i in range(0, iterations, concurrent_requests):
            batch_size = min(concurrent_requests, iterations - i)
            tasks = [make_request() for _ in range(batch_size)]

            batch_results = await asyncio.gather(*tasks)

            for response_time, success in batch_results:
                response_times.append(response_time)
                if not success:
                    error_count += 1

        # Calculate percentiles
        sorted_times = sorted(response_times)
        p50 = self._percentile(sorted_times, 50)
        p95 = self._percentile(sorted_times, 95)
        p99 = self._percentile(sorted_times, 99)

        success_rate = (iterations - error_count) / iterations * 100
        constitutional_compliance = p95 <= 200.0  # Constitutional requirement

        return PerformanceMetrics(
            endpoint=endpoint,
            method=method,
            response_times=response_times,
            success_rate=success_rate,
            error_count=error_count,
            p50=p50,
            p95=p95,
            p99=p99,
            max_response_time=max(response_times),
            constitutional_compliance=constitutional_compliance
        )

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of response times."""
        if not data:
            return 0.0
        index = (percentile / 100) * (len(data) - 1)
        if index == int(index):
            return data[int(index)]
        else:
            lower = data[int(index)]
            upper = data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class LoadTestUser(HttpUser):
    """
    Locust load testing user for GST Service Center Management System.
    Simulates realistic user behavior for capacity testing.
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    host = "http://localhost:8000"

    def on_start(self):
        """Login and get JWT token before starting load test."""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "test_admin",
            "password": "test_password"
        })
        if response.status_code == 200:
            token = response.json()["data"]["access_token"]
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            self.headers = {}

    @task(5)
    def list_inventory_items(self):
        """List inventory items - most common operation."""
        self.client.get("/api/v1/inventory/items", headers=self.headers)

    @task(3)
    def get_customer_list(self):
        """List customers."""
        self.client.get("/api/v1/customers", headers=self.headers)

    @task(2)
    def create_service_order(self):
        """Create a new service order."""
        payload = {
            "customer_id": "550e8400-e29b-41d4-a716-446655440001",
            "service_date": "2024-01-15",
            "description": "Load test service order",
            "labor_charges": 500.00,
            "line_items": []
        }
        self.client.post("/api/v1/service-orders",
                         json=payload, headers=self.headers)

    @task(2)
    def generate_gst_report(self):
        """Generate GST summary report."""
        self.client.get(
            "/api/v1/reports/gst-summary?month=1&year=2024", headers=self.headers)

    @task(1)
    def create_invoice(self):
        """Create invoice - less frequent but important operation."""
        payload = {
            "customer_id": "550e8400-e29b-41d4-a716-446655440001",
            "line_items": [
                {
                    "description": "Water pump 1HP",
                    "hsn_code": "84137090",
                    "quantity": 1,
                    "unit_price": 5000.00,
                    "gst_rate": 18.0
                }
            ],
            "payment_method": "cash",
            "due_date": "2024-01-30"
        }
        self.client.post("/api/v1/invoices", json=payload,
                         headers=self.headers)


@asynccontextmanager
async def performance_test_context():
    """Context manager for performance testing setup and cleanup."""
    tester = APIPerformanceTester()
    try:
        yield tester
    finally:
        await tester.close()


async def run_constitutional_performance_audit() -> Dict[str, PerformanceMetrics]:
    """
    Run comprehensive performance audit to verify constitutional compliance.
    Tests all critical endpoints against <200ms p95 requirement.

    Returns:
        Dictionary mapping endpoint names to performance metrics
    """
    results = {}

    # Define critical endpoints to test
    endpoints_to_test = [
        ("health_check", "GET", "/health", None),
        ("auth_login", "POST", "/api/v1/auth/login",
         {"username": "test", "password": "test"}),
        ("inventory_list", "GET", "/api/v1/inventory/items", None),
        ("customers_list", "GET", "/api/v1/customers", None),
        ("service_orders_list", "GET", "/api/v1/service-orders", None),
        ("invoices_list", "GET", "/api/v1/invoices", None),
        ("gst_report", "GET", "/api/v1/reports/gst-summary?month=1&year=2024", None),
    ]

    async with performance_test_context() as tester:
        for test_name, method, endpoint, payload in endpoints_to_test:
            print(f"Testing {test_name}: {method} {endpoint}")

            metrics = await tester.test_endpoint_performance(
                endpoint=endpoint,
                method=method,
                payload=payload,
                iterations=50,
                concurrent_requests=5
            )

            results[test_name] = metrics

            # Print results
            compliance_status = "✅ PASS" if metrics.constitutional_compliance else "❌ FAIL"
            print(
                f"  P95: {metrics.p95:.1f}ms | Success: {metrics.success_rate:.1f}% | {compliance_status}")

    return results


def generate_performance_report(results: Dict[str, PerformanceMetrics]) -> str:
    """Generate a formatted performance test report."""
    report = []
    report.append("# GST Service Center Performance Test Report")
    report.append(f"Constitutional Requirement: API responses <200ms p95")
    report.append("")

    compliant_count = sum(1 for metrics in results.values()
                          if metrics.constitutional_compliance)
    total_count = len(results)

    report.append(f"## Summary")
    report.append(f"- Endpoints tested: {total_count}")
    report.append(
        f"- Constitutional compliance: {compliant_count}/{total_count}")
    report.append(
        f"- Overall compliance rate: {(compliant_count/total_count)*100:.1f}%")
    report.append("")

    report.append("## Detailed Results")
    report.append(
        "| Endpoint | Method | P50 | P95 | P99 | Success Rate | Compliance |")
    report.append(
        "|----------|--------|-----|-----|-----|--------------|------------|")

    for test_name, metrics in results.items():
        compliance = "✅" if metrics.constitutional_compliance else "❌"
        report.append(
            f"| {test_name} | {metrics.method} | {metrics.p50:.1f}ms | "
            f"{metrics.p95:.1f}ms | {metrics.p99:.1f}ms | {metrics.success_rate:.1f}% | {compliance} |"
        )

    return "\n".join(report)


if __name__ == "__main__":
    # Run performance audit when script is executed directly
    async def main():
        results = await run_constitutional_performance_audit()
        report = generate_performance_report(results)
        print("\n" + report)

        # Save report to file
        with open("performance_report.md", "w") as f:
            f.write(report)

    asyncio.run(main())
