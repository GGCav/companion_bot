# Companion Bot - Hardware Setup Guide

Complete hardware wiring and configuration guide for Raspberry Pi 4, Mini Microphone, and Pi Camera v2.

## Table of Contents
1. [Hardware Requirements](#hardware-requirements)
2. [Wiring Diagrams](#wiring-diagrams)
3. [Software Installation](#software-installation)
4. [Hardware Testing](#hardware-testing)
5. [Troubleshooting](#troubleshooting)

---

## Hardware Requirements

### Core Components
- **Raspberry Pi 4** (4GB RAM minimum, 8GB recommended)
- **Pi Camera Module v2** (8MP, 1080p)
- **Mini USB Microphone** (or I2S MEMS microphone)
- **Speaker** (3W or higher, 3.5mm jack or USB)
- **TFT Display** (3.5" - 7", SPI or HDMI)
- **MicroSD Card** (32GB minimum, Class 10)
- **Power Supply** (5V 3A USB-C for Pi 4)
- **Portable Battery** (10000mAh+ for mobile operation)

### Sensors
- **3x Capacitive Touch Sensors** (TTP223 or similar)
- **1x Ultrasonic Sensor** (HC-SR04)
- **1x PIR Motion Sensor** (HC-SR501)

### Motors & Actuators
- **5x Servo Motors** (SG90 or MG90S)
  - 2x for head movement (pan/tilt)
  - 2x for ears
  - 1x for tail
- **Optional: PCA9685 16-Channel Servo Driver** (recommended for smoother control)

### Lab 3 Robot Kit
- Motor driver board
- Wheels and chassis
- DC motors

### Miscellaneous
- Jumper wires (Male-to-Female, Male-to-Male)
- Breadboard
- Resistors (if needed for voltage dividers)
- Screws and mounting hardware

---

## Wiring Diagrams

### Pin Configuration (GPIO BCM Mode)

```
Raspberry Pi 4 GPIO Pinout (BCM numbering)
==========================================

Touch Sensors:
  GPIO 17 - Touch Sensor (Head)
  GPIO 27 - Touch Sensor (Body)
  GPIO 22 - Touch Sensor (Back)

Ultrasonic Sensor (HC-SR04):
  GPIO 23 - Trigger Pin
  GPIO 24 - Echo Pin

PIR Motion Sensor:
  GPIO 25 - Signal Pin

Servos (if using direct GPIO):
  GPIO 12 - Head Pan Servo
  GPIO 13 - Head Tilt Servo
  GPIO 18 - Left Ear Servo
  GPIO 19 - Right Ear Servo
  GPIO 26 - Tail Servo

Lab 3 Robot Motors:
  GPIO 5  - Left Motor Forward
  GPIO 6  - Left Motor Backward
  GPIO 16 - Right Motor Forward
  GPIO 20 - Right Motor Backward

I2C (for PCA9685 Servo Driver - Optional):
  GPIO 2 (SDA) - I2C Data
  GPIO 3 (SCL) - I2C Clock

Camera:
  CSI Port - Pi Camera Module v2

Audio:
  USB Port - Mini Microphone
  3.5mm Jack or USB - Speaker

Display:
  HDMI - TFT Display (HDMI connection)
  OR
  SPI Pins - TFT Display (SPI connection)
```

### Detailed Wiring

#### 1. Touch Sensors (TTP223)

Each capacitive touch sensor has 3 pins:
- **VCC** → 3.3V (Pin 1 or 17)
- **GND** → Ground (Pin 6, 9, 14, 20, 25, 30, 34, or 39)
- **OUT** → GPIO Pin (17, 27, or 22)

```
Touch Sensor (Head):
  VCC → 3.3V
  GND → Ground
  OUT → GPIO 17

Touch Sensor (Body):
  VCC → 3.3V
  GND → Ground
  OUT → GPIO 27

Touch Sensor (Back):
  VCC → 3.3V
  GND → Ground
  OUT → GPIO 22
```

#### 2. Ultrasonic Sensor (HC-SR04)

**IMPORTANT:** HC-SR04 operates at 5V, but Pi GPIO is 3.3V. Use a voltage divider for Echo pin!

```
HC-SR04 Connections:
  VCC → 5V (Pin 2 or 4)
  GND → Ground
  TRIG → GPIO 23 (direct connection OK)
  ECHO → GPIO 24 (through voltage divider!)

Voltage Divider for Echo Pin:
  Echo → 1kΩ resistor → GPIO 24
         └─ 2kΩ resistor → Ground
  (This divides 5V to ~3.3V)
```

#### 3. PIR Motion Sensor (HC-SR501)

```
PIR Sensor:
  VCC → 5V
  GND → Ground
  OUT → GPIO 25
```

#### 4. Servo Motors

**Option A: Direct GPIO Connection (Simple but less smooth)**

```
Each Servo (SG90/MG90S):
  Brown/Black → Ground
  Red → 5V (external power recommended!)
  Orange/Yellow → GPIO PWM pin

IMPORTANT: DO NOT power multiple servos from Pi's 5V!
Use external 5V power supply (2A minimum) with common ground.
```

**Option B: PCA9685 Servo Driver (Recommended)**

```
PCA9685 16-Channel PWM Driver:
  VCC → 3.3V (Pi power)
  GND → Ground (common with Pi and servo power)
  SDA → GPIO 2 (I2C Data)
  SCL → GPIO 3 (I2C Clock)

  V+ → External 5-6V power supply (for servos)

  Channels 0-4 → Servo signal wires
```

Benefits of PCA9685:
- Dedicated PWM chip offloads Pi CPU
- Smoother servo control
- Can drive 16 servos simultaneously
- Better power management

#### 5. Pi Camera v2

```
Camera Connection:
1. Locate CSI port (between HDMI and audio jack)
2. Pull up on black tabs gently
3. Insert ribbon cable (blue side facing audio jack)
4. Push tabs back down to lock

Test: libcamera-hello (should show preview)
```

#### 6. Mini Microphone

**USB Microphone:**
```
Simply plug into any USB port.

Test with:
  arecord -l        # List recording devices
  arecord -D hw:1,0 -d 5 test.wav  # Record 5 seconds
  aplay test.wav    # Play back
```

**I2S MEMS Microphone (Advanced):**
```
Requires I2S configuration in /boot/config.txt
See: https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout
```

#### 7. Speaker

**3.5mm Audio Jack:**
```
Plug into audio jack.

Enable audio output:
  sudo raspi-config
  → System Options → Audio → Headphones

Test: aplay /usr/share/sounds/alsa/Front_Center.wav
```

**USB Speaker:**
```
Plug into USB port.
Set as default in settings.yaml or alsamixer.
```

#### 8. TFT Display

**HDMI Display (Easiest):**
```
Connect via micro-HDMI cable.
Auto-detected on boot.
```

**SPI Display (3.5"):**
```
Requires driver installation.
See manufacturer instructions (varies by model).
Common: Waveshare, Adafruit displays.
```

---

## Software Installation

### Step 1: Prepare Raspberry Pi

1. **Flash Raspberry Pi OS:**
   - Download Raspberry Pi OS Lite or Desktop
   - Use Raspberry Pi Imager
   - Flash to microSD card
   - Enable SSH in imager settings

2. **First Boot Setup:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo raspi-config
   # Enable: Camera, I2C, SSH
   # Set timezone and locale
   sudo reboot
   ```

### Step 2: Clone Repository

```bash
cd ~
git clone <your-repo-url> companion_bot
cd companion_bot
```

### Step 3: Run Setup Script

```bash
chmod +x setup.sh
./setup.sh
```

This script will:
- Install system dependencies
- Create Python virtual environment
- Install Python packages
- Install Ollama and download model
- Enable GPIO and camera interfaces
- Install pigpio for servo control
- Create systemd service

### Step 4: Configure Hardware

Edit `config/settings.yaml` to match your wiring:

```bash
nano config/settings.yaml
```

Update GPIO pin numbers, camera settings, audio devices, etc.

### Step 5: Test Installation

```bash
# Activate virtual environment
source venv/bin/activate

# Run hardware tests
python scripts/test_hardware.py
```

---

## Hardware Testing

### Test Individual Components

Create `scripts/test_hardware.py`:

```bash
mkdir -p scripts
nano scripts/test_hardware.py
```

```python
#!/usr/bin/env python3
"""Hardware component testing script"""

import sys
import yaml

# Test imports
print("Testing imports...")
try:
    import RPi.GPIO as GPIO
    import cv2
    import pyaudio
    import pygame
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test GPIO
print("\nTesting GPIO...")
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
print("✓ GPIO initialized")

# Test Camera
print("\nTesting Pi Camera...")
try:
    from picamera2 import Picamera2
    camera = Picamera2()
    camera.start()
    camera.stop()
    print("✓ Camera working")
except Exception as e:
    print(f"✗ Camera failed: {e}")

# Test Audio Input
print("\nTesting Microphone...")
try:
    p = pyaudio.PyAudio()
    info = p.get_default_input_device_info()
    print(f"✓ Default microphone: {info['name']}")
    p.terminate()
except Exception as e:
    print(f"✗ Microphone failed: {e}")

# Test Audio Output
print("\nTesting Speaker...")
try:
    pygame.mixer.init()
    print("✓ Speaker initialized")
    pygame.mixer.quit()
except Exception as e:
    print(f"✗ Speaker failed: {e}")

print("\n" + "="*50)
print("Hardware test complete!")
print("="*50)
```

Run the test:
```bash
chmod +x scripts/test_hardware.py
python scripts/test_hardware.py
```

### Individual Component Tests

**Test Touch Sensor:**
```python
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

print("Touch sensor test - touch GPIO 17")
for i in range(100):
    if GPIO.input(17):
        print("TOUCHED!")
    time.sleep(0.1)

GPIO.cleanup()
```

**Test Ultrasonic Sensor:**
```python
import RPi.GPIO as GPIO
import time

TRIG = 23
ECHO = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

GPIO.output(TRIG, False)
time.sleep(0.1)

GPIO.output(TRIG, True)
time.sleep(0.00001)
GPIO.output(TRIG, False)

while GPIO.input(ECHO) == 0:
    pulse_start = time.time()

while GPIO.input(ECHO) == 1:
    pulse_end = time.time()

distance = ((pulse_end - pulse_start) * 34300) / 2
print(f"Distance: {distance:.1f} cm")

GPIO.cleanup()
```

**Test Servo:**
```python
import pigpio
import time

pi = pigpio.pi()
SERVO_PIN = 12

# Center position
pi.set_servo_pulsewidth(SERVO_PIN, 1500)
time.sleep(1)

# Sweep test
for pw in range(1000, 2000, 100):
    pi.set_servo_pulsewidth(SERVO_PIN, pw)
    time.sleep(0.2)

pi.set_servo_pulsewidth(SERVO_PIN, 0)  # Off
pi.stop()
```

---

## Troubleshooting

### Common Issues

#### Camera Not Detected
```bash
# Check camera connection
vcgencmd get_camera

# Should show: supported=1 detected=1

# Test camera
libcamera-hello -t 5000

# If not working:
sudo raspi-config  # Enable camera
sudo reboot
```

#### Microphone Not Working
```bash
# List audio devices
arecord -l

# Test recording
arecord -D hw:1,0 -f cd test.wav -d 5
aplay test.wav

# If not detected:
- Try different USB port
- Check USB device power
- Use powered USB hub
```

#### GPIO Permission Denied
```bash
# Add user to gpio group
sudo usermod -a -G gpio $USER
sudo reboot
```

#### Servos Jittering
- Use external power supply (not Pi's 5V)
- Add capacitor (1000µF) across servo power
- Use PCA9685 servo driver instead of direct GPIO
- Ensure common ground between Pi and servo power

#### I2C Not Working
```bash
# Check I2C enabled
ls /dev/i2c*  # Should show /dev/i2c-1

# Scan for devices
i2cdetect -y 1

# Enable I2C
sudo raspi-config  # Interface Options → I2C
```

#### Low FPS from Camera
- Reduce resolution in settings.yaml
- Use lighter face detection (Haar instead of MediaPipe)
- Disable unnecessary processing
- Overclock Pi (carefully)

#### Audio Latency
- Use smaller buffer sizes (chunk_size in settings.yaml)
- Use faster STT model (Whisper tiny instead of base)
- Consider hardware acceleration

### Performance Optimization

**For Better Performance:**

1. **Overclock Raspberry Pi 4:**
   ```bash
   sudo nano /boot/config.txt

   # Add:
   over_voltage=2
   arm_freq=1750
   gpu_freq=600
   ```

2. **Disable Desktop Environment:**
   ```bash
   sudo systemctl set-default multi-user.target
   sudo reboot
   ```

3. **Use Lightweight Models:**
   - Whisper: `tiny` instead of `base`
   - Ollama: `qwen2.5:0.5b` instead of larger models

4. **Optimize Camera:**
   - Lower resolution (640x480 instead of 1080p)
   - Reduce FPS if not needed

---

## Additional Resources

- [Raspberry Pi GPIO Guide](https://pinout.xyz/)
- [Pi Camera Documentation](https://www.raspberrypi.com/documentation/accessories/camera.html)
- [pigpio Library](http://abyz.me.uk/rpi/pigpio/)
- [Ollama Documentation](https://ollama.com/docs)
- [OpenCV Raspberry Pi](https://docs.opencv.org/4.x/d7/d9f/tutorial_linux_install.html)

---

## Safety Notes

- **Never connect 5V signals directly to GPIO pins** (use voltage dividers)
- **Use external power for motors/servos** (not Pi's 5V rail)
- **Ensure common ground** between Pi and all peripherals
- **Monitor temperature** (`vcgencmd measure_temp`)
- **Use heatsinks** on Pi CPU for sustained operation

---

## Support

For issues or questions:
1. Check logs: `data/logs/companion.log`
2. Run hardware tests: `python scripts/test_hardware.py`
3. Check systemd service: `sudo journalctl -u companion-bot -f`

---

**Last Updated:** November 2025
**Compatible with:** Raspberry Pi 4 Model B (4GB/8GB)
