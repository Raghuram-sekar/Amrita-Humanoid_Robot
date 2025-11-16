# GitaGPT Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Clone & Setup
```bash
git clone <your-repo-url> gitagpt
cd gitagpt
python setup.py
```

### Step 2: Configure Network
**Edit `client/config.py`:**
```python
LAPTOP_IP = "YOUR_SERVER_IP_HERE"  # Find with: ipconfig (Windows) or ifconfig (Linux)
```

**Edit `server/config.py` if needed:**
```python
HOST = "0.0.0.0"  # Allow connections from other devices
PORT = 5000       # Default port
```

### Step 3: Start Server (Windows/Linux)
```bash
# Activate environment
source gitagpt/bin/activate  # Linux
# OR
.\gitagpt\Scripts\activate   # Windows

# Start server
cd server
python server_faiss_semantic.py
```

### Step 4: Start Client (Raspberry Pi)
```bash
# Activate environment  
source gitaenv/bin/activate

# Start client
cd client
python client.py
```

### Step 5: Ask Questions! 🙏
- Press ENTER to record
- Ask about dharma, karma, life's purpose
- Listen to Krishna's wisdom

## 📱 Quick Commands

### Test Server Health
```bash
curl http://YOUR_SERVER_IP:5000/health
```

### Find Arduino Port (Pi)
```bash
ls /dev/tty*
# Update ARDUINO_PORT in client/config.py
```

### Audio Test (Pi)
```bash
# Test microphone
arecord -d 3 test.wav && aplay test.wav

# Test speakers
speaker-test -t wav
```

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Check server IP in `client/config.py` |
| "Arduino not found" | Check USB connection, try `/dev/ttyUSB0` or `/dev/ttyACM0` |
| "No audio" | Install: `sudo apt install alsa-utils portaudio19-dev` |
| "Models not loading" | Ensure 8GB+ RAM, check file paths |
| "Slow responses" | Use smaller Whisper model: `WHISPER_MODEL = "tiny"` |

## 📁 Project Structure
```
gitagpt/
├── 🖥️  server/           # Server components
├── 📱 client/           # Client components  
├── 🤖 3D Files/         # Humanoid robot 3D models
├── 📊 data/             # Gita verses & search index
├── 🎤 models/           # TTS voice models
├── 📚 docs/             # Documentation
├── 🧪 tests/            # Testing utilities
└── ⚙️  config files     # Setup & deployment
```

## 🎯 Example Questions
- *"What does Krishna say about overcoming fear?"*
- *"How should I make difficult decisions?"*
- *"What is the meaning of dharma?"*
- *"How can I find inner peace?"*

---
**🕉️ "You have a right to perform your prescribed duty, but do not be attached to the fruits of action." - Bhagavad Gita 2.47**