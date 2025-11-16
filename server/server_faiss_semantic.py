#!/usr/bin/env python3
"""
GitaGPT Server with FAISS Semantic Search
Combines semantic understanding with FAISS vector search across all 700+ Gita verses
"""

import os
import io
import wave
import time
import json
import random
import traceback
import numpy as np
import pandas as pd
import whisper
from flask import Flask, request, jsonify

# Try to import required libraries
try:
    import faiss
    HAS_FAISS = True
    print("✅ FAISS available")
except ImportError:
    HAS_FAISS = False
    print("⚠️  FAISS not available")

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
    print("✅ SentenceTransformers available")
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    print("⚠️  SentenceTransformers not available")

try:
    from piper import PiperVoice
    HAS_PIPER = True
    print("✅ Piper TTS available")
except ImportError:
    HAS_PIPER = False
    print("⚠️  Piper TTS not available")

# Configuration
HOST = "0.0.0.0"
PORT = 5000
SAMPLE_RATE = 16000
CHANNELS = 1

# File paths
GITA_CSV_PATH = r"C:\Users\Raghuram S\OneDrive\Desktop\gitaGPT\bhagavad_gita_verses.csv"
FAISS_INDEX_PATH = r"C:\Users\Raghuram S\OneDrive\Desktop\gitaGPT\gita_faiss.index"
PIPER_VOICE_PATH = r"C:\Users\Raghuram S\OneDrive\Desktop\gitaGPT\en_GB-southern_english_female-low.onnx"

# Conversation control
EXIT_PHRASES = ["thank you", "thanks", "that's all", "nothing else", "goodbye"]
FOLLOW_UP_PHRASES = [
    "Is there anything else I can help you with?",
    "Would you like to explore this teaching further?", 
    "Any other spiritual questions?",
    "Would you like more guidance on this topic?"
]

# Global variables
app = Flask(__name__)
whisper_model = None
piper_voice = None
gita_data = None
faiss_index = None
sentence_model = None

def load_models():
    """Load all required models"""
    global whisper_model, piper_voice, gita_data, faiss_index, sentence_model
    
    print("🔄 Loading models...")
    
    # Load Whisper
    try:
        print("Loading Whisper model...")
        whisper_model = whisper.load_model("small")
        print("✅ Whisper loaded")
    except Exception as e:
        print(f"❌ Whisper loading failed: {e}")
        whisper_model = None
    
    # Load Gita data
    try:
        print("Loading Bhagavad Gita verses...")
        if os.path.exists(GITA_CSV_PATH):
            gita_data = pd.read_csv(GITA_CSV_PATH)
            print(f"✅ Loaded {len(gita_data)} verses from CSV")
            # Display first few verses for verification
            if 'translation' in gita_data.columns:
                print(f"📖 Sample verse: {gita_data['translation'].iloc[0][:100]}...")
            else:
                print(f"📖 Available columns: {gita_data.columns.tolist()}")
        else:
            print(f"❌ Gita CSV not found at {GITA_CSV_PATH}")
            gita_data = None
    except Exception as e:
        print(f"❌ Error loading Gita data: {e}")
        gita_data = None
    
    # Load SentenceTransformer for embeddings
    if HAS_SENTENCE_TRANSFORMERS:
        try:
            print("Loading SentenceTransformer model...")
            sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ SentenceTransformer loaded")
        except Exception as e:
            print(f"❌ SentenceTransformer loading failed: {e}")
            sentence_model = None
    
    # Load or create FAISS index
    if HAS_FAISS and sentence_model and gita_data is not None:
        try:
            if os.path.exists(FAISS_INDEX_PATH):
                print(f"Loading existing FAISS index from {FAISS_INDEX_PATH}")
                faiss_index = faiss.read_index(FAISS_INDEX_PATH)
                print(f"✅ FAISS index loaded with {faiss_index.ntotal} vectors")
            else:
                print("Creating new FAISS index...")
                faiss_index = create_faiss_index()
                if faiss_index:
                    print(f"✅ FAISS index created with {faiss_index.ntotal} vectors")
        except Exception as e:
            print(f"❌ FAISS index loading/creation failed: {e}")
            faiss_index = None
    else:
        print("⚠️  FAISS index not available (missing dependencies)")
        faiss_index = None
    
    # Load Piper TTS
    if HAS_PIPER:
        try:
            print("Loading Piper TTS voice...")
            if os.path.exists(PIPER_VOICE_PATH):
                piper_voice = PiperVoice.load(PIPER_VOICE_PATH)
                print("✅ Piper TTS loaded successfully!")
            else:
                print(f"❌ Piper voice file not found: {PIPER_VOICE_PATH}")
                piper_voice = None
        except Exception as e:
            print(f"❌ Piper loading failed: {e}")
            piper_voice = None
    else:
        piper_voice = None
    
    print(f"🎯 Final status:")
    print(f"   Whisper: {whisper_model is not None}")
    print(f"   Gita verses: {len(gita_data) if gita_data is not None else 0}")
    print(f"   FAISS index: {faiss_index.ntotal if faiss_index else 0} vectors")
    print(f"   TTS: {piper_voice is not None}")

def create_faiss_index():
    """Create FAISS index from Gita verses"""
    global gita_data, sentence_model
    
    if not sentence_model or gita_data is None:
        print("❌ Cannot create FAISS index - missing dependencies")
        return None
    
    try:
        # Get verse texts
        if 'translation' in gita_data.columns:
            verses = gita_data['translation'].astype(str).tolist()
        else:
            verses = gita_data.iloc[:, -1].astype(str).tolist()
        
        print(f"🔍 Creating embeddings for {len(verses)} verses...")
        
        # Create embeddings
        embeddings = sentence_model.encode(verses, show_progress_bar=True)
        embeddings = embeddings.astype('float32')
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        
        # Save index
        faiss.write_index(index, FAISS_INDEX_PATH)
        print(f"💾 FAISS index saved to {FAISS_INDEX_PATH}")
        
        return index
        
    except Exception as e:
        print(f"❌ Error creating FAISS index: {e}")
        import traceback
        traceback.print_exc()
        return None

def find_relevant_verses(query, top_k=3):
    """Find most relevant verses using FAISS semantic search"""
    global faiss_index, sentence_model, gita_data
    
    if not all([faiss_index, sentence_model, gita_data is not None]):
        print("⚠️  FAISS search not available, using fallback")
        return get_fallback_verses(query)
    
    try:
        print(f"🔍 Searching for: '{query}' (top {top_k} results)")
        
        # Create query embedding
        query_embedding = sentence_model.encode([query]).astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Search FAISS index
        similarities, indices = faiss_index.search(query_embedding, top_k)
        
        results = []
        verse_column = 'translation' if 'translation' in gita_data.columns else gita_data.columns[-1]
        
        for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
            if idx < len(gita_data):
                verse_data = gita_data.iloc[idx]
                verse_text = str(verse_data[verse_column])
                
                # Get chapter and verse info if available
                chapter_info = ""
                if 'chapter_number' in gita_data.columns and 'chapter_verse' in gita_data.columns:
                    chapter_info = f" ({verse_data['chapter_number']}, {verse_data['chapter_verse']})"
                
                result = {
                    'verse': verse_text,
                    'similarity': float(similarity),
                    'chapter_info': chapter_info,
                    'rank': i + 1
                }
                results.append(result)
                
                print(f"📖 Result #{i+1} (similarity: {similarity:.3f}){chapter_info}: {verse_text[:100]}...")
        
        return results
        
    except Exception as e:
        print(f"❌ FAISS search error: {e}")
        return get_fallback_verses(query)

def get_fallback_verses(query):
    """Fallback verse selection when FAISS is not available"""
    fallback_verses = [
        "You have the right to perform your actions, but you are not entitled to the fruits of your actions. Never let the fruits of action be your motive, nor let your attachment be to inaction.",
        "For the soul there is neither birth nor death. It is not slain when the body is slain. The soul is unborn, eternal, permanent, and primeval.",
        "Better is your own dharma, though imperfectly performed, than the dharma of another well performed. Better is death in the performance of one's own dharma; the dharma of another is fraught with danger.",
        "When meditation is mastered, the mind is unwavering like the flame of a lamp in a windless place.",
        "Whatever you do, whatever you eat, whatever you offer in sacrifice, whatever you give away, whatever austerities you practice - do that as an offering to the Divine."
    ]
    
    return [{'verse': random.choice(fallback_verses), 'similarity': 0.5, 'chapter_info': '', 'rank': 1}]

def understand_question_intent(query):
    """Enhanced semantic understanding of user's question"""
    query_lower = query.lower()
    
    intents = {
        'tiredness_laziness': ['lazy', 'tired', 'fatigue', 'exhausted', 'unmotivated', 'lethargy', 'energy', 'motivation', 'procrastination', 'weakness'],
        'sadness_depression': ['sad', 'sadness', 'depressed', 'depression', 'sorrow', 'grief', 'unhappy', 'melancholy', 'down', 'blue', 'hopeless'],
        'fear_anxiety': ['fear', 'afraid', 'scared', 'anxiety', 'anxious', 'worry', 'worried', 'panic', 'nervous', 'frightened', 'terror'],
        'life_purpose': ['purpose', 'meaning', 'direction', 'path', 'calling', 'destiny', 'goal', 'mission', 'dharma', 'why am i here', 'what should i do'],
        'anger_conflict': ['angry', 'anger', 'mad', 'furious', 'conflict', 'fight', 'argument', 'frustrated', 'rage', 'hate', 'resentment'],
        'attachment_loss': ['attachment', 'loss', 'lost', 'letting go', 'detachment', 'possession', 'clinging', 'breakup', 'death', 'separation'],
        'doubt_confusion': ['doubt', 'confused', 'confusion', 'uncertain', 'unsure', 'lost', 'decision', 'choice', 'dilemma'],
        'spiritual_practice': ['meditation', 'prayer', 'devotion', 'worship', 'spiritual', 'enlightenment', 'moksha', 'liberation'],
        'relationships': ['relationship', 'love', 'family', 'friends', 'marriage', 'parents', 'children', 'society'],
        'work_duty': ['work', 'job', 'career', 'duty', 'responsibility', 'service', 'profession', 'business']
    }
    
    detected_intents = []
    for intent, keywords in intents.items():
        if any(keyword in query_lower for keyword in keywords):
            detected_intents.append(intent)
    
    primary_intent = detected_intents[0] if detected_intents else 'general'
    print(f"🧠 Detected intent: {primary_intent} (from: {detected_intents})")
    
    return primary_intent, detected_intents

def generate_contextual_response(query, verse_results, intent):
    """Generate contextual response based on query, verses, and intent"""
    
    if not verse_results:
        return "The Bhagavad Gita teaches us that all suffering comes from ignorance of our true nature. Seek wisdom through righteous action, devotion, and self-knowledge."
    
    # Get the most relevant verse
    best_verse = verse_results[0]
    verse_text = best_verse['verse']
    chapter_info = best_verse['chapter_info']
    
    # Intent-based contextual responses
    intent_context = {
        'tiredness_laziness': "Krishna teaches that laziness comes from attachment to results and fear of failure. The solution is not inaction, but action without attachment.",
        'sadness_depression': "The Gita reminds us that our true nature is the eternal soul, beyond all temporary sorrows. This wisdom brings lasting peace.",
        'fear_anxiety': "Fear arises from the illusion of separateness. When you realize your connection to the Divine, fear naturally dissolves.",
        'life_purpose': "Your dharma (life purpose) is unique to your nature and circumstances. The Gita guides you to discover and follow your authentic path.",
        'anger_conflict': "Anger clouds judgment and leads to poor decisions. The Gita teaches emotional mastery through spiritual understanding.",
        'attachment_loss': "Attachment to temporary things causes suffering. True joy comes from loving without possessing and giving without expecting.",
        'doubt_confusion': "When confused, seek wisdom from sacred texts and wise teachers. The Divine guides those who sincerely seek truth.",
        'spiritual_practice': "Regular spiritual practice purifies the mind and reveals your true nature. Consistency is more important than intensity.",
        'relationships': "See the Divine in all beings. Love unconditionally, serve selflessly, and maintain your inner peace regardless of others' actions.",
        'work_duty': "Perform your work as worship. Excellence in action, without attachment to results, leads to both success and spiritual growth."
    }
    
    context = intent_context.get(intent, "The eternal wisdom of the Gita provides guidance for all of life's challenges.")
    
    # Create comprehensive response
    response = f"""🙏 **Krishna's Guidance:**

**Verse{chapter_info}:** "{verse_text[:300]}{'...' if len(verse_text) > 300 else ''}"

**Understanding:** {context}

**Practical Application:** Focus on your sincere effort rather than worrying about outcomes. Every step taken with devotion and wisdom brings you closer to peace and fulfillment."""
    
    # Add additional verses if very relevant
    if len(verse_results) > 1 and verse_results[1]['similarity'] > 0.7:
        additional_verse = verse_results[1]['verse'][:200]
        response += f"\n\n**Related Teaching:** \"{additional_verse}...\""
    
    print(f"✅ Generated contextual response for intent: {intent}")
    return response

def synthesize_speech(text):
    """Convert text to speech using Piper"""
    global piper_voice
    
    if not piper_voice:
        print("⚠️  Piper TTS not available")
        return None
    
    try:
        # Clean text for TTS
        clean_text = text.replace("**", "").replace("🙏", "").replace("*", "")
        clean_text = clean_text.replace("📖", "").replace("✅", "").strip()
        
        # Limit length for TTS
        if len(clean_text) > 1000:
            clean_text = clean_text[:1000] + "..."
        
        print(f"🎵 Generating TTS for {len(clean_text)} characters")
        
        # Create in-memory WAV
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            piper_voice.synthesize_wav(clean_text, wav_file)
        
        wav_data = wav_buffer.getvalue()
        print(f"✅ TTS generated: {len(wav_data)} bytes")
        return wav_data
        
    except Exception as e:
        print(f"❌ TTS synthesis error: {e}")
        return None

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'whisper': whisper_model is not None,
        'gita_verses': len(gita_data) if gita_data is not None else 0,
        'faiss_vectors': faiss_index.ntotal if faiss_index else 0,
        'sentence_model': sentence_model is not None,
        'tts': piper_voice is not None,
        'approach': 'faiss_semantic_search'
    })

@app.route('/process_audio', methods=['POST'])
def process_audio():
    """Process audio and return FAISS-based Gita response"""
    try:
        # Get audio data
        audio_data = request.get_data()
        if not audio_data:
            return jsonify({'error': 'No audio data'}), 400
        
        print(f"📡 Received {len(audio_data)} bytes")
        
        # Convert audio to numpy
        if len(audio_data) % 2 != 0:
            audio_data = audio_data[:-1]
        
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        audio_float = audio_np.astype(np.float32) / 32768.0
        
        # Transcribe
        print("🎤 Transcribing...")
        result = whisper_model.transcribe(audio_float)
        transcription = result['text'].strip()
        print(f"📝 Transcribed: '{transcription}'")
        
        # Check for exit
        end_conversation = any(phrase in transcription.lower() for phrase in EXIT_PHRASES)
        
        if end_conversation:
            response_text = "🙏 Thank you for seeking Gita wisdom. May you find peace and fulfillment on your spiritual journey. Om Shanti!"
        else:
            # Understand question intent
            primary_intent, all_intents = understand_question_intent(transcription)
            
            # Find relevant verses using FAISS
            verse_results = find_relevant_verses(transcription, top_k=3)
            
            # Generate contextual response
            response_text = generate_contextual_response(transcription, verse_results, primary_intent)
            response_text += f"\n\n{random.choice(FOLLOW_UP_PHRASES)}"
        
        # Generate speech
        print("🔊 Generating TTS audio...")
        audio_bytes = synthesize_speech(response_text)
        audio_hex = audio_bytes.hex() if audio_bytes else None
        
        return jsonify({
            'transcription': transcription,
            'response': response_text,
            'audio': audio_hex,
            'end_conversation': end_conversation,
            'intent': primary_intent if not end_conversation else 'goodbye',
            'verse_count': len(verse_results) if not end_conversation else 0
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/greet', methods=['GET'])
def greet():
    """Simple greeting endpoint"""
    try:
        greeting_text = "Om Namah Shivaya"
        print(f"🙏 Generating greeting: {greeting_text}")
        
        audio_bytes = synthesize_speech(greeting_text)
        audio_hex = audio_bytes.hex() if audio_bytes else None
        
        return jsonify({
            'message': greeting_text,
            'audio': audio_hex
        })
        
    except Exception as e:
        print(f"❌ Greeting error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting GitaGPT FAISS Semantic Server...")
    print("🔍 Using FAISS vector search across all Gita verses")
    print("🧠 With semantic understanding of user intent")
    
    # Load models
    load_models()
    
    print(f"🌐 Server ready on {HOST}:{PORT}")
    if faiss_index:
        print(f"📚 Ready to search through {faiss_index.ntotal} verse embeddings")
    else:
        print("⚠️  Running with fallback verse selection")
    
    app.run(host=HOST, port=PORT, debug=False)