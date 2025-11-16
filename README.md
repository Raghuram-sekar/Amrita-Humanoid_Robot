# GitaGPT - AI-Powered Bhagavad Gita Q&A with Humanoid Robot

🕉️ **An intelligent conversational AI that answers questions about the Bhagavad Gita with semantic search and humanoid robot integration.**

## 🌟 Features

- **Semantic Search**: FAISS-powered vector search across 700+ Gita verses
- **Multi-modal AI**: Whisper speech-to-text + LLM text generation + Piper TTS
- **Humanoid Integration**: Arduino-controlled jaw movement synchronized with responses
- **Flexible Deployment**: Server-client architecture supporting Windows/Linux/Raspberry Pi
- **Multiple TTS Options**: Piper TTS, pyttsx3, and system fallbacks
- **Real-time Audio**: Live recording, processing, and playback

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client (Pi)   │◄──►│  Server (Win)   │◄──►│   Arduino       │
│                 │    │                 │    │                 │
│ • Audio capture │    │ • Whisper ASR   │    │ • Jaw movement  │
│ • Audio playback│    │ • FAISS search  │    │ • Servo control │
│ • User interface│    │ • LLM generation│    │                 │
│ • Arduino ctrl │    │ • Piper TTS     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Server Setup (Windows)

1. **Install Dependencies**
   ```powershell
   python -m venv gitagpt
   .\gitagpt\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Install Ollama** (Optional for advanced LLM)
   ```powershell
   # Download from https://ollama.com/download
   ollama pull gemma3:1b
   ollama serve
   ```

3. **Run Server**
   ```powershell
   cd server
   python server_faiss_semantic.py
   ```

### Client Setup (Raspberry Pi)

1. **Install Dependencies**
   ```bash
   python3 -m venv gitaenv
   source gitaenv/bin/activate
   pip install -r requirements-pi.txt
   ```

2. **Configure Network**
   ```python
   # Edit client/config.py
   LAPTOP_IP = "192.168.1.100"  # Your server IP
   ARDUINO_PORT = "/dev/ttyUSB0"  # Your Arduino port
   ```

3. **Run Client**
   ```bash
   cd client
   python client.py
   ```

## 📁 Project Structure

```
gitagpt/
├── 📁 server/              # Server-side components
│   ├── server_faiss_semantic.py  # Main server with FAISS
│   ├── server.py           # Alternative server with Ollama
│   └── requirements.txt    # Server dependencies
│
├── 📁 client/              # Client-side components
│   ├── client.py          # Full humanoid robot client
│   ├── pi_client_with_audio.py  # Audio-only Pi client
│   ├── config.py          # Client configuration
│   └── requirements.txt   # Client dependencies
│
├── 📁 3D Files/            # Humanoid robot 3D models
│   ├── Articulating Neck/ # Neck movement components
│   ├── eye/               # Eye movement and tracking parts
│   ├── Neck/              # Basic neck structure
│   ├── Robotic arm/       # Arm movement components
│   ├── back_collar.stl    # Back collar piece
│   └── front camera collar.stl  # Front camera mount
│
├── 📁 data/               # Data files
│   ├── bhagavad_gita_verses.csv  # Gita verses dataset
│   └── gita_faiss.index   # Pre-built FAISS index
│
├── 📁 models/             # AI models
│   ├── en_GB-southern_english_female-low.onnx  # Piper TTS voice
│   └── en_GB-southern_english_female-low.onnx.json
│
├── 📁 tests/              # Testing utilities
│   ├── test_server.py     # Server connectivity test
│   └── test_local.py      # Local functionality test
│
└── 📁 docs/               # Documentation
    ├── setup-guide.md     # Detailed setup instructions
    ├── hardware.md       # Hardware setup guide
    └── api.md             # API documentation
```

## 🔧 Configuration

### Server Configuration
Edit `server/config.py` or use environment variables:

```python
# Network
HOST = "0.0.0.0"
PORT = 5000

# Audio
SAMPLE_RATE = 16000
CHANNELS = 1

# AI Models
WHISPER_MODEL = "small"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_MODEL = "gemma3:1b"
```

### Client Configuration
Edit `client/config.py`:

```python
# Network
LAPTOP_IP = "192.168.1.100"
LAPTOP_PORT = 5000

# Arduino
ARDUINO_PORT = "/dev/ttyUSB0"
ARDUINO_BAUDRATE = 9600

# Audio
RECORD_SECONDS = 10
```

## 🎯 Usage

1. **Start the server** on your Windows machine
2. **Connect Arduino** to Raspberry Pi (for humanoid version)
3. **Run the client** on Raspberry Pi
4. **Press ENTER** to record your question about the Gita
5. **Listen** to Krishna's wisdom with synchronized jaw movement

### Example Questions
- "What is dharma according to Krishna?"
- "How can I overcome fear and anxiety?"
- "What is the meaning of life?"
- "How should I make difficult decisions?"

## 🛠️ Hardware Requirements

### Server (Windows/Linux)
- **CPU**: Multi-core processor for Whisper/embeddings
- **RAM**: 8GB+ recommended
- **Storage**: 5GB for models and data
- **Network**: Wi-Fi/Ethernet for client communication

### Client (Raspberry Pi)
- **Model**: Pi 4B (4GB+) recommended
- **Audio**: USB microphone + speakers/headphones
- **Arduino**: For jaw control (optional)
- **Network**: Wi-Fi connection to server

### Arduino (Humanoid)
- **Board**: Arduino Uno/Nano
- **Servo**: For jaw movement
- **Connection**: USB to Raspberry Pi

### 3D Printed Parts
- **Head Assembly**: Front/back collar, neck components
- **Eye Tracking**: Eyeball mechanisms, gear holders, support structures  
- **Robotic Arms**: Complete arm movement assembly
- **Files**: All STL files included in `3D Files/` directory
- **Printer**: FDM printer (PLA/PETG compatible)

## 🔗 API Endpoints

### Health Check
```
GET /health
Response: {"status": "healthy", "models_loaded": true}
```

### Process Audio
```
POST /process_audio
Body: Raw PCM audio bytes (int16, 16kHz, mono)
Response: {
  "transcription": "What is dharma?",
  "response": "According to Krishna...",
  "audio": "hex-encoded-wav-bytes"
}
```

## 🔍 Troubleshooting

### Common Issues

**"Connection refused"**
- Check server IP address in client config
- Ensure server is running and accessible
- Verify firewall settings

**"Arduino not found"**
- Check USB connection
- Try different ports: `/dev/ttyUSB0`, `/dev/ttyACM0`
- Verify Arduino code is uploaded

**"Audio playback failed"**
- Install audio dependencies: `sudo apt install alsa-utils`
- Test with: `aplay test_audio.wav`
- Check speaker/headphone connection

**"Models not loading"**
- Ensure sufficient RAM (8GB+)
- Check file paths in configuration
- Verify FAISS index exists

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📜 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- **Bhagavad Gita translations** from various scholarly sources
- **OpenAI Whisper** for speech recognition
- **FAISS** by Facebook AI for semantic search
- **Piper TTS** for natural speech synthesis
- **Sentence Transformers** for text embeddings

---

*"You have a right to perform your prescribed duty, but do not be attached to the fruits of action."* - Bhagavad Gita 2.47
