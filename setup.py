#!/usr/bin/env python3
"""
GitaGPT Setup Script
Automated setup for server and client components
"""
import os
import sys
import subprocess
import platform
import shutil
import urllib.request
from pathlib import Path

def run_command(cmd, description):
    """Run shell command with error handling"""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def check_python_version():
    """Ensure Python 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required")
        return False
    print(f"✅ Python {version.major}.{version.minor} detected")
    return True

def setup_server():
    """Setup server environment"""
    print("\n🖥️  Setting up GitaGPT Server...")
    
    # Create virtual environment
    if platform.system() == "Windows":
        venv_cmd = "python -m venv gitagpt"
        activate_cmd = ".\\gitagpt\\Scripts\\activate"
        pip_cmd = ".\\gitagpt\\Scripts\\pip"
    else:
        venv_cmd = "python3 -m venv gitagpt"
        activate_cmd = "source gitagpt/bin/activate"
        pip_cmd = "gitagpt/bin/pip"
    
    run_command(venv_cmd, "Creating virtual environment")
    
    # Install dependencies
    install_cmd = f"{pip_cmd} install -r server/requirements.txt"
    run_command(install_cmd, "Installing server dependencies")
    
    # Download required data files if missing
    data_dir = Path("data")
    if not (data_dir / "bhagavad_gita_verses.csv").exists():
        print("📥 Bhagavad Gita data file missing - please add bhagavad_gita_verses.csv to data/ directory")
    
    print("\n✅ Server setup complete!")
    if platform.system() == "Windows":
        print("🚀 Start server: .\\gitagpt\\Scripts\\activate && python server/server_faiss_semantic.py")
    else:
        print("🚀 Start server: source gitagpt/bin/activate && python server/server_faiss_semantic.py")

def setup_client():
    """Setup client environment"""
    print("\n📱 Setting up GitaGPT Client...")
    
    # Create virtual environment
    if platform.system() == "Windows":
        print("❌ Client setup is intended for Raspberry Pi/Linux")
        return
    
    venv_cmd = "python3 -m venv gitaenv"
    run_command(venv_cmd, "Creating client virtual environment")
    
    # Install dependencies
    install_cmd = "gitaenv/bin/pip install -r client/requirements.txt"
    if not run_command(install_cmd, "Installing client dependencies"):
        print("⚠️  Some audio dependencies may need system packages:")
        print("   sudo apt update")
        print("   sudo apt install python3-dev portaudio19-dev")
        print("   sudo apt install alsa-utils")
    
    print("\n✅ Client setup complete!")
    print("🚀 Start client: source gitaenv/bin/activate && python client/client.py")

def setup_ollama():
    """Setup Ollama for advanced AI"""
    print("\n🤖 Setting up Ollama...")
    
    if platform.system() == "Windows":
        print("📥 Please download Ollama from: https://ollama.com/download")
        print("   Then run: ollama pull gemma3:1b")
    else:
        # Try to install Ollama on Linux
        install_cmd = "curl -fsSL https://ollama.com/install.sh | sh"
        if run_command(install_cmd, "Installing Ollama"):
            run_command("ollama pull gemma3:1b", "Downloading Gemma model")

def check_configuration():
    """Check configuration files"""
    print("\n⚙️  Checking configuration...")
    
    server_config = Path("server/config.py")
    client_config = Path("client/config.py")
    
    if server_config.exists():
        print("✅ Server config found")
    else:
        print("❌ Server config missing")
    
    if client_config.exists():
        print("✅ Client config found")
        print("⚠️  Remember to update LAPTOP_IP in client/config.py")
    else:
        print("❌ Client config missing")

def main():
    """Main setup function"""
    print("🕉️  GitaGPT Setup Wizard")
    print("=" * 40)
    
    if not check_python_version():
        return
    
    print("\nWhat would you like to set up?")
    print("1. Server (Windows/Linux)")
    print("2. Client (Raspberry Pi/Linux)")
    print("3. Both")
    print("4. Just check configuration")
    
    try:
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            setup_server()
            print("\n💡 Don't forget to install Ollama for better AI responses!")
        elif choice == "2":
            setup_client()
        elif choice == "3":
            setup_server()
            setup_client()
        elif choice == "4":
            check_configuration()
        else:
            print("❌ Invalid choice")
            return
        
        # Always check configuration at the end
        check_configuration()
        
        print("\n🎉 Setup complete!")
        print("\n📚 Next steps:")
        print("   1. Update IP addresses in config files")
        print("   2. Place audio model files in models/ directory")
        print("   3. Ensure bhagavad_gita_verses.csv is in data/ directory")
        print("   4. Run tests with: python tests/test_server.py")
        print("\n📖 For detailed instructions, see docs/setup-guide.md")
        
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")

if __name__ == "__main__":
    main()