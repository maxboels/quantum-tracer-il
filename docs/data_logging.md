## Arduino-Based Data Collection Setup

**Updated Architecture:** This project now uses an Arduino-based approach for more reliable PWM signal reading:

1. **Arduino UNO R3**: Reads PWM signals directly from ESC/Receiver on pins 2 & 3
2. **Raspberry Pi 5**: Receives data from Arduino via USB serial + handles camera capture

**No more direct GPIO PWM reading or pigpiod daemon needed!**

### Current Setup Requirements

**Hardware:**
- Arduino UNO R3 connected to RC car's ESC/Receiver PWM signals
- USB cable connecting Arduino to Raspberry Pi  
- Camera connected to Raspberry Pi
- No logic level converter needed (Arduino handles 5V PWM directly)

**Software:**
- `pwm_recorder.ino` uploaded to Arduino
- `integrated_data_collector.py` on Raspberry Pi

### Next Step: Test the Arduino-Raspberry Pi Connection

1.  **Check Arduino Connection:** Verify Arduino is connected via USB:

    ```bash
    ls /dev/ttyUSB* /dev/ttyACM*
    ```

2.  **Test Arduino Data Stream:** Check that Arduino is sending PWM data:

    ```bash
    python3 -c "
    import serial
    import time
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)  # Adjust port as needed
    time.sleep(2)
    print('Listening for Arduino data...')
    for i in range(10):
        line = ser.readline().decode('utf-8').strip()
        if line:
            print(line)
    ser.close()
    "
    ```

3.  **Run Data Collection:** Start recording episodes:

    ```bash
    # Record a 60-second episode
    python3 src/record/integrated_data_collector.py --episode-duration 60
    ```

### Expected Arduino Data Output

While the Arduino data collection is running, you should see PWM data like this:

```
DATA,4001,0.0723,0.1525,1528,108,21296,1012
DATA,4035,0.0496,0.1525,1516,108,21292,1012
DATA,4068,0.0723,0.1525,1528,108,21296,1012
```

**Data Format:** `DATA,timestamp,steering_normalized,throttle_normalized,steering_raw_us,throttle_raw_us,steering_period_us,throttle_period_us`

### What to Test and Verify

Move your RC transmitter controls to verify the data:

| Action | Expected Steering | Expected Throttle |
| :--- | :--- | :--- |
| **Steering Wheel Center** | Normalized: ≈ **0.00** | Normalized: **0.00** |
| **Steering Wheel Full Right** | Normalized: ≈ **+1.00** | Normalized: **0.00** |
| **Steering Wheel Full Left** | Normalized: ≈ **-1.00** | Normalized: **0.00** |
| **Throttle Forward** | Normalized: ≈ **0.00** | Normalized: ≈ **0.50-1.00** |

Once you see these numbers tracking your physical movements accurately in the Arduino serial data, you have successfully implemented the PWM capture system! The integrated data collector will synchronize this with camera frames for training data.