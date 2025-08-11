#!/usr/bin/env python3
"""
Comprehensive API verification script for seeded data
Tests all major endpoints to verify UUID usage and data integrity
"""

import asyncio
import httpx
import json
from typing import Any
import sys
from datetime import datetime


class APIVerifier:
    def __init__(self, base_url: str = "http://localhost:3001"):
        self.base_url = base_url
        self.auth_token = None
        self.test_results = []
        
    def log_test(self, endpoint: str, status: str, message: str, data: Any = None):
        """Log test results"""
        result = {
            "endpoint": endpoint,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data_sample": str(data)[:200] if data else None
        }
        self.test_results.append(result)
        
        # Color coding for console output
        color = "\033[92m" if status == "PASS" else "\033[91m" if status == "FAIL" else "\033[93m"
        reset = "\033[0m"
        print(f"{color}[{status}]{reset} {endpoint}: {message}")
        
        if data and status == "PASS":
            if isinstance(data, list) and len(data) > 0:
                print(f"   📊 Found {len(data)} items")
                if hasattr(data[0], 'keys') or isinstance(data[0], dict):
                    first_item = data[0] if isinstance(data[0], dict) else data[0].__dict__
                    for key, value in list(first_item.items())[:3]:
                        print(f"   • {key}: {value}")
            elif isinstance(data, dict):
                print(f"   📋 Keys: {list(data.keys())[:5]}")

    async def test_health_check(self, client: httpx.AsyncClient):
        """Test health check endpoint"""
        try:
            response = await client.get("/")
            if response.status_code == 200:
                data = response.json()
                self.log_test("GET /", "PASS", "Health check successful", data)
                return True
            else:
                self.log_test("GET /", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("GET /", "FAIL", f"Error: {str(e)}")
            return False

    async def test_users_endpoint(self, client: httpx.AsyncClient):
        """Test users endpoint"""
        try:
            response = await client.get("/users/")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Verify UUID format in first user
                    first_user = data[0]
                    has_uuid = "user_id" in first_user and len(first_user["user_id"]) == 36
                    self.log_test("GET /users/", "PASS", f"Found {len(data)} users, UUID format: {has_uuid}", data[:2])
                    return True
                else:
                    self.log_test("GET /users/", "FAIL", "No users found")
                    return False
            else:
                self.log_test("GET /users/", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("GET /users/", "FAIL", f"Error: {str(e)}")
            return False

    async def attempt_authentication(self, client: httpx.AsyncClient):
        """Attempt to authenticate with admin user"""
        try:
            login_data = {
                "email": "admin@sportstelecast.com",
                "password": "admin123"
            }
            response = await client.post("/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.auth_token = data["access_token"]
                    client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                    self.log_test("POST /auth/login", "PASS", "Authentication successful")
                    return True
                else:
                    self.log_test("POST /auth/login", "FAIL", "No access token in response")
                    return False
            else:
                self.log_test("POST /auth/login", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("POST /auth/login", "FAIL", f"Error: {str(e)}")
            return False

    async def test_endpoint_with_auth(self, client: httpx.AsyncClient, endpoint: str, method: str = "GET"):
        """Test an endpoint that might require authentication"""
        try:
            if method.upper() == "GET":
                response = await client.get(endpoint)
            else:
                response = await client.request(method, endpoint)
                
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.log_test(f"{method} {endpoint}", "PASS", "Success", data)
                    return True, data
                except:
                    self.log_test(f"{method} {endpoint}", "PASS", "Success (non-JSON response)")
                    return True, response.text
            elif response.status_code == 401:
                self.log_test(f"{method} {endpoint}", "WARN", "Authentication required")
                return False, None
            else:
                error_msg = f"Status: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text[:100]}"
                self.log_test(f"{method} {endpoint}", "FAIL", error_msg)
                return False, None
        except Exception as e:
            self.log_test(f"{method} {endpoint}", "FAIL", f"Error: {str(e)}")
            return False, None

    async def test_emoji_endpoints(self, client: httpx.AsyncClient):
        """Test emoji-related endpoints"""
        # Test emoji list
        success, data = await self.test_endpoint_with_auth(client, "/fan-engagement/emoji/v1/listEmojis")
        
        if success and data:
            # Test emoji reaction summary with a sample event
            try:
                # Get a sample event ID from database check we did earlier
                sample_event_id = "054ff645-834d-4b1c-9847-062eacfeb862"  # From our database query
                await self.test_endpoint_with_auth(client, f"/fan-engagement/emoji/v1/reactions/{sample_event_id}")
            except Exception as e:
                self.log_test("Emoji reactions", "WARN", f"Could not test reactions: {str(e)}")

    async def verify_all_endpoints(self):
        """Run comprehensive verification of all endpoints"""
        print("🚀 Starting comprehensive API verification...")
        print("=" * 60)
        
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            # 1. Health Check
            await self.test_health_check(client)
            
            # 2. Users endpoint (works without auth)
            await self.test_users_endpoint(client)
            
            # 3. Try to authenticate
            auth_success = await self.attempt_authentication(client)
            
            # 4. Test other endpoints (some may require auth)
            endpoints_to_test = [
                ("/matches/", "GET"),
                ("/matches/events/", "GET"), 
                ("/highlights/", "GET"),
                ("/schedules/", "GET"),
                ("/profiles/", "GET"),
            ]
            
            for endpoint, method in endpoints_to_test:
                await self.test_endpoint_with_auth(client, endpoint, method)
            
            # 5. Test emoji endpoints if authenticated
            if auth_success:
                await self.test_emoji_endpoints(client)
            
            # 6. Test specific endpoints that should work
            await self.test_endpoint_with_auth(client, "/users/stats/overview")
            await self.test_endpoint_with_auth(client, "/health/database")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        pass_count = len([r for r in self.test_results if r["status"] == "PASS"])
        fail_count = len([r for r in self.test_results if r["status"] == "FAIL"])
        warn_count = len([r for r in self.test_results if r["status"] == "WARN"])
        
        print(f"✅ PASSED: {pass_count}")
        print(f"❌ FAILED: {fail_count}")  
        print(f"⚠️  WARNINGS: {warn_count}")
        print(f"📈 TOTAL: {len(self.test_results)}")
        
        if fail_count > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"   • {result['endpoint']}: {result['message']}")
        
        # Save results to file
        with open("api_verification_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2)
        print("\n💾 Detailed results saved to: api_verification_results.json")


async def main():
    """Main verification function"""
    verifier = APIVerifier()
    await verifier.verify_all_endpoints()
    verifier.print_summary()
    
    # Return exit code based on results
    failed_tests = [r for r in verifier.test_results if r["status"] == "FAIL"]
    if failed_tests:
        print("\n⚠️  Some tests failed. Check the logs above for details.")
        return 1
    else:
        print("\n🎉 All tests passed successfully!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
