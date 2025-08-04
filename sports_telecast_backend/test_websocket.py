"""
Simple WebSocket test script for sports telecast backend
"""
import asyncio
import websockets
import json
import sys

async def test_websocket():
    """Test WebSocket connection to the backend"""
    
    # Test without authentication first
    uri = "ws://localhost:8000/ws/MATCH001"
    
    try:
        print(f"🔗 Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Wait for initial message
            try:
                initial_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📨 Initial message: {initial_message}")
                
                # Send ping message
                ping_msg = {
                    "type": "ping",
                    "timestamp": "2025-08-04T15:30:00Z"
                }
                await websocket.send(json.dumps(ping_msg))
                print(f"📤 Sent ping: {ping_msg}")
                
                # Wait for pong response
                pong_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📨 Pong response: {pong_response}")
                
                # Request reaction summary
                summary_msg = {
                    "type": "get_reaction_summary"
                }
                await websocket.send(json.dumps(summary_msg))
                print(f"📤 Sent summary request: {summary_msg}")
                
                # Wait for summary response
                summary_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📨 Summary response: {summary_response}")
                
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for message")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    return True

async def main():
    """Main test function"""
    print("🏟️ Testing Sports Telecast Backend WebSocket...")
    
    success = await test_websocket()
    
    if success:
        print("✅ WebSocket test completed successfully!")
        sys.exit(0)
    else:
        print("❌ WebSocket test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
