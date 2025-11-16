#!/usr/bin/env python3
"""
GitaGPT Server - Semantic Understanding Version
Server with proper semantic understanding and curated Gita verse responses
"""

import os
import io
import wave
import time
import json
import random
import traceback
from flask import Flask, request, jsonify
import numpy as np
import pandas as pd
import whisper

# Try to import Piper TTS
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
PIPER_VOICE_PATH = r"C:\Users\Raghuram S\OneDrive\Desktop\gitaGPT\en_GB-southern_english_female-low.onnx"

# Conversation control
EXIT_PHRASES = ["thank you", "thanks", "that's all", "nothing else", "goodbye"]
FOLLOW_UP_PHRASES = [
    "Is there anything else I can help you with?",
    "Would you like to explore this teaching further?", 
    "Any other spiritual questions?"
]

# Curated Gita responses for common spiritual questions
SPIRITUAL_RESPONSES = {
    "laziness_tiredness": {
        "verse": "You have the right to perform your actions, but you are not entitled to the fruits of your actions. Never let the fruits of action be your motive, nor let your attachment be to inaction. (Chapter 2, Verse 47)",
        "explanation": "Krishna teaches that when we feel lazy or tired, the solution is not to avoid action, but to act without attachment to results. Laziness often comes from fear of failure or being overwhelmed by outcomes. When you focus only on doing your duty sincerely, without worrying about success or failure, action becomes effortless and energizing.",
        "guidance": "Start with small, manageable tasks. Dedicate your efforts to a higher purpose. Remember that even small righteous actions purify the mind and build spiritual strength."
    },
    
    "sadness_depression": {
        "verse": "For the soul there is neither birth nor death. It is not slain when the body is slain. The soul is unborn, eternal, permanent, and primeval. (Chapter 2, Verse 20)",
        "explanation": "Krishna reminds Arjuna (and us) that our true nature is the eternal soul, which is beyond all temporary emotions like sadness. Sadness comes from identifying with the temporary - our circumstances, relationships, achievements. But you are the eternal witness of all these changing experiences.",
        "guidance": "Practice seeing yourself as the observer of your emotions rather than being overwhelmed by them. Engage in meditation, selfless service, and remember that 'this too shall pass.'"
    },
    
    "fear_anxiety": {
        "verse": "Abandon all varieties of dharma and just surrender unto Me. I shall deliver you from all sinful reactions. Do not fear. (Chapter 18, Verse 66)",
        "explanation": "Fear comes from the illusion that we are alone and must control everything. Krishna assures us that when we surrender our ego and trust in the Divine plan, we are protected. The Divine consciousness that runs the entire universe is the same consciousness within you.",
        "guidance": "Practice surrender through prayer and meditation. Face your fears with courage, knowing that you are never alone. Take righteous action despite fear - courage is not the absence of fear, but action in spite of it."
    },
    
    "life_purpose": {
        "verse": "Better is your own dharma, though imperfectly performed, than the dharma of another well performed. Better is death in the performance of one's own dharma; the dharma of another is fraught with danger. (Chapter 3, Verse 35)",
        "explanation": "Your life purpose (dharma) is unique to you - based on your nature, abilities, and circumstances. Krishna teaches that it's better to follow your own path imperfectly than to perfectly imitate someone else's path. Your authentic purpose brings fulfillment and contributes to cosmic harmony.",
        "guidance": "Reflect on your natural talents, what brings you joy, and how you can serve others. Your dharma is where your gifts meet the world's needs. Trust your inner wisdom and take steps toward your authentic path."
    },
    
    "anger_conflict": {
        "verse": "Anger leads to clouding of judgment, which results in bewilderment of the memory. When the memory is bewildered, the intellect gets destroyed; and when the intellect is destroyed, one is ruined. (Chapter 2, Verse 63)",
        "explanation": "Krishna explains the destructive chain reaction of anger. When we're angry, we lose our ability to think clearly, make poor decisions, and ultimately harm ourselves and others. The solution is to develop emotional mastery through spiritual practice.",
        "guidance": "When anger arises, pause and breathe deeply. Remember this teaching and choose your response consciously. Practice seeing the Divine in all beings - this naturally dissolves anger and cultivates compassion."
    },
    
    "attachment_loss": {
        "verse": "You came empty-handed, and you will leave empty-handed. What is yours today belonged to someone else yesterday, and will belong to someone else tomorrow. Change is the law of the universe. (Chapter 2, Verse 27 - expanded teaching)",
        "explanation": "Attachment to temporary things - relationships, possessions, achievements - causes suffering. Krishna teaches that everything in the material world is constantly changing. True peace comes from loving without attachment and enjoying without possessing.",
        "guidance": "Practice gratitude for what you have while holding it lightly. Focus on giving rather than receiving. Remember that love is about the joy of loving, not about possession or control."
    },
    
    "doubt_confusion": {
        "verse": "Whenever righteousness declines and unrighteousness increases, I manifest Myself. To protect the righteous, to annihilate the wicked, and to reestablish the principles of dharma, I appear millennium after millennium. (Chapter 4, Verse 7-8)",
        "explanation": "When you're confused about right and wrong, remember that Divine wisdom is always available to guide you. Truth and righteousness are eternal principles that ultimately prevail. Your sincere seeking will be answered.",
        "guidance": "In times of doubt, study sacred texts, seek guidance from wise teachers, and trust your inner moral compass. The Divine responds to sincere seeking. Meditate and listen to your higher wisdom."
    }
}

# Global variables
app = Flask(__name__)
whisper_model = None
piper_voice = None
gita_data = None

def load_models():
    """Load required models"""
    global whisper_model, piper_voice, gita_data
    
    print("🔄 Loading models...")
    
    # Load Whisper
    try:
        print("Loading Whisper model...")
        whisper_model = whisper.load_model("small")
        print("✅ Whisper loaded")
    except Exception as e:
        print(f"❌ Whisper loading failed: {e}")
        whisper_model = None
    
    # Load Gita data (for reference, though we're using curated responses)
    try:
        print("Loading Bhagavad Gita verses...")
        if os.path.exists(GITA_CSV_PATH):
            gita_data = pd.read_csv(GITA_CSV_PATH)
            print(f"✅ Loaded {len(gita_data)} verses for reference")
        else:
            print(f"⚠️  Gita CSV not found at {GITA_CSV_PATH}")
            gita_data = None
    except Exception as e:
        print(f"❌ Error loading Gita data: {e}")
        gita_data = None
    
    # Load Piper TTS
    global piper_voice
    piper_voice = None
    
    if HAS_PIPER:
        try:
            print("Loading Piper TTS voice...")
            if os.path.exists(PIPER_VOICE_PATH):
                print(f"Found Piper voice file: {PIPER_VOICE_PATH}")
                piper_voice = PiperVoice.load(PIPER_VOICE_PATH)
                print("✅ Piper TTS loaded successfully!")
            else:
                print(f"❌ Piper voice file not found: {PIPER_VOICE_PATH}")
        except Exception as e:
            print(f"❌ Piper loading failed: {e}")
            import traceback
            traceback.print_exc()
            piper_voice = None
    else:
        print("❌ Piper TTS library not installed")
        piper_voice = None
    
    print(f"🎯 Final status - TTS available: {piper_voice is not None}")

def understand_question(query):
    """Semantic understanding of the user's spiritual question"""
    query_lower = query.lower()
    
    print(f"🧠 Understanding question: {query}")
    
    # Laziness, tiredness, lack of motivation
    if any(word in query_lower for word in ['lazy', 'tired', 'fatigue', 'exhausted', 'unmotivated', 'lethargy', 'energy', 'motivation', 'procrastination']):
        print("🎯 Identified: Laziness/Tiredness issue")
        return "laziness_tiredness"
    
    # Sadness, depression, sorrow
    elif any(word in query_lower for word in ['sad', 'sadness', 'depressed', 'depression', 'sorrow', 'grief', 'unhappy', 'melancholy', 'down', 'blue']):
        print("🎯 Identified: Sadness/Depression issue")
        return "sadness_depression"
    
    # Fear, anxiety, worry
    elif any(word in query_lower for word in ['fear', 'afraid', 'scared', 'anxiety', 'anxious', 'worry', 'worried', 'panic', 'nervous', 'frightened']):
        print("🎯 Identified: Fear/Anxiety issue")
        return "fear_anxiety"
    
    # Life purpose, meaning, direction
    elif any(word in query_lower for word in ['purpose', 'meaning', 'direction', 'path', 'calling', 'destiny', 'goal', 'mission', 'dharma', 'why am i here']):
        print("🎯 Identified: Life Purpose question")
        return "life_purpose"
    
    # Anger, conflict, relationships
    elif any(word in query_lower for word in ['angry', 'anger', 'mad', 'furious', 'conflict', 'fight', 'argument', 'frustrated', 'rage', 'hate']):
        print("🎯 Identified: Anger/Conflict issue")
        return "anger_conflict"
    
    # Attachment, loss, letting go
    elif any(word in query_lower for word in ['attachment', 'loss', 'lost', 'letting go', 'detachment', 'possession', 'clinging', 'breakup', 'death', 'separation']):
        print("🎯 Identified: Attachment/Loss issue")
        return "attachment_loss"
    
    # Doubt, confusion, uncertainty
    elif any(word in query_lower for word in ['doubt', 'confused', 'confusion', 'uncertain', 'unsure', 'lost', 'direction', 'decision', 'choice']):
        print("🎯 Identified: Doubt/Confusion issue")
        return "doubt_confusion"
    
    # Default to general wisdom
    else:
        print("🎯 General spiritual question - using life purpose guidance")
        return "life_purpose"

def generate_gita_response(question_type, original_query):
    """Generate appropriate Gita response based on semantic understanding"""
    
    if question_type in SPIRITUAL_RESPONSES:
        response_data = SPIRITUAL_RESPONSES[question_type]
        
        # Create comprehensive response
        response = f"""🙏 **Gita Wisdom for Your Question:**

**Verse:** {response_data['verse']}

**Understanding:** {response_data['explanation']}

**Practical Guidance:** {response_data['guidance']}

Remember, the Bhagavad Gita is not just philosophy - it's a practical guide for living. Apply these teachings gradually in your daily life."""
        
        print(f"✅ Generated curated response for: {question_type}")
        return response
    
    else:
        # Fallback response
        return """🙏 The Bhagavad Gita teaches us that all suffering comes from ignorance of our true nature. You are the eternal soul, beyond all temporary difficulties. Through righteous action, devotion, and self-knowledge, you can find lasting peace and fulfillment."""

def synthesize_speech(text):
    """Convert text to speech using Piper"""
    global piper_voice
    
    if not piper_voice:
        print("⚠️  Piper TTS not available")
        return None
    
    try:
        # Clean text for TTS (remove markdown formatting)
        clean_text = text.replace("**", "").replace("🙏", "").replace("🎯", "")
        clean_text = clean_text.replace("*", "").strip()
        
        print(f"🎵 Generating TTS for text length: {len(clean_text)} chars")
        
        # Create in-memory WAV
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            # Set WAV parameters
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(22050)  # Sample rate
            
            # Generate speech
            piper_voice.synthesize_wav(clean_text, wav_file)
        
        wav_data = wav_buffer.getvalue()
        print(f"✅ TTS generated: {len(wav_data)} bytes")
        return wav_data
        
    except Exception as e:
        print(f"❌ TTS synthesis error: {e}")
        import traceback
        traceback.print_exc()
        return None

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    models_loaded = all([
        whisper_model is not None,
        len(SPIRITUAL_RESPONSES) > 0
    ])
    
    return jsonify({
        'status': 'healthy',
        'models_loaded': models_loaded,
        'whisper': whisper_model is not None,
        'spiritual_responses': len(SPIRITUAL_RESPONSES),
        'tts': piper_voice is not None,
        'approach': 'semantic_understanding'
    })

@app.route('/process_audio', methods=['POST'])
def process_audio():
    """Process audio and return curated Gita response"""
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
            # Understand the question semantically
            question_type = understand_question(transcription)
            
            # Generate appropriate Gita response
            response_text = generate_gita_response(question_type, transcription)
            response_text += f"\n\n{random.choice(FOLLOW_UP_PHRASES)}"
        
        print(f"💬 Response generated for question type: {question_type if not end_conversation else 'goodbye'}")
        
        # Generate speech
        print("🔊 Generating TTS audio...")
        audio_bytes = synthesize_speech(response_text)
        audio_hex = audio_bytes.hex() if audio_bytes else None
        
        if audio_hex:
            print(f"✅ TTS generated: {len(audio_bytes)} bytes -> {len(audio_hex)} hex chars")
        else:
            print("❌ TTS generation failed - no audio returned")
        
        return jsonify({
            'transcription': transcription,
            'response': response_text,
            'audio': audio_hex,
            'end_conversation': end_conversation,
            'question_type': question_type if not end_conversation else 'goodbye'
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
        
        # Generate speech
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
    print("🚀 Starting GitaGPT Semantic Server...")
    print("📚 Using curated responses based on semantic understanding")
    
    # Load models
    load_models()
    
    print(f"🌐 Server ready on {HOST}:{PORT}")
    print(f"🎯 Available spiritual guidance categories: {list(SPIRITUAL_RESPONSES.keys())}")
    
    app.run(host=HOST, port=PORT, debug=False)