# GitaGPT AI Coding Instructions

## Project Overview
GitaGPT is a distributed AI system combining semantic search, speech processing, and robotics to answer Bhagavad Gita questions. The architecture spans **server-client** with optional **Arduino integration**.

## Architecture & Data Flow
```
Client (Pi) → [Audio] → Server (Windows) → [Whisper ASR] → [FAISS Search] → [LLM] → [TTS] → [Audio] → Client → Arduino
```

**Key Components:**
- **Server**: Flask app with Whisper, FAISS, sentence-transformers, Ollama/transformers, Piper TTS
- **Client**: Audio recording/playback, Arduino jaw control, HTTP communication  
- **Data**: 700+ Gita verses in CSV, pre-built FAISS embeddings index
- **Hardware**: Raspberry Pi client, Arduino servo control, USB audio

## Critical File Patterns

### Server Files (`server/`)
- `server_faiss_semantic.py` - **Main production server** (FAISS + semantic search)
- `server.py` - Alternative with Ollama integration
- Both use **identical Flask API**: `/health`, `/process_audio` (POST with raw PCM bytes)

### Client Files (`client/`)
- `client.py` - **Full humanoid robot client** (audio + Arduino jaw control)
- `pi_client_with_audio.py` - Audio-only version without Arduino
- **Audio handling**: Supports sounddevice → pyaudio → system command fallbacks

### Configuration Pattern
All scripts use **hardcoded paths and IPs** that must be updated:
```python
# These MUST be changed for deployment
LAPTOP_IP = "192.168.104.80"  # Server IP
GITA_CSV_PATH = r"C:\Users\Raghuram S\OneDrive\Desktop\gitaGPT\..."
ARDUINO_PORT = "/dev/ttyUSB0"  # Pi-specific
```

## Development Workflows

### Testing Sequence
1. **Server health**: `python tests/test_server.py` (checks `/health` endpoint)
2. **Local functions**: `python tests/test_local.py` 
3. **Client connection**: Run client, check server logs for audio processing

### Arduino Integration
- **Single-character commands**: `'O'` (open jaw), `'c'` (close), `'s'` (stop)
- **Jaw animation**: 9-second cycles (3s open → 3s closed → 3s open) during TTS playback
- **Serial debugging**: Use `ls /dev/tty*` to find Arduino port

### Audio Pipeline
```
Record (int16 PCM) → HTTP POST → Whisper → FAISS search → LLM → TTS → hex WAV → Client playback
```
**Critical**: Client/server must match audio settings: 16kHz, mono, int16

## Project-Specific Conventions

### Error Handling Pattern
```python
# All clients use graceful audio fallbacks
if HAS_SOUNDDEVICE:
    self.audio_method = "sounddevice" 
elif HAS_PYAUDIO:
    self.audio_method = "pyaudio"
else:
    self.audio_method = "system"  # aplay, omxplayer, etc.
```

### FAISS Index Management
- **Auto-generation**: If `gita_faiss.index` missing, builds from CSV
- **Embedding model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim)
- **Search**: Retrieves top-k similar verses for LLM context

### LLM Fallback Chain
1. **Ollama** (if `ollama serve` running) → `gemma3:1b`
2. **Transformers** fallback → `bigscience/bloom` 
3. **Error handling**: Returns generic spiritual guidance

### TTS Priority
1. **Piper TTS** (.onnx voice models) - highest quality
2. **pyttsx3** - cross-platform fallback
3. **win32com SAPI** - Windows-only fallback

## Integration Points

### Network Communication
- **Flask REST API**: Raw PCM audio in request body, JSON response with hex-encoded WAV
- **Health checks**: Client validates `/health` before audio processing
- **IP configuration**: Hardcoded IPs must match network topology

### File Dependencies
- **Required data**: `bhagavad_gita_verses.csv` (642 verses with translations)
- **Optional models**: Piper voice files (`.onnx` + `.json`)
- **Generated**: `gita_faiss.index` (cached embeddings)

### Virtual Environment Pattern
```bash
# Server (Windows)
python -m venv gitagpt
.\gitagpt\Scripts\Activate.ps1

# Client (Pi)  
python3 -m venv gitaenv
source gitaenv/bin/activate
```

## Common Debugging Patterns

### Audio Issues
- **Test recording**: Check `RECORD_SECONDS`, sample rate matching
- **Playback failure**: Verify audio system, try different players
- **Empty response**: Check server logs for Whisper transcription

### Arduino Connection
- **Port detection**: `ls /dev/tty*` on Pi, try USB0/ACM0
- **Jaw not moving**: Verify Arduino sketch uploaded, check serial connection
- **Serial errors**: Ensure baudrate matches (9600), check permissions

### Server Performance  
- **Model loading**: Requires 8GB+ RAM for Whisper + embeddings
- **FAISS build**: First run takes time to generate embeddings
- **Ollama**: Optional but improves response quality when available

## Key Files for AI Agents
- `GitaGPT_Setup_Instructions.md` - Complete deployment guide
- `server_faiss_semantic.py` - Core semantic search implementation  
- `client.py` - Full robotics integration reference
- `bhagavad_gita_verses.csv` - Complete spiritual knowledge base