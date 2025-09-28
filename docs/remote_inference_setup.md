# Remote Inference Setup - RC Car Autonomous Driving

This system allows you to run ML inference on your laptop's GPU while collecting sensor data and controlling the RC car from the Raspberry Pi over WiFi.

## Architecture Overview

```
RC Car ← Arduino ← USB → Raspberry Pi ←→ WiFi ←→ Laptop (GPU) 
   ↑                            ↑                    ↑
 PWM Control              Camera + Sensors      ML Inference
```

**Data Flow:**
1. **Raspberry Pi** captures camera frames and Arduino sensor data
2. **WiFi Network** streams data to laptop and receives control commands  
3. **Laptop** runs GPU-accelerated ML inference on received data
4. **Control Commands** sent back to Pi → Arduino → RC Car

## Quick Start Guide

### 1. Laptop Setup (Inference Server)

**Install Dependencies:**
```bash
pip install torch torchvision opencv-python numpy
```

**Test Server Setup:**
```bash
cd /path/to/your/project
python3 src/network/network_setup.py --mode server --port 8888
```

**Start Inference Server:**
```bash
# With dummy model (for testing)
python3 src/network/remote_inference_server.py --port 8888 --dummy-model

# With trained model
python3 src/network/remote_inference_server.py --port 8888 --model-path ./trained_model.pth
```

### 2. Raspberry Pi Setup (Client)

**Update Arduino Firmware:**
Upload `enhanced_pwm_recorder_with_control.ino` to your Arduino to support control commands.

**Test Pi Setup:**
```bash
python3 src/network/network_setup.py --mode client --server-ip 192.168.1.100
```

**Start Remote Inference Client:**
```bash
python3 src/network/remote_inference_client.py --server-ip 192.168.1.100 --server-port 8888
```

### 3. Network Configuration

**Find Your Laptop's IP:**
```bash
# Linux/Mac
ip addr show  # or ifconfig

# Windows  
ipconfig
```

**Test Connectivity:**
```bash
# From Raspberry Pi, test connection to laptop
python3 src/network/network_setup.py --mode test --target-ip 192.168.1.100 --port 8888
```

## System Components

### 1. Arduino Firmware (`enhanced_pwm_recorder_with_control.ino`)

**Features:**
- Reads PWM signals from RC car (same as before)
- **NEW:** Accepts control commands via serial
- **NEW:** Outputs PWM control signals for autonomous driving
- Supports mode switching between manual and autonomous

**Control Commands:**
```
CTRL,<steering>,<throttle>  # Set control values (-1.0 to 1.0, 0.0 to 1.0)
MODE,AUTO                   # Switch to autonomous mode
MODE,MANUAL                 # Switch back to manual control  
STATUS                      # Get current status
```

### 2. Raspberry Pi Client (`remote_inference_client.py`)

**Responsibilities:**
- Capture camera frames at 30 FPS
- Read Arduino sensor data  
- Stream data to laptop via WiFi
- Receive and execute control commands
- Monitor system performance

**Key Features:**
- Low-latency frame streaming with JPEG compression
- Automatic reconnection handling
- Real-time performance statistics
- Graceful fallback to safe driving

### 3. Laptop Server (`remote_inference_server.py`)

**Responsibilities:**
- Receive camera frames and sensor data
- Run ML model inference on GPU
- Send control commands back to Pi
- Handle multiple clients (future expansion)

**Key Features:**
- PyTorch GPU acceleration
- Dummy model for testing without trained weights
- Performance monitoring and latency tracking
- Multi-threaded client handling

## Performance Considerations

### Network Requirements
- **WiFi:** 2.4GHz or 5GHz (5GHz preferred for lower latency)
- **Bandwidth:** ~2-5 Mbps for 30fps at 320x240 resolution
- **Latency:** Target <100ms end-to-end (camera → prediction → control)

### Optimization Tips
1. **Reduce Frame Size:** Lower resolution = less network usage
2. **Adjust JPEG Quality:** Balance compression vs quality
3. **GPU Memory:** Ensure laptop has sufficient VRAM
4. **WiFi Proximity:** Keep Pi and laptop close to router

## Usage Examples

### Testing Without Trained Model
```bash
# Laptop: Start dummy server
python3 src/network/remote_inference_server.py --dummy-model

# Raspberry Pi: Connect and test
python3 src/network/remote_inference_client.py --server-ip 192.168.1.100
```

### Production Use with Trained Model
```bash
# Laptop: Load your trained model
python3 src/network/remote_inference_server.py --model-path ./my_model.pth

# Raspberry Pi: Start autonomous driving
python3 src/network/remote_inference_client.py --server-ip 192.168.1.100
```

### Development and Debugging
```bash
# Test network connectivity
python3 src/network/network_setup.py --mode test --target-ip 192.168.1.100

# Check hardware on Pi
python3 src/network/network_setup.py --mode client --server-ip 192.168.1.100
```

## Troubleshooting

### Common Issues

**1. "Connection refused"**
- Check laptop IP address
- Verify server is running
- Check firewall settings

**2. "Arduino not responding"**
- Upload latest firmware with control support
- Check USB cable connection
- Verify Arduino port (/dev/ttyACM0 vs /dev/ttyUSB0)

**3. "Camera not available"**
- Check camera connection
- Test with `lsusb` or `v4l2-ctl --list-devices`
- Try different camera ID (0, 1, 2...)

**4. High latency**
- Move closer to WiFi router
- Switch to 5GHz WiFi band
- Reduce frame resolution
- Close other network applications

### Safety Features

**Automatic Failsafe:**
- If network connection lost → Arduino returns to manual control
- If server stops responding → Safe driving mode activated
- Emergency stop command always available

**Manual Override:**
- Physical RC transmitter always takes priority
- Arduino firmware supports immediate mode switching
- Control commands have timeout protection

## File Structure

```
src/network/
├── remote_inference_client.py      # Raspberry Pi client
├── remote_inference_server.py      # Laptop server  
├── network_setup.py                # Setup and testing utilities
└── enhanced_pwm_recorder_with_control.ino  # Arduino firmware

docs/
└── remote_inference_setup.md       # This documentation
```

## Advanced Configuration

### Custom Model Integration

To integrate your own trained model, modify the `PyTorchModel` class in `remote_inference_server.py`:

```python
def _load_model(self, model_path: str):
    # Load your specific model architecture
    model = YourModelClass()
    model.load_state_dict(torch.load(model_path))
    model.eval()
    return model

def predict(self, frame: np.ndarray, sensor_data: Dict) -> Tuple[float, float, float]:
    # Implement your model's inference logic
    # Return: steering (-1 to 1), throttle (0 to 1), confidence (0 to 1)
    pass
```

### Performance Monitoring

Both client and server provide real-time statistics:
- Frame rate and bandwidth usage
- Inference latency and GPU utilization  
- Network connection quality
- Control command success rate

## Next Steps

1. **Test the system** with dummy model first
2. **Train your model** using collected episode data
3. **Integrate your model** into the server
4. **Fine-tune performance** for your network setup
5. **Scale to multiple cars** using the same server

This networked architecture gives you the flexibility to leverage powerful desktop/laptop hardware while maintaining real-time control of your RC car!