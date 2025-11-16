#!/usr/bin/env python3
"""
Quick test script to check if GitaGPT server is working
"""
import requests
import time

SERVER_IP = "10.12.187.47"
SERVER_PORT = 5000

def test_server():
    """Test if server is responding"""
    try:
        print(f"Testing server at http://{SERVER_IP}:{SERVER_PORT}")
        
        # Test health endpoint
        response = requests.get(f"http://{SERVER_IP}:{SERVER_PORT}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is healthy!")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Models loaded: {data.get('models_loaded', 'unknown')}")
            return True
        else:
            print(f"❌ Server responded with status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server")
        print(f"   Make sure:")
        print(f"   1. Server is running: python server_v5.py")
        print(f"   2. Firewall allows port 5000")
        print(f"   3. Server is listening on {SERVER_IP}:{SERVER_PORT}")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Server timeout (might be starting up)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_greeting():
    """Test greeting endpoint"""
    try:
        print(f"\nTesting greeting endpoint...")
        response = requests.get(f"http://{SERVER_IP}:{SERVER_PORT}/greet", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Greeting works!")
            print(f"   Response: {data.get('response', 'No response')}")
            print(f"   Audio available: {'Yes' if data.get('audio') else 'No'}")
            return True
        else:
            print(f"❌ Greeting failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Greeting error: {e}")
        return False

if __name__ == "__main__":
    print("🕉️  GitaGPT Server Test 🕉️")
    print("="*40)
    
    # Test health first
    if test_server():
        # If health works, test greeting
        if test_greeting():
            print(f"\n🎉 Server is fully working!")
            print(f"   Your Pi can now connect to: {SERVER_IP}:{SERVER_PORT}")
        else:
            print(f"\n⚠️  Server health OK but greeting failed")
    else:
        print(f"\n❌ Server is not responding")
        print(f"   Start the server first with: python server_v5.py")
    
    print(f"\nNext steps:")
    print(f"1. Make sure server is running and this test passes")
    print(f"2. Copy pi_client.py to your Raspberry Pi")
    print(f"3. Run the client on Pi to test full system")