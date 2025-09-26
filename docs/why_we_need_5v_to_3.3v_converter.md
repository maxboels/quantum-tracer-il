That is the single most common source of confusion when interfacing high-power (RC car) systems with low-power (Raspberry Pi/Jetson) microcomputers!

You are mixing up two very different types of voltage, which is exactly why the **Logic Level Converter** is critical:

1.  **High Power/Battery Voltage:** $7.4\text{V}$ (LiPo/Li-Ion)
2.  **Digital Signal/Logic Voltage:** $5\text{V}$ and $3.3\text{V}$

Let me break down exactly why you need the converter, despite the RPi expecting a $5\text{V}$ power *input* and the car having a $5\text{V}$ component *internally*.

---

## The Difference Between Power and Signal

### 1. The Car's Electrical System (ESC/Receiver)

The RC car has three voltage stages:

* **Battery Power ($\mathbf{7.4\text{V}}$):** This is the raw energy source that powers the entire system. It goes directly to the ESC's power stage and then runs the motor.
* **BEC Regulator ($\mathbf{5\text{V}}$):** The ESC/Receiver board has a built-in regulator (called a Battery Eliminator Circuit, or BEC). This circuit takes the $7.4\text{V}$ and steps it down to a stable **$5\text{V}$**.
* **Digital Signal Logic ($\mathbf{5\text{V}}$):** The receiver chip and the servo driver chip use this stable **$5\text{V}$** to represent a logic $\text{HIGH}$. **The taps you soldered are on these $5\text{V}$ logic lines.**

### 2. The Raspberry Pi's Electrical System (RPi 5)

The Raspberry Pi has its own set of voltages:

* **Power Input ($\mathbf{5\text{V}}$):** The USB-C port expects a $5\text{V}$ power source (from your power bank) to run the entire computer.
* **GPIO Logic ($\mathbf{3.3\text{V}}$):** This is the critical point. The actual pins on the $\text{GPIO}$ header that read and write signals operate on a strictly **$3.3\text{V}$** standard. This is the maximum voltage the tiny semiconductor transistors inside the RPi's Broadcom chip can handle.

## Why $5\text{V}$ Signal $\rightarrow 3.3\text{V}$ Pin is Dangerous

When you connect the car's **$5\text{V}$ signal tap** directly to the RPi's **$3.3\text{V}$ $\text{GPIO}$ input pin**:

1.  The RPi expects the signal to be $\mathbf{0\text{V}}$ (LOW) or $\mathbf{3.3\text{V}}$ (HIGH).
2.  The car is sending a pulse that peaks at $\mathbf{5\text{V}}$.
3.  That $5\text{V}$ surge is **$1.7\text{V}$ higher** than the RPi's safe limit, overloading the internal chip structure and often leading to instantaneous, irreparable damage to that $\text{GPIO}$ pin, and sometimes the entire chip.

**The Logic Level Converter's Job:**

The level converter's sole job is to sit between these two standards. It sees the $5\text{V}$ pulse on one side and safely outputs an identical $3.3\text{V}$ pulse on the other side, allowing your RPi to read the data without frying its brain. 

| Side | Voltage | Connected To | Action |
| :--- | :--- | :--- | :--- |
| **HV (High Voltage)** | **$5\text{V}$** | Car's $\text{PWM}$ Signal Taps | *Receives* the signal *safely*. |
| **LV (Low Voltage)** | **$3.3\text{V}$** | RPi's $\text{GPIO}$ Pins | *Transmits* the translated signal *safely*. |

You are correct that both systems involve $5\text{V}$ *somewhere*, but the signal lines you tapped only need to interface with the RPi's $3.3\text{V}$ logic pins. The converter bridges that $\mathbf{1.7\text{V}}$ difference.