#!/usr/bin/env python3
"""
server.py (piper TTS variant)

Receives raw int16 mono PCM bytes at POST /process_audio, transcribes (Whisper),
retrieves Bhagavad Gita verses via FAISS, generates a reply using Ollama (if reachable)
or falls back to transformers, and returns JSON including an optional TTS WAV (hex).

TTS behavior:
 - Try Piper-based TTS (if piper package and voice .onnx file available)
 - Fallback to pyttsx3-based WAV generation
 - As last resort on Windows/COM try win32com SAPI
"""
import os
import time
import tempfile
import traceback
import io
import wave
from flask import Flask, request, jsonify
import numpy as np
import whisper
from sentence_transformers import SentenceTransformer
import faiss
import pandas as pd
from scipy.io.wavfile import write as wav_write
import pyttsx3
import re

# Optional Ollama client
_HAS_OLLAMA = False
try:
    import ollama
    _HAS_OLLAMA = True
except Exception:
    _HAS_OLLAMA = False

# === PIPER TTS integration ===
_HAS_PIPER = False
_piper_voice = None

# Keep your original voice path and instructions (maintained as requested)
# Update if you want different voice or use env var PIPER_VOICE_PATH
PIPER_VOICE_PATH = os.environ.get(
    "PIPER_VOICE_PATH",
    r"C:\Users\Raghuram S\OneDrive\Desktop\gitaGPT\en_GB-southern_english_female-low.onnx"
)

# optional default synthesis config values; can be overridden if you want
_PIPER_SYN_CFG = {
    "volume": 1.0,
    "length_scale": 1.4,
    "noise_scale": 0.7,
    "noise_w_scale": 0.7,
    "normalize_audio": True
}

try:
    from piper import PiperVoice, SynthesisConfig  # from your piper_test.py pattern
    _HAS_PIPER = True
except Exception as e:
    print("Piper import failed (piper-tts not installed?):", e)
    _HAS_PIPER = False

# -------------------- Configuration (edit or set env vars) --------------------
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))

# Audio settings — client and server must match these for recording
SAMPLE_RATE = int(os.environ.get("SAMPLE_RATE", 16000))
CHANNELS = int(os.environ.get("CHANNELS", 1))

TOP_K = int(os.environ.get("TOP_K", 5))
EMBED_MODEL_NAME = os.environ.get("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
WHISPER_MODEL_NAME = os.environ.get("WHISPER_MODEL_NAME", "small")  # choose 'tiny', 'base', 'small' as needed

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:1b")
TRANSFORMER_MODEL = os.environ.get("TRANSFORMER_MODEL", "bigscience/bloom")

# Data paths (set these or use env vars)
FAISS_INDEX_PATH = os.environ.get("FAISS_INDEX_PATH", r"C:\Users\Raghuram S\OneDrive\Desktop\gitaGPT\gita_faiss.index")
DF_PATH = os.environ.get("DF_PATH", r"C:\Users\Raghuram S\OneDrive\Desktop\gitaGPT\bhagavad_gita_verses.csv")

# ------------------------------------------------------------------------------

app = Flask(__name__)

# Global model handles
whisper_model = None
embedder = None
faiss_index = None
texts = None
df = None

# ------------------ Utilities ------------------
def load_dataframe(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataframe file not found: {path}")
    if path.endswith(".csv"):
        return pd.read_csv(path)
    else:
        return pd.read_pickle(path)

def build_faiss_index(texts_list, embedder_local, dim, index_path=None):
    embeddings = embedder_local.encode(texts_list, show_progress_bar=True, convert_to_numpy=True)
    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    if index_path:
        faiss.write_index(index, index_path)
    return index, embeddings

def load_or_build_index(df_local, text_col='text', embed_model=EMBED_MODEL_NAME, index_path=None, dim=384):
    global embedder
    embedder_local = SentenceTransformer(embed_model)
    embedder = embedder_local
    texts_local = df_local[text_col].astype(str).tolist()
    if index_path and os.path.exists(index_path):
        index_local = faiss.read_index(index_path)
        return index_local, texts_local
    index_local, _ = build_faiss_index(texts_local, embedder_local, dim, index_path=index_path)
    return index_local, texts_local

def retrieve(query, index, texts_list, embedder_local, top_k=TOP_K):
    if not query or not query.strip():
        return []
    q_emb = embedder_local.encode([query], convert_to_numpy=True)
    faiss.normalize_L2(q_emb)
    distances, indices = index.search(q_emb, top_k)
    results = []
    for idx, score in zip(indices[0], distances[0]):
        if 0 <= idx < len(texts_list):
            results.append((int(idx), float(score), texts_list[int(idx)]))
    return results

def make_prompt(query, retrieved, max_context_chars=2000):
    context_parts = []
    total_len = 0
    for idx, score, txt in retrieved:
        entry = f"(id={idx}, score={score:.4f})\n{txt.strip()}\n---\n"
        total_len += len(entry)
        if total_len > max_context_chars:
            break
        context_parts.append(entry)
    context = "\n".join(context_parts)
    instruction = (
        """You are an assistant who answers *with reference to the Bhagavad Gita*.

GUIDELINES:
1. Use only the verses provided in the CONTEXT.
   - Treat CONTEXT as the sole knowledge source for Gita references.
   - Do not invent or recall verses outside the given IDs.

2. Citations:
   - When basing any part of your answer on a verse, include an inline citation in this exact format: (id=XYZ).
   - If summarizing multiple verses, cite each relevant id, it would be preferable to give chapter number and verse number as well in the beginning before referencing that to the answer to solution.

3. Quoting:
   - Keep direct quotes short (a phrase or line).
   - Prefer paraphrasing + explanation over long copy-pastes.

4. Style of Answer:
   - Provide clear, decently detailed explanations in under 120 words.
   - Show how the verse connects to the user’s question (very very important).
   - Encourage and guide the user in understanding, without being preachy. 

5. Boundaries:
   - Do not fabricate chapter/verse numbers.
   - Do not rely on outside knowledge — only use the given CONTEXT."""
    )
    return f"{instruction}\n\nCONTEXT:\n{context}\nUSER QUERY:\n{query}\n\nAnswer:"

# ------------------ Generation (Ollama / Transformers fallback) ------------------
def generate_with_ollama(prompt, model=OLLAMA_MODEL):
    system_msg = {"role": "system", "content": "You are an assistant that must answer using only the provided verses and cite them by id."}
    user_msg = {"role": "user", "content": prompt}
    resp = ollama.chat(model=model, messages=[system_msg, user_msg])
    return resp['message']['content']

def generate_with_transformers(prompt, model_name=TRANSFORMER_MODEL, max_new_tokens=200):
    # Lazy import to avoid heavy startup when Ollama is used
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    text_gen = pipeline("text-generation", model=model, tokenizer=tokenizer)
    out = text_gen(prompt, max_new_tokens=max_new_tokens, do_sample=True, top_p=0.95, temperature=0.7)
    return out[0]['generated_text']

def safe_generate(prompt):
    """Try Ollama first; if it fails, fallback to transformers and return a string."""
    if _HAS_OLLAMA:
        try:
            return generate_with_ollama(prompt)
        except Exception:
            print("Warning: Ollama generation failed, falling back to transformers.")
            traceback.print_exc()
    try:
        print("Using transformers fallback to generate response.")
        return generate_with_transformers(prompt)
    except Exception:
        traceback.print_exc()
        return "I'm sorry — the language model is currently unavailable."

# ------------------ Response cleaning ------------------
def clean_response_text(text: str) -> str:
    """
    Strip citation/index tokens from model output so the final response
    is natural-sounding speech without things like [id=123] or (id=123, score=0.9).
    """
    if not text:
        return text

    cleaned = text

    # remove patterns like [id=123]
    cleaned = re.sub(r"\[id=\s*\d+\s*\]", " ", cleaned)

    # remove patterns like (id=123) or (id=123, score=0.9234)
    cleaned = re.sub(r"\(id=\s*\d+(?:\s*,\s*score\s*=\s*[-+]?\d*\.?\d+)?\s*\)", " ", cleaned, flags=re.IGNORECASE)

    # remove standalone id=123 occurrences
    cleaned = re.sub(r"\bid\s*=\s*\d+\b", " ", cleaned)

    # remove stray brackets or parentheses left empty
    cleaned = re.sub(r"\[\s*\]", " ", cleaned)
    cleaned = re.sub(r"\(\s*\)", " ", cleaned)
    # swap asterisk with space
    cleaned = cleaned.replace(r"*", " ")

    # collapse multiple newlines to max two
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # collapse multiple spaces
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)

    # strip leading/trailing whitespace
    cleaned = cleaned.strip()

    # if the model accidentally included the context block, remove a repeated "CONTEXT:" section
    cleaned = re.sub(r"CONTEXT:.*USER QUERY:.*Answer:", "", cleaned, flags=re.DOTALL | re.IGNORECASE).strip()

    return cleaned

# ------------------ PIPER helpers and TTS ------------------
def _piper_init_once(use_cuda=False):
    """
    Initialize Piper voice if available. Safe to call repeatedly.
    Returns True if piper voice is loaded.
    """
    global _piper_voice, _HAS_PIPER, PIPER_VOICE_PATH
    if not _HAS_PIPER:
        return False
    if _piper_voice is not None:
        return True
    if not os.path.exists(PIPER_VOICE_PATH):
        print(f"Piper voice file not found at path: {PIPER_VOICE_PATH}")
        return False
    try:
        print("Loading Piper voice:", PIPER_VOICE_PATH)
        # PiperVoice.load(path, use_cuda=...)
        _piper_voice = PiperVoice.load(PIPER_VOICE_PATH, use_cuda=use_cuda)
        print("Loaded Piper voice. sample_rate:", getattr(_piper_voice, "sample_rate", "unknown"),
              "channels:", getattr(_piper_voice, "sample_channels", "unknown"),
              "sample_width:", getattr(_piper_voice, "sample_width", "unknown"))
        return True
    except Exception:
        traceback.print_exc()
        _piper_voice = None
        return False

def _piper_synthesize_to_wav_bytes(text, syn_cfg=None):
    """
    Use the loaded piper voice to synthesize text to WAV bytes (PCM16).
    Returns bytes or None on failure.
    """
    global _piper_voice
    if _piper_voice is None:
        raise RuntimeError("Piper voice not initialized")
    # Compose a SynthesisConfig if SynthesisConfig is available
    cfg_obj = None
    try:
        if syn_cfg is not None and 'SynthesisConfig' in globals():
            # if syn_cfg is a dict convert to SynthesisConfig
            if isinstance(syn_cfg, dict):
                cfg_obj = SynthesisConfig(**syn_cfg)
            elif isinstance(syn_cfg, SynthesisConfig):
                cfg_obj = syn_cfg
    except Exception:
        cfg_obj = None

    buf = io.BytesIO()
    # Piper expects a wave.Wave_write object for synthesize_wav
    with wave.open(buf, "wb") as wav_file:
        sample_rate = getattr(_piper_voice, "sample_rate", 24000)
        sample_width = getattr(_piper_voice, "sample_width", 2)
        channels = getattr(_piper_voice, "sample_channels", 1)
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        if cfg_obj is not None:
            _piper_voice.synthesize_wav(text, wav_file, syn_config=cfg_obj)
        else:
            # attempt to create SynthesisConfig from defaults if possible
            try:
                cfg = SynthesisConfig(**_PIPER_SYN_CFG)
                _piper_voice.synthesize_wav(text, wav_file, syn_config=cfg)
            except Exception:
                _piper_voice.synthesize_wav(text, wav_file)
    wav_bytes = buf.getvalue()
    return wav_bytes

def _to_wav_bytes_from_samples(samples, sample_rate):
    """Given numpy samples (1D or 2D) and rate, write WAV bytes and return."""
    try:
        import soundfile as sf
        # many TTS libs return float32 - convert to int16 for standard wav
        samples_np = np.asarray(samples)
        if samples_np.dtype.kind == "f":
            scaled = np.clip(samples_np, -1.0, 1.0)
            int_samples = (scaled * 32767).astype(np.int16)
        else:
            int_samples = samples_np.astype(np.int16)
        with io.BytesIO() as b:
            sf.write(b, int_samples, sample_rate, format="WAV", subtype="PCM_16")
            return b.getvalue()
    except Exception:
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpf:
                tmpname = tmpf.name
            wav_write(tmpname, sample_rate, samples)
            with open(tmpname, "rb") as fh:
                data = fh.read()
            try:
                os.remove(tmpname)
            except Exception:
                pass
            return data
        except Exception:
            traceback.print_exc()
            return None

def generate_tts_audio(text, preferred="piper"):
    """
    Attempts to produce WAV bytes for the given text.
    preferred: "piper" or "pyttsx3" to prefer specific backend first.
    Returns bytes (WAV data) or None.
    """
    # 1) Piper attempt (best quality if available)
    if preferred == "piper" and _HAS_PIPER:
        try:
            if not _piper_init_once():
                raise RuntimeError("piper init failed or voice not found")
            wav_bytes = _piper_synthesize_to_wav_bytes(text, syn_cfg=_PIPER_SYN_CFG)
            if wav_bytes:
                return wav_bytes
        except Exception as e:
            print("Piper TTS failed or not available:", e)
            traceback.print_exc()

    # 2) pyttsx3 fallback (pure-python, cross-platform but voices vary)
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpf:
            tmpname = tmpf.name
        engine.save_to_file(text, tmpname)
        engine.runAndWait()
        # small sleep to ensure file flushed
        time.sleep(0.15)
        with open(tmpname, "rb") as fh:
            data = fh.read()
        try:
            os.remove(tmpname)
        except Exception:
            pass
        return data
    except Exception as e:
        print("pyttsx3 TTS failed:", e)
        traceback.print_exc()

    # 3) On Windows, try COM SAPI if pyttsx3 failed (best-effort)
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpf:
            tmpname = tmpf.name
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        from comtypes import CLSCTX_ALL
        stream.Open(tmpname, 3, False)
        speaker.AudioOutputStream = stream
        speaker.Speak(text)
        stream.Close()
        with open(tmpname, "rb") as fh:
            data = fh.read()
        try:
            os.remove(tmpname)
        except Exception:
            pass
        return data
    except Exception:
        traceback.print_exc()
        return None

# ------------------ HTTP endpoints ------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "models_loaded": whisper_model is not None}), 200

@app.route("/process_audio", methods=["POST"])
def process_audio():
    global whisper_model, embedder, faiss_index, texts, df
    try:
        if whisper_model is None:
            return jsonify({"error": "Models not loaded on server."}), 503

        audio_bytes = request.data
        if not audio_bytes:
            return jsonify({"error": "No audio data received"}), 400

        print(f"Received {len(audio_bytes)} bytes of audio data.")

        # Convert bytes -> int16 numpy -> float32 in [-1,1]
        try:
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        except Exception as e:
            return jsonify({"error": f"Failed to parse int16 audio bytes: {e}"}), 400

        if CHANNELS > 1 and audio_int16.size % CHANNELS == 0:
            audio_int16 = audio_int16.reshape(-1, CHANNELS)[:, 0]

        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        # Try direct numpy transcription first (avoids ffmpeg)
        try:
            print("Attempting direct transcription from numpy array...")
            result = whisper_model.transcribe(audio_float32, fp16=False)
        except Exception as e_direct:
            print("Direct transcription failed:", e_direct)
            print("Falling back to WAV-file transcription (may require ffmpeg on PATH).")
            tmp_wav = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpf:
                    tmp_wav = tmpf.name
                    wav_write(tmp_wav, SAMPLE_RATE, audio_int16)
                result = whisper_model.transcribe(tmp_wav, fp16=False)
            except Exception as e_file:
                msg = (
                    "Transcription failed. If this mentions ffmpeg or WinError 2, "
                    "please install ffmpeg and ensure it is on PATH. "
                    f"Direct error: {e_direct}; file error: {e_file}"
                )
                print(msg)
                traceback.print_exc()
                return jsonify({"error": msg}), 500
            finally:
                if tmp_wav and os.path.exists(tmp_wav):
                    try:
                        os.remove(tmp_wav)
                    except Exception:
                        pass

        transcribed_text = result.get("text", "").strip()
        print("Transcription:", transcribed_text)

        # Retrieve similar verses - use 'translation' column for verse text
        text_col_candidates = [c for c in df.columns if df[c].dtype == object or df[c].dtype == "string"]
        text_col = 'translation' if 'translation' in df.columns else (
            text_col_candidates[0] if text_col_candidates else df.columns[0]
        )
        retrieved = retrieve(transcribed_text, faiss_index, texts, embedder, top_k=TOP_K)

        # LLM prompt and generation
        prompt = make_prompt(transcribed_text, retrieved)

        # generate raw response (may include citation tokens)
        response_text_raw = safe_generate(prompt)
        # create a cleaned natural-speech version without ids for TTS/response
        response_text = clean_response_text(response_text_raw)

        # formatted small summary (view-friendly) — keep retrieval ids here for traceability
        formatted_response = "=== AI Response ===\n" + response_text.strip() + "\n\n"
        if retrieved:
            formatted_response += "=== Top Source Verse(s) ===\n"
            for idx, score, txt in retrieved[:TOP_K]:
                formatted_response += f"\n(id={idx}, score={score:.4f})\n{txt}\n---\n"
        else:
            formatted_response += "(No verses retrieved.)\n"

        # TTS (try piper first, fallback to pyttsx3/others) - use cleaned response_text for TTS
        tts_bytes = None
        try:
            tts_bytes = generate_tts_audio(response_text, preferred="piper")
            if tts_bytes:
                print("TTS audio generated (bytes length):", len(tts_bytes))
            else:
                print("No TTS bytes returned (all TTS backends failed).")
        except Exception as e:
            print("TTS generation error:", e)
            traceback.print_exc()
            tts_bytes = None

        return jsonify({
            "transcription": transcribed_text,
            # return the cleaned natural-speech response (no index ids)
            "response": response_text,
            "formatted_response": formatted_response,
            "audio": tts_bytes.hex() if tts_bytes else None,
            # also include the raw LM output if you want to debug
            "response_raw": response_text_raw
        }), 200

    except Exception as e:
        print("Unhandled server error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ------------------ Initialization ------------------
def initialize_models():
    global whisper_model, embedder, faiss_index, texts, df
    print("Loading Whisper model (this may take a while)...")
    whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
    print("Loading dataframe from:", DF_PATH)
    df = load_dataframe(DF_PATH)
    
    # Use 'translation' column for verse text if available, otherwise find text columns
    if 'translation' in df.columns:
        text_col = 'translation'
        print("Using 'translation' column for verse text")
    else:
        text_col_candidates = [c for c in df.columns if df[c].dtype == object or df[c].dtype == "string"]
        text_col = text_col_candidates[0] if text_col_candidates else df.columns[0]
        print(f"Using '{text_col}' column for verse text")
    
    print("Loading/building FAISS index (this may take a while)...")
    faiss_idx, texts_list = load_or_build_index(df, text_col=text_col, index_path=FAISS_INDEX_PATH)
    # set globals
    global faiss_index
    faiss_index = faiss_idx
    texts = texts_list
    print("Models initialized.")
    # try to initialize piper voice early (optional)
    if _HAS_PIPER:
        print("Attempting to initialize Piper voice (optional)...")
        try:
            ok = _piper_init_once()
            if not ok:
                print("Piper voice not initialized (check PIPER_VOICE_PATH).")
            else:
                print("Piper voice initialized.")
        except Exception:
            traceback.print_exc()

if __name__ == "__main__":
    print("Before using Ollama: ensure you pulled/installed models and started the Ollama daemon if you plan to use Ollama.")
    print("Examples:\n  ollama pull gemma3:1b\n  ollama serve\n  (Set OLLAMA_HOST=0.0.0.0:11434 before serving to accept remote requests)\n")
    initialize_models()
    app.run(host=HOST, port=PORT, debug=False)
