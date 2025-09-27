# System Architecture - RC Car Imitation Learning

## Current Architecture (Updated Setup)

### Data Flow Overview
```
RC Transmitter → ESC/Receiver → Arduino UNO R3 → USB Serial → Raspberry Pi
                                                            ↓
                                Camera → Raspberry Pi → Synchronized Episodes
```

### Hardware Components

**Arduino UNO R3:**
- **Purpose**: PWM signal acquisition and preprocessing
- **Inputs**: 
  - Pin 2: Throttle PWM (900Hz, 0-70% duty cycle)
  - Pin 3: Steering PWM (50Hz, 5-9.2% duty cycle)
- **Output**: USB Serial at 115200 baud
- **Firmware**: `pwm_recorder.ino`

**Raspberry Pi:**
- **Purpose**: Data coordination, camera capture, episode management
- **Inputs**: 
  - USB Serial from Arduino (control data)
  - USB/CSI Camera (visual data)
- **Output**: Synchronized training episodes
- **Software**: `integrated_data_collector.py`

### Key Advantages

1. **Reliable PWM Reading**: Arduino's hardware interrupts provide precise PWM timing
2. **5V Compatibility**: Arduino handles 5V PWM signals directly (no level converter needed)
3. **Synchronized Data**: Raspberry Pi coordinates timestamps between control and camera data
4. **Scalable**: Easy to add more sensors or modify PWM processing on Arduino

## Software Architecture

### Arduino Firmware (`pwm_recorder.ino`)
- Hardware interrupt-based PWM measurement
- 30Hz synchronized data output
- CSV-format serial communication
- Built-in signal validation and normalization

### Raspberry Pi Scripts

**Primary Data Collection:**
- `integrated_data_collector.py` - Main episode recording system
- `episode_analyzer.py` - Data quality analysis and visualization

**Debugging/Testing:**
- `arduino_range_tester.py` - PWM range calibration
- `interactive_calibration.py` - Interactive calibration tool

## Deprecated Components

**⚠️ No longer used:**
- Direct GPIO PWM reading (`data_logger.py`, `control_*.py`)
- pigpio daemon requirement
- Logic level converters for PWM signals
- Raspberry Pi GPIO pins 18 & 23 for PWM input

## Data Format

### Arduino Serial Output
```
DATA,timestamp,steering_normalized,throttle_normalized,steering_raw_us,throttle_raw_us,steering_period_us,throttle_period_us
```

### Episode Structure
```
episodes/episode_YYYYMMDD_HHMMSS/
├── episode_data.json          # Metadata and configuration
├── control_data.csv           # Arduino PWM data with timestamps
├── frame_data.csv             # Camera frame metadata
├── frames/                    # Individual frame images
│   ├── frame_0000.jpg
│   ├── frame_0001.jpg
│   └── ...
└── training_data.npz          # Synchronized training format
```

## Quick Start

1. **Upload Arduino firmware**:
   ```bash
   # Upload pwm_recorder.ino to Arduino UNO R3
   ```

2. **Test Arduino connection**:
   ```bash
   ls /dev/ttyUSB* /dev/ttyACM*
   python3 -c "import serial; s=serial.Serial('/dev/ttyUSB0', 115200); print([s.readline().decode().strip() for _ in range(5)])"
   ```

3. **Record episodes**:
   ```bash
   python3 src/record/integrated_data_collector.py --episode-duration 60
   ```

4. **Analyze data**:
   ```bash
   python3 src/record/episode_analyzer.py --episode-dir ./episodes/episode_* --plots
   ```