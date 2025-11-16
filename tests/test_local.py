#!/usr/bin/env python3
"""
Test local server connectivity
"""
import requests

def test_localhost():
    try:
        response = requests.get("http://127.0.0.1:5000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server working on localhost!")
            return True
    except Exception as e:
        print(f"❌ Localhost test failed: {e}")
    return False

def test_network_ip():
    try:
        response = requests.get("http://10.12.187.47:5000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server working on network IP!")
            return True
    except Exception as e:
        print(f"❌ Network IP test failed: {e}")
    return False

print("Testing server connectivity...")
if test_localhost():
    if test_network_ip():
        print("🎉 Server is fully accessible!")
    else:
        print("⚠️  Server works locally but not on network")
        print("   This might be a firewall issue")
        print("   Please configure Windows Firewall to allow port 5000")
else:
    print("❌ Server not responding at all")