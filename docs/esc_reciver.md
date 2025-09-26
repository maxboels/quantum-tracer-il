# FTX Tracer Truggy Autonomy Project: ESC/Receiver Specifications

This consolidated sheet contains all confirmed technical specifications for the FTX Tracer Truggy's integrated board and precise wiring instructions for connecting it to your Raspberry Pi for command reading and autonomous control.

## Overview

This document provides three structured sections covering:
- **General Hardware Specifications**
- **Control Signal Characteristics** 
- **Detailed Wiring Pinout**

All parameters are derived from product data and oscilloscope analysis for the **FTX Tracer ESC/Receiver (Part No: FTX9731)**.

---

## I. General Hardware and Power Specifications

| Specification | Value | Technical Detail |
|:---|:---|:---|
| **Integrated Board** | FTX9731 (Brushed ESC/Receiver) | Combines radio receiver, speed controller, and servo driver |
| **Main Power Source** | 7.4V (2S Li-Ion/LiPo) | Voltage used to drive the motor and power the entire system |
| **Motor Type** | RC390 Brushed | Type of motor controlled by the ESC (explains the high PWM frequency) |
| **Control Logic Voltage** | **≈5V** (Inferred) | Voltage level of the PWM signal taps (requires level shifting) |
| **Radio System** | 2.4 GHz | Standard RC control frequency |

---

## II. Control Signal Characteristics (Action Space Parameters)

These are the precise PWM parameters that must be used by the **`RCReader` class** for data logging and the **`set_control_commands`** function for autonomous driving.

| Signal | Control Mechanism | Frequency | Neutral/Stop | Full Range |
|:---|:---|:---|:---|:---|
| **Steering (PWM Servo)** | **Pulse Width** (μs) | ≈47 Hz | 1491μs (≈7.0% Duty) | 1065μs (Left) → 1959μs (Right) |
| **Throttle (PWM Drive)** | **Duty Cycle** (%) | ≈985 Hz | 0% Duty | 0% (Stop) → 70% (Full Forward) |

### Key Signal Notes:
- **Steering**: Standard RC servo signal with pulse width modulation
- **Throttle**: High-frequency PWM for brushed motor control
- **Frequency difference**: Steering uses standard 50Hz RC frequency, while throttle uses high-frequency for motor control

---

## III. Raspberry Pi Wiring Pinout (Via Level Shifter)

These connections use the taps on the integrated PCB and a **5V ↔ 3.3V Logic Level Converter** for safety.

| Car PCB Tap (HV Side) | Logic Level Converter | Raspberry Pi GPIO (LV Side) | RPi Physical Pin | Python Script Variable |
|:---|:---|:---|:---|:---|
| **GND** | → **GND** → | **GND** | **Pin 6** | N/A |
| **PWM Servo** (Steering) | **HV Input** → **LV Output** → | **BCM 18** | **Pin 12** | `STEERING_PIN_GPIO` |
| **PWM Drive** (Throttle) | **HV Input** → **LV Output** → | **BCM 23** | **Pin 16** | `THROTTLE_PIN_GPIO` |

### Wiring Safety Notes:
- **⚠️ CRITICAL**: Always use a logic level converter - direct connection will damage the Raspberry Pi
- **Ground connection**: Essential for signal integrity and safety
- **Signal isolation**: The level converter provides electrical isolation between 5V car systems and 3.3V RPi
- **Pin verification**: Double-check BCM vs Physical pin numbering in your connections

### Connection Verification:
1. **Measure voltages** before connecting to RPi
2. **Test level converter** with multimeter
3. **Verify ground continuity** across all systems
4. **Check signal integrity** with oscilloscope if available