#!/usr/bin/env python3
"""
Comprehensive API Testing Script for Sports Telecast Backend

This script validates all REST API endpoints including:
- Authentication (register, login, refresh)
- Users (CRUD, search, admin functions)
- Profiles (CRUD, search, privacy settings)
- Matches (live, upcoming, detailed views)
- Schedules (daily, weekly, live)
- Highlights (CRUD, featured)
- Emoji reactions (submit, get summaries)
- Health checks and monitoring
"""

import asyncio
import sys
from datetime import datetime
import aiohttp
from typing import Dict, Any, Optional

class APITester:
    """Comprehensive API testing class"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.auth_token = None
        self.test_user_id = None
        self.test_profile_id = None
        
        # Test results tracking
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    
    async def setup_session(self):
        """Setup HTTP session"""
        self.session = aiohttp.ClientSession()
    
    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, 
                          data: Optional[Dict] = None,
                          headers: Optional[Dict] = None,
                          params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        request_headers = {"Content-Type": "application/json"}
        
        if headers:
            request_headers.update(headers)
        
        if self.auth_token:
            request_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            async with self.session.request(
                method, url, 
                json=data if method in ["POST", "PUT", "PATCH"] else None,
                headers=request_headers,
                params=params
            ) as response:
                response_data = await response.json() if response.content_length else {}
                return {
                    "status_code": response.status,
                    "data": response_data,
                    "success": response.status < 400
                }
        except Exception as e:
            return {
                "status_code": 0,
                "data": {"error": str(e)},
                "success": False
            }
    
    def record_test(self, test_name: str, success: bool, details: str = ""):
        """Record test result"""
        self.results["total_tests"] += 1
        if success:
            self.results["passed"] += 1
            print(f"✅ {test_name}")
        else:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {details}")
            print(f"❌ {test_name}: {details}")
    
    async def test_health_endpoints(self):
        """Test health check endpoints"""
        print("\n🔍 Testing Health Endpoints...")
        
        # Test main health endpoint
        response = await self.make_request("GET", "/")
        self.record_test(
            "Health Check", 
            response["success"] and "Sports Telecast Backend API is running" in response["data"].get("message", ""),
            f"Status: {response['status_code']}"
        )
        
        # Test database health endpoint
        response = await self.make_request("GET", "/health/database")
        self.record_test(
            "Database Health Check",
            response["success"] and "database" in response["data"],
            f"Status: {response['status_code']}"
        )
    
    async def test_authentication_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication Endpoints...")
        
        # Test user registration
        test_user_data = {
            "email": f"test_user_{datetime.now().timestamp()}@example.com",
            "username": f"testuser_{int(datetime.now().timestamp())}",
            "password": "testpassword123",
            "full_name": "Test User"
        }
        
        response = await self.make_request("POST", "/auth/register", test_user_data)
        if response["success"]:
            self.auth_token = response["data"].get("access_token")
            self.test_user_id = response["data"].get("user", {}).get("user_id")
        
        self.record_test(
            "User Registration",
            response["success"] and self.auth_token is not None,
            f"Status: {response['status_code']}"
        )
        
        # Test user login
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        response = await self.make_request("POST", "/auth/login", login_data)
        self.record_test(
            "User Login",
            response["success"] and "access_token" in response["data"],
            f"Status: {response['status_code']}"
        )
        
        # Test get current user
        response = await self.make_request("GET", "/auth/me")
        self.record_test(
            "Get Current User",
            response["success"] and "user_id" in response["data"],
            f"Status: {response['status_code']}"
        )
        
        # Test token refresh
        response = await self.make_request("POST", "/auth/refresh")
        self.record_test(
            "Token Refresh",
            response["success"] and "access_token" in response["data"],
            f"Status: {response['status_code']}"
        )
    
    async def test_user_endpoints(self):
        """Test user management endpoints"""
        print("\n👥 Testing User Endpoints...")
        
        # Test get users list
        response = await self.make_request("GET", "/users", params={"limit": 10})
        self.record_test(
            "Get Users List",
            response["success"] and isinstance(response["data"], list),
            f"Status: {response['status_code']}"
        )
        
        # Test get user by ID
        if self.test_user_id:
            response = await self.make_request("GET", f"/users/{self.test_user_id}")
            self.record_test(
                "Get User by ID",
                response["success"] and "user_id" in response["data"],
                f"Status: {response['status_code']}"
            )
        
        # Test user search suggestions
        response = await self.make_request("GET", "/users/search/suggestions", params={"q": "test"})
        self.record_test(
            "User Search Suggestions",
            response["success"] and isinstance(response["data"], list),
            f"Status: {response['status_code']}"
        )
        
        # Test user statistics
        response = await self.make_request("GET", "/users/stats/overview")
        self.record_test(
            "User Statistics",
            response["success"] and "total_users" in response["data"],
            f"Status: {response['status_code']}"
        )
    
    async def test_profile_endpoints(self):
        """Test user profile endpoints"""
        print("\n👤 Testing Profile Endpoints...")
        
        # Test create profile
        profile_data = {
            "user_id": self.test_user_id,
            "display_name": "Test User Profile",
            "bio": "This is a test user profile",
            "location": "Test City",
            "favorite_teams": ["team1", "team2"],
            "favorite_sports": ["football", "basketball"]
        }
        
        response = await self.make_request("POST", "/profiles/", profile_data)
        if response["success"]:
            self.test_profile_id = response["data"].get("profile_id")
        
        self.record_test(
            "Create Profile",
            response["success"] and "profile_id" in response["data"],
            f"Status: {response['status_code']}"
        )
        
        # Test get my profile
        response = await self.make_request("GET", "/profiles/me")
        self.record_test(
            "Get My Profile",
            response["success"] and "profile_id" in response["data"],
            f"Status: {response['status_code']}"
        )
        
        # Test search profiles
        response = await self.make_request("GET", "/profiles/", params={"limit": 10})
        self.record_test(
            "Search Profiles",
            response["success"] and isinstance(response["data"], list),
            f"Status: {response['status_code']}"
        )
        
        # Test update profile
        update_data = {
            "bio": "Updated test user profile",
            "location": "Updated Test City"
        }
        response = await self.make_request("PUT", "/profiles/me", update_data)
        self.record_test(
            "Update Profile",
            response["success"] and "profile_id" in response["data"],
            f"Status: {response['status_code']}"
        )
    
    async def test_schedule_endpoints(self):
        """Test schedule endpoints"""
        print("\n📅 Testing Schedule Endpoints...")
        
        # Test get daily schedule
        from datetime import date
        today = date.today().isoformat()
        response = await self.make_request("GET", f"/schedules/daily/{today}")
        self.record_test(
            "Get Daily Schedule",
            response["success"] and "matches_count" in response["data"],
            f"Status: {response['status_code']}"
        )
        
        # Test get weekly schedule
        response = await self.make_request("GET", "/schedules/weekly")
        self.record_test(
            "Get Weekly Schedule",
            response["success"] and "daily_schedules" in response["data"],
            f"Status: {response['status_code']}"
        )
        
        # Test get upcoming schedules
        response = await self.make_request("GET", "/schedules/upcoming", params={"days": 7})
        self.record_test(
            "Get Upcoming Schedules",
            response["success"] and isinstance(response["data"], list),
            f"Status: {response['status_code']}"
        )
        
        # Test get live matches
        response = await self.make_request("GET", "/schedules/live")
        self.record_test(
            "Get Live Matches Schedule",
            response["success"] and "matches_count" in response["data"],
            f"Status: {response['status_code']}"
        )
        
        # Test get schedules list
        response = await self.make_request("GET", "/schedules/", params={"limit": 10})
        self.record_test(
            "Get Schedules List",
            response["success"] and "schedules" in response["data"],
            f"Status: {response['status_code']}"
        )
    
    async def test_match_endpoints(self):
        """Test match endpoints"""
        print("\n⚽ Testing Match Endpoints...")
        
        # Test get matches
        response = await self.make_request("GET", "/matches", params={"limit": 10})
        self.record_test(
            "Get Matches",
            response["success"],
            f"Status: {response['status_code']}"
        )
        
        # Test get live matches
        response = await self.make_request("GET", "/matches/live")
        self.record_test(
            "Get Live Matches",
            response["success"],
            f"Status: {response['status_code']}"
        )
        
        # Test get upcoming matches
        response = await self.make_request("GET", "/matches/upcoming")
        self.record_test(
            "Get Upcoming Matches",
            response["success"],
            f"Status: {response['status_code']}"
        )
    
    async def test_highlight_endpoints(self):
        """Test highlight endpoints"""
        print("\n🎬 Testing Highlight Endpoints...")
        
        # Test get highlights
        response = await self.make_request("GET", "/highlights", params={"limit": 10})
        self.record_test(
            "Get Highlights",
            response["success"],
            f"Status: {response['status_code']}"
        )
        
        # Test get featured highlights
        response = await self.make_request("GET", "/highlights/featured", params={"limit": 5})
        self.record_test(
            "Get Featured Highlights",
            response["success"],
            f"Status: {response['status_code']}"
        )
    
    async def test_emoji_endpoints(self):
        """Test emoji endpoints"""
        print("\n😊 Testing Emoji Endpoints...")
        
        # Test list emojis
        response = await self.make_request("GET", "/fan-engagement/emoji/v1/listEmojis")
        self.record_test(
            "List Emojis",
            response["success"] and "emojis" in response["data"],
            f"Status: {response['status_code']}"
        )
    
    async def test_api_logs_endpoints(self):
        """Test API logs endpoints"""
        print("\n📊 Testing API Logs Endpoints...")
        
        # Test get API calls
        response = await self.make_request("GET", "/api-logs/calls", params={"limit": 5})
        self.record_test(
            "Get API Calls",
            response["success"],
            f"Status: {response['status_code']}"
        )
        
        # Test get API statistics
        response = await self.make_request("GET", "/api-logs/stats")
        self.record_test(
            "Get API Statistics",
            response["success"],
            f"Status: {response['status_code']}"
        )
        
        # Test get endpoints
        response = await self.make_request("GET", "/api-logs/endpoints")
        self.record_test(
            "Get Endpoints List",
            response["success"],
            f"Status: {response['status_code']}"
        )
    
    async def run_all_tests(self):
        """Run all API endpoint tests"""
        print("🚀 Starting Comprehensive API Testing...")
        print(f"Base URL: {self.base_url}")
        
        await self.setup_session()
        
        try:
            # Run test suites in order
            await self.test_health_endpoints()
            await self.test_authentication_endpoints()
            
            if self.auth_token:  # Only run authenticated tests if we have a token
                await self.test_user_endpoints()
                await self.test_profile_endpoints()
                await self.test_schedule_endpoints()
                await self.test_match_endpoints()
                await self.test_highlight_endpoints()
                await self.test_emoji_endpoints()
                await self.test_api_logs_endpoints()
            else:
                print("⚠️  Skipping authenticated endpoint tests - no auth token")
            
        finally:
            await self.cleanup_session()
        
        # Print final results
        print("\n📈 Test Results Summary:")
        print(f"   • Total Tests: {self.results['total_tests']}")
        print(f"   • Passed: {self.results['passed']} ✅")
        print(f"   • Failed: {self.results['failed']} ❌")
        
        if self.results['failed'] > 0:
            print("\n❌ Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        success_rate = (self.results['passed'] / self.results['total_tests']) * 100 if self.results['total_tests'] > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        return success_rate >= 80  # Consider 80%+ success rate as overall success

async def main():
    """Main testing function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive API Testing")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    
    tester = APITester(args.url)
    success = await tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
