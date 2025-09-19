#!/usr/bin/env python3
"""
Test script untuk memverifikasi semua API endpoint Production Simulator
"""

import requests
import json

API_BASE = "http://localhost:8000"

def test_endpoint(method, url, expected_status=200, data=None):
    """Test a single endpoint"""
    try:
        if method.upper() == "GET":
            response = requests.get(url)
        elif method.upper() == "POST":
            response = requests.post(url, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url)
        else:
            return False, f"Unsupported method: {method}"
        
        if response.status_code == expected_status:
            return True, f"✅ {method} {url} - Status: {response.status_code}"
        else:
            return False, f"❌ {method} {url} - Expected: {expected_status}, Got: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"❌ {method} {url} - Error: {str(e)}"

def main():
    print("🔧 Testing Production Simulator API Endpoints")
    print("=" * 50)
    
    # Test endpoints
    endpoints = [
        ("GET", f"{API_BASE}/health", 200),
        ("GET", f"{API_BASE}/", 200),
        ("GET", f"{API_BASE}/setups/production/", 200),
        ("GET", f"{API_BASE}/setups/logistics/", 200),
        ("GET", f"{API_BASE}/master/locations/", 200),
        ("GET", f"{API_BASE}/master/transport-units/", 200),
        ("GET", f"{API_BASE}/master/process-templates/", 200),
        ("GET", f"{API_BASE}/production/status", 200),
        ("GET", f"{API_BASE}/logistics/status", 200),
        # Test CRUD operations
        ("POST", f"{API_BASE}/master/transport-units/", 200, {
            "name": "Test Unit",
            "type": "Test",
            "num_sub_units": 1,
            "capacity_per_sub_unit": 2,
            "description": "Test description"
        }),
        ("PUT", f"{API_BASE}/master/transport-units/3", 200, {
            "name": "Updated Unit",
            "type": "Updated",
            "num_sub_units": 2,
            "capacity_per_sub_unit": 3,
            "description": "Updated description"
        }),
        ("DELETE", f"{API_BASE}/master/transport-units/3", 200),
        # Test CRUD operations for locations
        ("POST", f"{API_BASE}/master/locations/", 200, {
            "name": "Test Location",
            "description": "Test location description",
            "stock": 100
        }),
        ("PUT", f"{API_BASE}/master/locations/1", 200, {
            "name": "Updated Location",
            "description": "Updated location description",
            "stock": 200
        }),
        ("DELETE", f"{API_BASE}/master/locations/1", 200),
    ]
    
    passed = 0
    total = len(endpoints)
    
    for endpoint in endpoints:
        if len(endpoint) == 3:
            method, url, expected_status = endpoint
            data = None
        else:
            method, url, expected_status, data = endpoint
        
        success, message = test_endpoint(method, url, expected_status, data)
        print(message)
        if success:
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} endpoints working")
    
    if passed == total:
        print("🎉 All API endpoints are working correctly!")
        print("✅ Frontend should now work without 404 errors")
    else:
        print("⚠️  Some endpoints are not working. Check the errors above.")
    
    print("\n🌐 Frontend URL: http://localhost:3001")
    print("📚 API Docs: http://localhost:8000/docs")

if __name__ == "__main__":
    main()
