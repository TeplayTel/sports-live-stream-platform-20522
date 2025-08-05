"""
Comprehensive API testing script for Sports Telecast Backend
Tests all major endpoints and functionality

"""
import requests
import time
import sys
from typing import Optional

BASE_URL = "http://localhost:3001"

class APITester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.token: Optional[str] = None
        
    def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        print("🔍 Testing health check endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data['message']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_user_registration(self) -> bool:
        """Test user registration"""
        print("🔍 Testing user registration...")
        try:
            user_data = {
                "email": "testuser@example.com",
                "username": "testuser123",
                "password": "securepassword123",
                "full_name": "Test User"
            }
            
            response = self.session.post(
                f"{self.base_url}/auth/register",
                json=user_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                print(f"✅ User registration successful: {data['user']['username']}")
                print(f"🔑 Token received: {self.token[:20]}...")
                return True
            else:
                print(f"❌ Registration failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    def test_matches_list(self) -> bool:
        """Test getting matches list"""
        print("🔍 Testing matches list...")
        try:
            response = self.session.get(f"{self.base_url}/matches/")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Matches list: {data['total']} matches found")
                return True
            else:
                print(f"❌ Matches list failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Matches list error: {e}")
            return False
    
    def test_live_matches(self) -> bool:
        """Test getting live matches"""
        print("🔍 Testing live matches...")
        try:
            response = self.session.get(f"{self.base_url}/matches/live")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Live matches: {data['total']} live matches")
                if data['total'] > 0:
                    match = data['matches'][0]
                    print(f"📺 Sample: {match['home_team']['name']} vs {match['away_team']['name']}")
                return True
            else:
                print(f"❌ Live matches failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Live matches error: {e}")
            return False
    
    def test_emoji_list(self) -> bool:
        """Test emoji list endpoint"""
        if not self.token:
            print("❌ No token available for emoji test")
            return False
            
        print("🔍 Testing emoji list...")
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(
                f"{self.base_url}/fan-engagement/emoji/v1/listEmojis",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Emoji list: {len(data['emojis'])} emojis available")
                for emoji in data['emojis'][:3]:  # Show first 3
                    print(f"😊 {emoji['name']}: {emoji['emoji_type']}")
                return True
            else:
                print(f"❌ Emoji list failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Emoji list error: {e}")
            return False
    
    def test_emoji_reaction(self) -> bool:
        """Test emoji reaction submission"""
        if not self.token:
            print("❌ No token available for emoji reaction test")
            return False
            
        print("🔍 Testing emoji reaction...")
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            reaction_data = {
                "event_id": "MATCH001",
                "emoji_id": "EMJ103",
                "created_at": "2025-08-04T15:30:00Z"
            }
            
            response = self.session.post(
                f"{self.base_url}/fan-engagement/emoji/v1/userEmojiReaction",
                headers=headers,
                json=reaction_data
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Emoji reaction successful: {data['status']}")
                return True
            else:
                print(f"❌ Emoji reaction failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Emoji reaction error: {e}")
            return False
    
    def test_reaction_summary(self) -> bool:
        """Test getting reaction summary"""
        print("🔍 Testing reaction summary...")
        try:
            response = self.session.get(
                f"{self.base_url}/fan-engagement/emoji/v1/reactions/MATCH001"
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Reaction summary: {data['total_reactions']} total reactions")
                if data['top_emojis']:
                    print("🏆 Top reactions:")
                    for emoji in data['top_emojis'][:3]:
                        print(f"  {emoji['emoji_type']}: {emoji['count']} reactions")
                return True
            else:
                print(f"❌ Reaction summary failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Reaction summary error: {e}")
            return False
    
    def test_highlights(self) -> bool:
        """Test highlights endpoint"""
        print("🔍 Testing highlights...")
        try:
            response = self.session.get(f"{self.base_url}/highlights/")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Highlights: {data['total']} highlights available")
                if data['highlights']:
                    highlight = data['highlights'][0]
                    print(f"🎬 Sample: {highlight['title']} ({highlight['duration']}s)")
                return True
            else:
                print(f"❌ Highlights failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Highlights error: {e}")
            return False
    
    def test_websocket_stats(self) -> bool:
        """Test WebSocket statistics"""
        print("🔍 Testing WebSocket stats...")
        try:
            response = self.session.get(f"{self.base_url}/ws/stats")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ WebSocket stats: {data['total_connections']} active connections")
                return True
            else:
                print(f"❌ WebSocket stats failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ WebSocket stats error: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all API tests"""
        print("🏟️ Starting Sports Telecast Backend API Tests...\n")
        
        tests = [
            ("Health Check", self.test_health_check),
            ("User Registration", self.test_user_registration),
            ("Matches List", self.test_matches_list),
            ("Live Matches", self.test_live_matches),
            ("Emoji List", self.test_emoji_list),
            ("Emoji Reaction", self.test_emoji_reaction),
            ("Reaction Summary", self.test_reaction_summary),
            ("Highlights", self.test_highlights),
            ("WebSocket Stats", self.test_websocket_stats),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            print(f"\n{'='*50}")
            print(f"Running: {test_name}")
            print('='*50)
            
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                failed += 1
            
            time.sleep(0.5)  # Brief pause between tests
        
        print(f"\n{'='*50}")
        print("📊 TEST RESULTS")
        print('='*50)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        return failed == 0

def main():
    """Main test function"""
    print("🚀 Sports Telecast Backend API Test Suite")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print(f"❌ Server not responding correctly at {BASE_URL}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print(f"   Error: {e}")
        print("   Make sure the server is running with: uvicorn src.api.main:app --host 0.0.0.0 --port 3001")
        sys.exit(1)
    
    tester = APITester(BASE_URL)
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! API is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
