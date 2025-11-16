#!/usr/bin/env python3
"""
GitaGPT Pi Client with Audio Playback
Complete version that plays the server's audio response
"""
import os
import time
import wave
import requests
import json
from io import BytesIO
import binascii
import subprocess

try:
    import sounddevice as sd
    import numpy as np
    HAS_SOUNDDEVICE = True
    print("✅ sounddevice available")
except ImportError:
    HAS_SOUNDDEVICE = False
    print("⚠️  sounddevice not available")

try:
    import pyaudio
    HAS_PYAUDIO = True
    print("✅ pyaudio available")
except ImportError:
    HAS_PYAUDIO = False
    print("⚠️  pyaudio not available")

# Configuration
LAPTOP_IP = "192.168.8.80"
LAPTOP_PORT = 5000
SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 5

class GitaGPTClient:
    def __init__(self):
        self.server_url = f"http://{LAPTOP_IP}:{LAPTOP_PORT}"
        
        # Choose audio method
        if HAS_SOUNDDEVICE:
            print("🔊 Using sounddevice for audio")
            self.audio_method = "sounddevice"
        elif HAS_PYAUDIO:
            print("🔊 Using pyaudio for audio")
            self.audio_method = "pyaudio"
        else:
            print("⚠️  Using system audio commands")
            self.audio_method = "system"
    
    def record_audio(self):
        """Record audio using available method"""
        if self.audio_method == "sounddevice":
            return self.record_sounddevice()
        elif self.audio_method == "pyaudio":
            return self.record_pyaudio()
        else:
            print("❌ No audio recording method available")
            return None
    
    def record_sounddevice(self):
        """Record using sounddevice"""
        try:
            print("🎤 Recording for 5 seconds...")
            print("🔴 SPEAK NOW!")
            
            audio_data = sd.rec(
                int(RECORD_SECONDS * SAMPLE_RATE), 
                samplerate=SAMPLE_RATE, 
                channels=CHANNELS, 
                dtype=np.int16
            )
            sd.wait()
            print("✅ Recording finished")
            
            # Check audio level
            max_amp = np.max(np.abs(audio_data))
            print(f"Audio level: {max_amp}")
            
            return audio_data.tobytes()
        except Exception as e:
            print(f"❌ Recording error: {e}")
            return None
    
    def record_pyaudio(self):
        """Record using pyaudio"""
        try:
            print("🎤 Recording for 5 seconds...")
            print("🔴 SPEAK NOW!")
            
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=1024
            )
            
            frames = []
            for _ in range(0, int(SAMPLE_RATE / 1024 * RECORD_SECONDS)):
                data = stream.read(1024)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            print("✅ Recording finished")
            
            return b''.join(frames)
        except Exception as e:
            print(f"❌ Recording error: {e}")
            return None
    
    def play_audio(self, audio_hex):
        """Play audio response from server"""
        try:
            print("🔊 Playing audio response...")
            
            # Convert hex to binary
            audio_data = binascii.unhexlify(audio_hex)
            print(f"Audio data size: {len(audio_data)} bytes")
            
            if self.audio_method == "sounddevice":
                # Play with sounddevice
                # First, let's save to a temp file and get the format
                temp_file = "/tmp/response.wav"
                with open(temp_file, "wb") as f:
                    f.write(audio_data)
                
                # Try to play with sounddevice
                try:
                    # Read the WAV file to get proper format
                    with wave.open(temp_file, 'rb') as wf:
                        sample_rate = wf.getframerate()
                        channels = wf.getnchannels()
                        frames = wf.readframes(wf.getnframes())
                        
                        # Convert to numpy array
                        audio_array = np.frombuffer(frames, dtype=np.int16)
                        if channels == 2:
                            audio_array = audio_array.reshape(-1, 2)
                        
                        print(f"Playing: {sample_rate}Hz, {channels}ch, {len(audio_array)} samples")
                        sd.play(audio_array, samplerate=sample_rate)
                        sd.wait()  # Wait until playback is finished
                        print("✅ Playback finished")
                except Exception as sd_error:
                    print(f"⚠️  Sounddevice playback failed: {sd_error}")
                    # Fallback to system command
                    self.play_with_system(temp_file)
                
            elif self.audio_method == "pyaudio":
                # Play with pyaudio
                temp_file = "/tmp/response.wav"
                with open(temp_file, "wb") as f:
                    f.write(audio_data)
                
                try:
                    wf = wave.open(temp_file, 'rb')
                    p = pyaudio.PyAudio()
                    
                    stream = p.open(
                        format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True
                    )
                    
                    # Play the audio
                    chunk = 1024
                    data = wf.readframes(chunk)
                    while data:
                        stream.write(data)
                        data = wf.readframes(chunk)
                    
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    wf.close()
                    print("✅ Playback finished")
                    
                except Exception as pa_error:
                    print(f"⚠️  PyAudio playback failed: {pa_error}")
                    # Fallback to system command
                    self.play_with_system(temp_file)
            else:
                # Use system command
                temp_file = "/tmp/response.wav"
                with open(temp_file, "wb") as f:
                    f.write(audio_data)
                self.play_with_system(temp_file)
                
        except Exception as e:
            print(f"❌ Audio playback error: {e}")
    
    def play_with_system(self, audio_file):
        """Play audio using system commands"""
        print("🔊 Trying system audio players...")
        
        # Try different audio players available on Pi
        players = [
            ["aplay", audio_file],           # ALSA player (most common on Pi)
            ["omxplayer", audio_file],       # Pi-specific player
            ["mpg123", audio_file],          # MP3 player (may work with WAV)
            ["cvlc", "--play-and-exit", audio_file],  # VLC command line
            ["paplay", audio_file],          # PulseAudio player
        ]
        
        for player_cmd in players:
            try:
                print(f"Trying: {' '.join(player_cmd)}")
                result = subprocess.run(player_cmd, 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=30)
                if result.returncode == 0:
                    print("✅ Audio played successfully!")
                    return
                else:
                    print(f"⚠️  {player_cmd[0]} failed: {result.stderr}")
            except FileNotFoundError:
                print(f"⚠️  {player_cmd[0]} not found")
            except subprocess.TimeoutExpired:
                print(f"⚠️  {player_cmd[0]} timed out")
            except Exception as e:
                print(f"⚠️  {player_cmd[0]} error: {e}")
        
        print("❌ Could not play audio with any system player")
        print("💡 Try installing: sudo apt install alsa-utils")
    
    def process_question(self):
        """Record question and get response"""
        print("\n🎯 Ready to record your question...")
        input("Press ENTER to start recording...")
        
        # Record audio
        audio_data = self.record_audio()
        if not audio_data:
            print("❌ Recording failed")
            return
        
        try:
            # Send to server
            print("📡 Sending to server...")
            response = requests.post(
                f"{self.server_url}/process_audio",
                data=audio_data,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print("✅ Server response received!")
                print(f"📝 You asked: '{result.get('transcription', 'Unknown')}'")
                print(f"🙏 Gita says: {result.get('response', 'No response')}")
                
                # Play audio response
                audio_hex = result.get('audio')
                if audio_hex:
                    self.play_audio(audio_hex)
                else:
                    print("⚠️  No audio response from server")
                    
            else:
                print(f"❌ Server error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error communicating with server: {e}")
    
    def check_server(self):
        """Check if server is available"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                print(f"✅ Server healthy: {health}")
                return True
            else:
                print(f"❌ Server unhealthy: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot reach server: {e}")
            return False
    
    def run(self):
        """Main client loop"""
        print("🕉️  GitaGPT Pi Client with Audio")
        print("="*40)
        print(f"📡 Server: {self.server_url}")
        
        # Check server
        if not self.check_server():
            print("❌ Server not available - exiting")
            return
        
        print("\n🎙️  Ready for questions!")
        print("📋 Instructions:")
        print("   • Press ENTER to record question")
        print("   • Speak clearly for 5 seconds")
        print("   • Listen to Gita's wisdom")
        print("   • Type 'quit' to exit")
        print("="*40)
        
        while True:
            try:
                user_input = input("\n🎯 Press ENTER to ask question (or 'quit'): ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("🙏 Om Shanti! Goodbye!")
                    break
                
                self.process_question()
                
                print("\n" + "-"*30)
                
            except KeyboardInterrupt:
                print("\n🙏 Om Shanti! Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(1)

def main():
    print("🚀 Starting GitaGPT Pi Client...")
    
    client = GitaGPTClient()
    client.run()

if __name__ == "__main__":
    main()