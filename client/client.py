#!/usr/bin/env python3

"""
Complete GitaGPT Humanoid Robot Client - client5
Integrates working audio system with original Arduino jaw control
Uses ENTER key toggle for recording, synchronized jaw movement during speech
"""
import os
import time
import wave
import requests
import json
from io import BytesIO
import binascii
import subprocess
import threading
import numpy as np

# Serial communication with Arduino
try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
    print("✅ Serial communication available")
except ImportError:
    HAS_SERIAL = False
    print("⚠️  Serial communication not available")

try:
    import sounddevice as sd
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
LAPTOP_IP = "192.168.104.80"  # Your laptop IP
LAPTOP_PORT = 5000
SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 10

# Arduino configuration (from your original code)
ARDUINO_PORT = "/dev/ttyUSB0"  # Change as needed
ARDUINO_BAUDRATE = 9600

class ArduinoJawController:
    """Arduino jaw control using your original single-character commands"""
    
    def __init__(self):
        self.arduino = None
        self.is_connected = False
        self.jaw_moving = False
        self.jaw_thread = None
        
        if HAS_SERIAL:
            self.init_arduino()
    
    def find_arduino_ports(self):
        """Find potential Arduino ports"""
        if not HAS_SERIAL:
            return []
            
        ports = []
        
        # Try common ports first
        common_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
        for port in common_ports:
            if os.path.exists(port):
                ports.append(port)
        
        # Also check detected serial ports
        detected = serial.tools.list_ports.comports()
        for port in detected:
            if port.device not in ports:
                ports.append(port.device)
                
        return ports
    
    def init_arduino(self):
        """Initialize Arduino connection with better stability"""
        try:
            # Try the configured port first
            ports_to_try = [ARDUINO_PORT] + self.find_arduino_ports()
            
            for port in ports_to_try:
                try:
                    print(f"🔌 Trying Arduino on {port}...")
                    
                    # Close any existing connection
                    if self.arduino:
                        try:
                            self.arduino.close()
                        except:
                            pass
                    
                    # Open new connection with better settings
                    self.arduino = serial.Serial(
                        port, 
                        ARDUINO_BAUDRATE, 
                        timeout=2,           # Longer timeout
                        write_timeout=2,     # Write timeout
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE
                    )
                    
                    time.sleep(3)  # Longer wait for Arduino to initialize
                    
                    # Clear any existing data in buffers
                    self.arduino.flushInput()
                    self.arduino.flushOutput()
                    
                    # Test connection with multiple attempts
                    test_success = False
                    for attempt in range(3):
                        try:
                            self.arduino.write(b'c')  # Close jaw as test
                            self.arduino.flush()
                            time.sleep(0.2)
                            test_success = True
                            break
                        except Exception as e:
                            print(f"⚠️  Test attempt {attempt + 1} failed: {e}")
                            time.sleep(0.5)
                    
                    if test_success:
                        print(f"✅ Connected to Arduino on {port}")
                        self.is_connected = True
                        return
                    else:
                        print(f"❌ Arduino test failed on {port}")
                        
                except Exception as e:
                    print(f"⚠️  Failed on {port}: {e}")
                    if self.arduino:
                        try:
                            self.arduino.close()
                        except:
                            pass
                        self.arduino = None
            
            print("❌ Failed to connect to Arduino on any port")
            self.is_connected = False
            
        except Exception as e:
            print(f"❌ Arduino connection error: {e}")
            self.is_connected = False
    
    def send_jaw_command(self, command):
        """Send jaw control command to Arduino with better error handling"""
        if not self.arduino or not self.arduino.is_open:
            return False
            
        try:
            # Send command as string with newline (matching Arduino code)
            command_str = f"{command.upper()}\n"  # 'O\n' or 'C\n'
            self.arduino.write(command_str.encode())  
            self.arduino.flush()  # Ensure data is sent immediately
            
            # Wait for Arduino response
            time.sleep(0.1)
            if self.arduino.in_waiting > 0:
                response = self.arduino.readline().decode().strip()
                print(f"📡 Arduino: {response}")
            
            print(f"✅ Sent to Arduino: '{command.upper()}'")
            return True
        except serial.SerialTimeoutException:
            print("⚠️  Arduino write timeout")
            return False
        except serial.SerialException as e:
            print(f"❌ Arduino serial error: {e}")
            # Try to reconnect
            self.reconnect_arduino()
            return False
        except Exception as e:
            print(f"❌ Arduino send error: {e}")
            return False
    
    def reconnect_arduino(self):
        """Try to reconnect to Arduino"""
        print("🔄 Attempting to reconnect to Arduino...")
        if self.arduino:
            try:
                self.arduino.close()
            except:
                pass
        
        time.sleep(1)
        self.init_arduino()
        
        if self.is_connected:
            print("✅ Arduino reconnected successfully")
        else:
            print("❌ Arduino reconnection failed")
    
    def move_jaw_simple(self):
        """Jaw movement pattern: 3s open → 3s close → 3s open → close when done"""
        print("🦾 Starting jaw animation pattern...")
        
        start_time = time.time()
        
        while self.jaw_moving:
            elapsed = time.time() - start_time
            cycle_position = elapsed % 9  # 9 second cycle (3+3+3)
            
            if cycle_position < 3:
                # First 3 seconds: OPEN
                if not hasattr(self, '_current_jaw_state') or self._current_jaw_state != 'open':
                    print("🗣️ Opening jaw (0-3s)")
                    self.send_jaw_command('O')
                    self._current_jaw_state = 'open'
                    
            elif cycle_position < 6:
                # Next 3 seconds: CLOSE  
                if not hasattr(self, '_current_jaw_state') or self._current_jaw_state != 'closed':
                    print("🤐 Closing jaw (3-6s)")
                    self.send_jaw_command('C')
                    self._current_jaw_state = 'closed'
                    
            else:
                # Last 3 seconds: OPEN again
                if not hasattr(self, '_current_jaw_state') or self._current_jaw_state != 'open_again':
                    print("🗣️ Opening jaw again (6-9s)")
                    self.send_jaw_command('O')
                    self._current_jaw_state = 'open_again'
            
            time.sleep(0.5)  # Check every 500ms
        
        print("🤐 Audio finished - closing jaw...")
        
        # Close jaw at end of speech (try multiple times to ensure it closes)
        for _ in range(3):
            if self.send_jaw_command('C'):
                print("✅ Jaw closed")
                break
            time.sleep(0.2)  # Small delay between attempts
        
        # Reset state tracking
        if hasattr(self, '_current_jaw_state'):
            delattr(self, '_current_jaw_state')
    
    def start_speaking(self):
        """Start jaw movement for speaking"""
        if not self.jaw_moving and self.is_connected:
            self.jaw_moving = True
            self.jaw_thread = threading.Thread(target=self.move_jaw_simple, daemon=True)
            self.jaw_thread.start()
            print("🗣️  Arduino jaw opened for speech")
    
    def stop_speaking(self):
        """Stop jaw movement"""
        if self.jaw_moving:
            self.jaw_moving = False
            if self.jaw_thread and self.jaw_thread.is_alive():
                self.jaw_thread.join(timeout=1.0)
            print("🤐 Arduino jaw animation stopped")
    
    def test_arduino_connection(self):
        """Test Arduino connection with manual jaw movement"""
        if not self.is_connected:
            print("❌ Arduino not connected")
            return False
            
        print("🔧 Testing Arduino jaw movement...")
        
        try:
            # Test sequence: close -> open -> close
            commands = ['c', 'o', 'c', 'o', 'c']
            
            for i, cmd in enumerate(commands):
                print(f"Sending command {i+1}/{len(commands)}: '{cmd}'")
                success = self.send_jaw_command(cmd)
                
                if success:
                    print("✅ Command sent successfully")
                else:
                    print("❌ Command failed")
                    return False
                
                time.sleep(0.5)  # Wait to see the movement
            
            print("✅ Arduino jaw test completed")
            return True
            
        except Exception as e:
            print(f"❌ Arduino test error: {e}")
            return False
    
    def cleanup(self):
        """Clean up Arduino connection"""
        self.jaw_moving = False
        
        if self.arduino and self.arduino.is_open:
            try:
                # Send close command multiple times to ensure jaw closes
                for _ in range(3):
                    self.arduino.write(b'c')  # Close jaw
                    self.arduino.flush()
                    time.sleep(0.1)
                
                time.sleep(0.5)
                self.arduino.close()
                print("✅ Arduino disconnected")
            except Exception as e:
                print(f"⚠️  Arduino cleanup error: {e}")

class GitaGPTHumanoidRobot:
    def __init__(self):
        self.server_url = f"http://{LAPTOP_IP}:{LAPTOP_PORT}"
        self.recording = False
        
        # Initialize Arduino jaw controller only
        self.arduino_jaw = ArduinoJawController()
        
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
        """Record audio for specified duration"""
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
            print(f"🎤 Recording for {RECORD_SECONDS} seconds...")
            print("🔴 SPEAK NOW!")
            
            audio_data = sd.rec(
                int(RECORD_SECONDS * SAMPLE_RATE), 
                samplerate=SAMPLE_RATE, 
                channels=CHANNELS, 
                dtype=np.int16
            )
            sd.wait()
            print("✅ Recording finished")
            
            max_amp = np.max(np.abs(audio_data))
            print(f"Audio level: {max_amp}")
            
            return audio_data.tobytes()
        except Exception as e:
            print(f"❌ Recording error: {e}")
            return None
    
    def record_pyaudio(self):
        """Record using pyaudio"""
        try:
            print(f"🎤 Recording for {RECORD_SECONDS} seconds...")
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
    
    def play_audio_with_jaw(self, audio_hex):
        """Play audio with jaw movement synchronized to actual audio duration"""
        try:
            print("🔊 Playing audio with jaw animation...")
            
            # Convert hex to binary
            audio_data = binascii.unhexlify(audio_hex)
            print(f"Audio data size: {len(audio_data)} bytes")
            
            # Save audio to temp file first to get duration
            temp_file = "/tmp/gita_response.wav"
            with open(temp_file, "wb") as f:
                f.write(audio_data)
            
            # Get audio duration
            audio_duration = self.get_audio_duration(temp_file)
            print(f"Audio duration: {audio_duration:.1f} seconds")
            
            # Start jaw animation - Arduino only
            if self.arduino_jaw.is_connected:
                self.arduino_jaw.start_speaking()
            else:
                print("⚠️  Arduino not connected - no jaw movement")
            
            # Play audio - the jaw will keep moving until audio finishes
            audio_played = False
            
            if self.audio_method == "sounddevice":
                audio_played = self.play_sounddevice(temp_file)  # sd.wait() already waits for completion
            elif self.audio_method == "pyaudio":
                audio_played = self.play_pyaudio(temp_file)  # stream.write() blocks until complete
            
            if not audio_played:
                audio_played = self.play_with_system_timed(temp_file, audio_duration)
            
            # Stop jaw animation after audio finishes
            if self.arduino_jaw.is_connected:
                self.arduino_jaw.stop_speaking()
            else:
                print("⚠️  Arduino not connected - no jaw to close")
            
            if audio_played:
                print("✅ Audio and jaw animation complete")
            else:
                print("❌ Audio playback failed")
                
        except Exception as e:
            print(f"❌ Audio playback error: {e}")
            # Make sure to stop jaw animation on error
            if self.arduino_jaw.is_connected:
                self.arduino_jaw.stop_speaking()
    
    def get_audio_duration(self, audio_file):
        """Get duration of audio file in seconds"""
        try:
            with wave.open(audio_file, 'rb') as wf:
                frames = wf.getnframes()
                sample_rate = wf.getframerate()
                duration = frames / sample_rate
                return duration
        except Exception as e:
            print(f"⚠️  Could not get audio duration: {e}")
            return 5.0  # Default fallback duration
    
    def play_sounddevice(self, audio_file):
        """Play using sounddevice"""
        try:
            with wave.open(audio_file, 'rb') as wf:
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                frames = wf.readframes(wf.getnframes())
                
                audio_array = np.frombuffer(frames, dtype=np.int16)
                if channels == 2:
                    audio_array = audio_array.reshape(-1, 2)
                
                print(f"Playing: {sample_rate}Hz, {channels}ch")
                sd.play(audio_array, samplerate=sample_rate)
                sd.wait()
                return True
        except Exception as e:
            print(f"⚠️  Sounddevice playback failed: {e}")
            return False
    
    def play_pyaudio(self, audio_file):
        """Play using pyaudio"""
        try:
            wf = wave.open(audio_file, 'rb')
            p = pyaudio.PyAudio()
            
            stream = p.open(
                format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )
            
            chunk = 1024
            data = wf.readframes(chunk)
            while data:
                stream.write(data)
                data = wf.readframes(chunk)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            wf.close()
            return True
        except Exception as e:
            print(f"⚠️  PyAudio playback failed: {e}")
            return False
    
    def play_with_system_timed(self, audio_file, audio_duration):
        """Play using system commands and ensure jaw moves for full duration"""
        players = [
            ["aplay", audio_file],
            ["omxplayer", audio_file],
            ["cvlc", "--play-and-exit", audio_file],
        ]
        
        for player_cmd in players:
            try:
                print(f"Trying: {' '.join(player_cmd)}")
                # Run the player and let it finish naturally
                result = subprocess.run(player_cmd, 
                                      capture_output=True, 
                                      timeout=audio_duration + 5)  # Extra 5s safety
                if result.returncode == 0:
                    print(f"✅ Audio played with {player_cmd[0]}")
                    return True
                else:
                    print(f"⚠️  {player_cmd[0]} failed")
            except FileNotFoundError:
                print(f"⚠️  {player_cmd[0]} not found")
                continue
            except subprocess.TimeoutExpired:
                print(f"⚠️  {player_cmd[0]} timed out")
                continue
            except Exception as e:
                print(f"⚠️  {player_cmd[0]} error: {e}")
                continue
        
        print("❌ No system audio player worked")
        print(f"⏰ Waiting {audio_duration:.1f}s to keep jaw moving...")
        time.sleep(audio_duration)  # Keep jaw moving even if audio failed
        return False
    
    def play_with_system(self, audio_file):
        """Play using system commands"""
        players = [
            ["aplay", audio_file],
            ["omxplayer", audio_file],
            ["cvlc", "--play-and-exit", audio_file],
        ]
        
        for player_cmd in players:
            try:
                result = subprocess.run(player_cmd, capture_output=True, timeout=30)
                if result.returncode == 0:
                    print(f"✅ Audio played with {player_cmd[0]}")
                    return True
            except FileNotFoundError:
                continue
            except Exception:
                continue
        
        print("❌ No system audio player worked")
        return False
    
    def process_question(self):
        """Process a question (record → send → play response)"""
        print("\n🎯 Press ENTER to start recording...")
        input()  # Wait for ENTER key
        
        # Record audio
        audio_data = self.record_audio()
        if not audio_data:
            print("❌ No audio recorded")
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
                
                # Play audio with jaw movement
                audio_hex = result.get('audio')
                if audio_hex:
                    self.play_audio_with_jaw(audio_hex)
                else:
                    print("⚠️  No audio response from server")
                    
            else:
                print(f"❌ Server error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error communicating with server: {e}")
    
    def check_server_health(self):
        """Check server health"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                print(f"✅ Server healthy: {health}")
                return health.get("models_loaded", False)
            else:
                print(f"❌ Server unhealthy: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot reach server: {e}")
            return False
    
    def run(self):
        """Main robot loop"""
        print("🤖 GitaGPT Humanoid Robot Client")
        print("="*50)
        print(f"📡 Server: {self.server_url}")
        print(f"🤖 Arduino: {'✅ Connected' if self.arduino_jaw.is_connected else '❌ Not Connected'}")
        
        # Check server
        if not self.check_server_health():
            print("❌ Server not available - exiting")
            return
        
        # Initialize jaw position
        if self.arduino_jaw.is_connected:
            self.arduino_jaw.send_jaw_command('c')  # Close jaw
            print("🤐 Arduino jaw set to closed position")
        
        print("\n🎙️  Humanoid robot ready!")
        print("📋 Instructions:")
        print("   • Press ENTER to record question")
        print("   • Type 'test' to test Arduino jaw movement")
        print("   • Speak clearly for 10 seconds")
        print("   • Watch jaw move during Gita's response")
        print("   • Type 'quit' to exit")
        print("="*50)
        
        try:
            while True:
                user_input = input("\n🎯 Press ENTER to ask question, 'test' for jaw test, or 'quit': ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("🙏 Om Shanti! Robot shutting down...")
                    break
                elif user_input.lower() == 'test':
                    if self.arduino_jaw.is_connected:
                        self.arduino_jaw.test_arduino_connection()
                    else:
                        print("❌ Arduino not connected - cannot test")
                elif user_input == '':  # ENTER key pressed
                    self.process_question()
                else:
                    print("⚠️  Unknown command. Press ENTER, type 'test', or 'quit'")
                
                print("\n" + "-"*40)
                
        except KeyboardInterrupt:
            print("\n🙏 Om Shanti! Robot shutting down...")
        
        finally:
            # Cleanup
            print("🧹 Cleaning up robot systems...")
            self.arduino_jaw.cleanup()
            print("✅ Robot shutdown complete")

def main():
    print("🚀 Starting GitaGPT Humanoid Robot...")
    
    # System check
    if not (HAS_SOUNDDEVICE or HAS_PYAUDIO):
        print("⚠️  No audio libraries - install sounddevice or pyaudio")
    if not HAS_SERIAL:
        print("⚠️  No serial library - install pyserial for Arduino")
    
    robot = GitaGPTHumanoidRobot()
    robot.run()

if __name__ == "__main__":
    main()