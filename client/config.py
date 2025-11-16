"""
Client Configuration for GitaGPT
"""

# Network Configuration
LAPTOP_IP = "192.168.1.100"  # UPDATE THIS: Your server's IP address
LAPTOP_PORT = 5000

# Audio Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 10

# Arduino Configuration
ARDUINO_PORT = "/dev/ttyUSB0"  # UPDATE THIS: Check with 'ls /dev/tty*' on Pi
ARDUINO_BAUDRATE = 9600

# Audio Method Priorities (will auto-detect best available)
PREFERRED_AUDIO_METHODS = ["sounddevice", "pyaudio", "system"]

# System Audio Players (fallback commands)
AUDIO_PLAYERS = [
    ["aplay"],
    ["omxplayer"],
    ["cvlc", "--play-and-exit"],
]