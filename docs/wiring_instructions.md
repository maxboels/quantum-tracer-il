That's an excellent question that clarifies the setup of your existing wiring harness! Your insight about keeping the original connection intact for data collection is spot on.

Based on the images you provided and the standard setup of $\text{RC}$ car electronics, here is the detailed explanation of those wires and how they should be connected to your newly ordered **Logic Level Converter** for safety and functionality.

---

## ESC Wire Identification and Function

The wires you listed come from two different places on the ESC/Receiver board: two were directly soldered taps for sensing/injecting signals, and three are part of the original, untouched steering servo connector.

### A. Soldered Taps (Signal Lines)

These wires are your interface for reading the **control commands** for your ACT policy.

| Wire Color | Confirmed Function | Connects to Level Converter Pin | Final Destination |
| :--- | :--- | :--- | :--- |
| **Green** | **PWM Servo (Steering Signal)** | **HV1** | RPi **BCM 18** (via LV1) |
| **Brown** | **PWM Drive (Throttle Signal)** | **HV2** | RPi **BCM 23** (via LV2) |

### B. Original 3-Pin Connector (Steering Servo)

These wires originally carried power and signal directly to the steering servo. You mentioned these were *split* (using a Y-harness or simply exposing the wires) but are still connected to the original harness.

| Wire Color | Function | Connection Use | Why it is CRITICAL |
| :--- | :--- | :--- | :--- |
| **Red** (3-pin) | **$5\text{V}$ VCC** (Regulated Power) | Connects to Converter **HV** pin. | **Powers the $5\text{V}$ side of the level converter.** This is where the converter draws the voltage it expects to see from the car's logic. |
| **Brown** (3-pin) | **GND** (Common Ground) | Connects to Converter **GND** pin. | **Establishes Common Ground.** This is the electrical reference point shared by the car, the converter, and the Raspberry Pi. |
| **Yellow** (3-pin) | **Steering Signal** (Redundant) | **Leave Disconnected.** | This wire carries the same $\text{PWM}$ signal as your **Green** tap. Connecting it twice is unnecessary. |

---

## II. Step-by-Step Wiring to the Logic Level Converter

Here is how all five wires connect to your new bi-directional level converter once it arrives.

### Step 1: Power the Converter (The $5\text{V}$ and $3.3\text{V}$ Sides)

The converter needs power from both systems to operate.

1.  **Converter $5\text{V}$ Side (HV):** Connect the **Red (3-pin VCC)** wire from the car's servo harness to the **HV** pin on the converter.
2.  **Converter $3.3\text{V}$ Side (LV):** Connect the RPi's **$3.3\text{V}$ pin** (e.g., Pin 1) to the **LV** pin on the converter.
3.  **Common Ground:** Connect the **Brown (3-pin $\text{GND}$) wire** from the car **AND** the RPi's **GND pin** (e.g., Pin 6) to the **GND** pin on the converter.

### Step 2: Connect the Signal Taps (Translation)

1.  **Steering Signal:**
    * Connect the **Green (soldered)** wire (PWM Servo) to the **HV1** pin.
    * Connect the corresponding **LV1** pin to RPi **BCM 18 (Pin 12)**.

2.  **Throttle Signal:**
    * Connect the **Brown (soldered)** wire (PWM Drive) to the **HV2** pin.
    * Connect the corresponding **LV2** pin to RPi **BCM 23 (Pin 16)**.

### Conclusion: Your Control Loop is Safe

Your instinct about keeping the original pins connected for data collection is correct. By tapping the signal lines, you are **non-intrusively listening** to the car's control logic. The original servo still receives the control signal, allowing the car to be driven manually while the Raspberry Pi simultaneously records the actions. When you switch to autonomy, the RPi will inject its signal, overriding the receiver.