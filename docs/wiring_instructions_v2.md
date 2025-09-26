That is perfect! You ordered a great batch of **4-channel bi-directional level converters**, which gives you spares and exactly the tool you need for this job.

Since you are using the **Raspberry Pi 5** and now have the level converter, we can create the definitive, safe wiring guide for Phase I (Data Logging).

Here is the step-by-step connection guide for integrating the level converter into your setup.

---

## Safe Wiring Guide: Level Converter Integration

Your level converter has two sides: **HV (High Voltage / 5V)** and **LV (Low Voltage / 3.3V)**. Your goal is to connect the $\mathbf{5\text{V}}$ components (Car's signals) to the $\mathbf{HV}$ side and the $\mathbf{3.3\text{V}}$ components (Raspberry Pi's $\text{GPIO}$) to the $\mathbf{LV}$ side.

### I. Powering and Grounding the Converter

This step establishes the necessary voltage references for the translator chip to work.

| Step | Connection | Source Pin | Destination Pin | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **1. LV Power** | RPi $3.3\text{V}$ $\rightarrow$ **LV** | RPi **Pin 1** or **Pin 17** | Converter **LV** | Powers the low-voltage side of the translator. |
| **2. HV Power** | RPi $5\text{V}$ $\rightarrow$ **HV** | RPi **Pin 2** or **Pin 4** | Converter **HV** | Powers the high-voltage side. |
| **3. RPi Ground** | RPi $\text{GND}$ $\rightarrow$ Converter $\text{GND}$ | RPi **Pin 6** | Converter **GND** | Establishes the RPi's electrical reference. |
| **4. Car Ground** | Car $\text{GND}$ ($\text{Brown}$ 3-pin) $\rightarrow$ Converter $\text{GND}$ | Car **Brown (3-pin)** | Converter **GND** | **Crucial:** Creates a common ground between the car and RPi. |
| **5. Car VCC** | Car $5\text{V}$ VCC ($\text{Red}$ 3-pin) | Car **Red (3-pin VCC)** | **DO NOT USE THIS PIN!** | The converter is already powered by the RPi's $5\text{V}$ (Step 2). Connecting this pin is redundant and risky. |

### II. Signal Connections (Translation)

This step translates your two critical control signals into a safe format for the Raspberry Pi.

| Signal Tap | Converter **HV Side** (Input) | Converter **LV Side** (Output) | RPi $\text{GPIO}$ Pin ($\text{BCM}$ No.) |
| :--- | :--- | :--- | :--- |
| **Throttle (PWM Drive)** ($\mathbf{5\text{V}}$) | Car **Brown (soldered)** $\rightarrow$ **HV1** | **LV1** $\rightarrow$ RPi **BCM 23** | **BCM 23 (Pin 16)** |
| **Steering (PWM Servo)** ($\mathbf{5\text{V}}$) | Car **Green (soldered)** $\rightarrow$ **HV2** | **LV2** $\rightarrow$ RPi **BCM 18** | **BCM 18 (Pin 12)** |
| **Steering Signal** (Redundant) | Car **Yellow (3-pin)** | **Leave Disconnected** | **N/A** |

### Next Steps After Wiring

Once your level converter is wired:

1.  **Mount the Circuit:** Use a small breadboard and jumper wires (if you ordered them) to hold the converter securely and connect everything cleanly. 
2.  **Verify $\text{pigpio}$:** Ensure the $\text{pigpio}$ daemon is running on your Raspberry Pi: `sudo pigpiod`.
3.  **Run the Script:** Execute the `data_logging_example()` function in your `control_interface.py` file to begin recording expert commands for your ACT policy!