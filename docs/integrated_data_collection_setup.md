# RC Car Data Collection Setup Instructions

## Architecture Overview

**Current Setup:** Arduino-based PWM reading with Raspberry Pi data coordination

- **Arduino UNO R3**: Reads PWM signals directly from ESC/Receiver, sends via USB serial
- **Raspberry Pi**: Receives Arduino data + captures camera frames + coordinates episode recording
- **No direct GPIO PWM reading** - Arduino handles all PWM signal processing

## Hardware Setup

### Arduino UNO R3 Connections
```
ESC/Receiver -> Arduino
Steering PWM  -> Pin 2 (Digital, Interrupt capable)
Throttle PWM  -> Pin 3 (Digital, Interrupt capable) 
GND          -> GND
+5V          -> 5V (if needed for power)
```

### Raspberry Pi Connections
- USB Camera (or CSI camera)
- USB connection to Arduino UNO R3 (for data)
- Power supply

**Note:** No logic level converter needed - Arduino handles 5V PWM signals directly.

## Software Requirements

### Python Packages
```bash
pip install opencv-python pyserial pandas matplotlib numpy
```

### Arduino IDE
- Install Arduino IDE on your computer
- Upload `enhanced_pwm_recorder.ino` to Arduino UNO R3

## Quick Start Guide

### 1. Prepare Arduino
1. Connect PWM signals from ESC/Receiver to Arduino pins 2 and 3
2. Upload `enhanced_pwm_recorder.ino` to Arduino
3. Connect Arduino to Raspberry Pi via USB

### 2. Test Arduino Connection
```bash
# Check if Arduino is detected
ls /dev/ttyUSB* /dev/ttyACM*

# Test serial communication
python3 -c "
import serial
import time
ser = serial.Serial('/dev/ttyUSB0', 115200)  # Adjust port
time.sleep(2)
for i in range(10):
    line = ser.readline().decode('utf-8').strip()
    print(line)
ser.close()
"
```

### 3. Test Camera
```bash
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
if ret:
    print('Camera OK:', frame.shape)
else:
    print('Camera failed')
cap.release()
"
```

### 4. Record Episodes
```bash
# Start data collection
python3 integrated_data_collector.py --episode-duration 60 --output-dir ./episodes

# With custom settings
python3 integrated_data_collector.py \
    --episode-duration 30 \
    --output-dir ./training_episodes \
    --arduino-port /dev/ttyUSB0 \
    --camera-id 0
```

### 5. Analyze Data
```bash
# Analyze single episode
python3 episode_analyzer.py --episode-dir ./episodes/episode_20250927_143022 --plots --video

# Multi-episode summary
python3 episode_analyzer.py --episodes-dir ./episodes --summary
```

## Data Format

### Episode Structure
```
episodes/
├── episode_20250927_143022/
│   ├── episode_data.json      # Complete metadata
│   ├── control_data.csv       # Control signals from Arduino
│   ├── frame_data.csv         # Frame timestamps and paths
│   ├── training_data.npz      # Synchronized training data
│   ├── preview.mp4            # Video preview with overlays
│   └── frames/                # Individual frame images
│       ├── frame_000001.jpg
│       ├── frame_000002.jpg
│       └── ...
```

### Control Data Format (CSV)
```csv
arduino_timestamp,system_timestamp,steering_normalized,throttle_normalized,steering_raw_us,throttle_raw_us,steering_period_us,throttle_period_us
1234,1727123456.789,-0.1234,0.5678,1400,1600,20000,20000
```

### Synchronized Training Data (NPZ)
```python
import numpy as np
data = np.load('training_data.npz')
# data['timestamps']   # Frame timestamps
# data['frame_paths']  # Image file paths
# data['steering']     # Normalized steering [-1, 1]
# data['throttle']     # Normalized throttle [0, 1]
```

## Calibration

### PWM Signal Calibration
The Arduino code includes these calibration constants:

```cpp
const unsigned long STEERING_NEUTRAL_US = 1491;  // Neutral position
const unsigned long STEERING_RANGE_US = 450;     // Full range from neutral
const float THROTTLE_MAX_DUTY = 70.0;            // Maximum throttle duty cycle
```

Adjust these values based on your specific ESC/Receiver:

1. Record some PWM data with controls at known positions
2. Identify neutral/min/max values
3. Update constants in Arduino code
4. Re-upload to Arduino

### Data Rate Tuning
- Target: 30 Hz for both control and camera data
- Arduino samples at 30 Hz (33.33ms intervals)
- Camera captures at 30 FPS
- Adjust `SAMPLE_RATE_MS` in Arduino code if needed

## Troubleshooting

### Arduino Issues
- Check serial port permissions: `sudo usermod -a -G dialout $USER`
- Verify PWM connections with oscilloscope or logic analyzer
- Test with Arduino Serial Monitor first

### Camera Issues
- Check camera permissions: `sudo usermod -a -G video $USER`
- Try different camera IDs: `--camera-id 1`
- Verify camera with: `v4l2-ctl --list-devices`

### Synchronization Issues
- Ensure both systems use same time reference
- Check for USB latency issues
- Monitor data rates with analyzer tool

### Low Frame Rates
- Reduce camera resolution in code
- Check USB bandwidth (use USB 3.0 if available)
- Optimize frame compression settings

## Data Quality Checklist

### Good Episode Characteristics
- ✅ Control rate: 25-35 Hz
- ✅ Frame rate: 25-35 FPS  
- ✅ Duration: Target ± 2 seconds
- ✅ Control activity: > 20% of episode
- ✅ Signal range: Steering ±0.8, Throttle 0.0-0.8
- ✅ No missing frame sequences > 1 second

### Episode Validation
```bash
# Quick quality check
python3 episode_analyzer.py --episode-dir ./episodes/episode_YYYYMMDD_HHMMSS
```

Look for:
- Consistent data rates
- Reasonable control signal ranges
- Complete frame sequences
- Proper synchronization between control and camera data