"""
Server Configuration for GitaGPT
"""
import os

# Network Configuration
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))

# Audio Configuration
SAMPLE_RATE = int(os.environ.get("SAMPLE_RATE", 16000))
CHANNELS = int(os.environ.get("CHANNELS", 1))

# AI Model Configuration
TOP_K = int(os.environ.get("TOP_K", 5))
EMBED_MODEL_NAME = os.environ.get("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
WHISPER_MODEL_NAME = os.environ.get("WHISPER_MODEL_NAME", "small")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:1b")
TRANSFORMER_MODEL = os.environ.get("TRANSFORMER_MODEL", "bigscience/bloom")

# File Paths (Update these paths for your system)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITA_CSV_PATH = os.environ.get("GITA_CSV_PATH", os.path.join(BASE_DIR, "data", "bhagavad_gita_verses.csv"))
FAISS_INDEX_PATH = os.environ.get("FAISS_INDEX_PATH", os.path.join(BASE_DIR, "data", "gita_faiss.index"))
PIPER_VOICE_PATH = os.environ.get("PIPER_VOICE_PATH", os.path.join(BASE_DIR, "models", "en_GB-southern_english_female-low.onnx"))

# Conversation Control
EXIT_PHRASES = ["thank you", "thanks", "that's all", "nothing else", "goodbye"]
FOLLOW_UP_PHRASES = [
    "Is there anything else I can help you with?",
    "Would you like to explore this teaching further?", 
    "Any other spiritual questions?",
    "How can Krishna's wisdom guide you today?",
    "What other aspects of dharma interest you?"
]