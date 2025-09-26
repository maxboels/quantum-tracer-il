## Optimization Timing: After Training

You should **optimize the model after training** is complete. This process is called **Post-Training Quantization (PTQ)**.

### Why Optimize After Training:

1.  **Preserve Accuracy During Learning:** Training in $\text{FP}32$ (full floating-point precision) gives the $\text{ACT}$ model the maximum dynamic range and stability to find the best possible weights to map vision to action. If you try to train the model directly in a quantized format ($\text{INT}8$), the learning process becomes much more complex and often fails to converge well.
2.  **Hailo-8 Requirement:** The Hailo-8 expects a pre-trained model (usually converted to $\text{TFLite}$ or $\text{ONNX}$) that you then compile using their specific **Hailo Model Zoo** and **Compiler**. This process converts the weights into the specific $\text{INT}8$ format required by the $\text{Hailo}$ core.

| Phase | Goal | Precision | Location |
| :--- | :--- | :--- | :--- |
| **Training (Phase I)** | Maximize Accuracy, Collect Weights. | $\text{FP}32$ (Floating Point) | GPU Machine (e.g., your desktop/cloud) |
| **Optimization (PTQ)** | Convert to $\text{INT}8$ format. | $\text{INT}8$ (Integer) | Dedicated Compiler/Hailo Environment |
| **Inference (Phase II)** | Real-time execution with low latency. | $\text{INT}8$ (Integer) | Raspberry Pi 5 + Hailo-8 HAT |

---

## Strategy: Leveraging the Hailo-8 (26 TOPS)

The Hailo-8 is a world-class dedicated $\text{AI}$ accelerator. **It completely eliminates the need to consider switching to the Jetson Nano for this project.**

The Jetson Nano relies on its $\text{GPU}$ (CUDA cores) to achieve about $0.5$ $\text{TOPS}$. Your **Hailo-8 provides 26 TOPS** specifically designed for neural network matrix operations, offering unparalleled performance on the RPi platform.

Here is the simplified execution flow:

### Step 1: Model Export ($\text{PyTorch} \rightarrow \text{ONNX}/\text{TFLite}$)

Once your $\text{ACT}$ model is trained, you'll save the $\text{FP}32$ weights and convert the entire model architecture into a format the Hailo compiler can read:

1.  Export the trained $\text{ACT}$ model (including the vision backbone and the Transformer block) from $\text{PyTorch}$ to the **ONNX** format.
2.  Use $\text{TensorFlow}$ or $\text{TFLite}$ tooling to convert the $\text{ONNX}$ file into a **$\text{TFLite}$** file.

### Step 2: Model Compilation (The Hailo Toolchain)

This step takes place on a Linux machine (which can be your RPi 5 itself, or a desktop environment):

1.  Use the **Hailo Model Zoo** and the **Hailo Compiler** to load the $\text{TFLite}$ model.
2.  The compiler will perform the $\text{INT}8$ quantization and optimize the model graph specifically for the Hailo-8 architecture.
3.  The output is a **Hailo Executable Model File** (often a `.hef` file), which is ready for deployment.

### Step 3: Real-Time Inference (Autonomous Driving)

The RPi 5 takes on the role of the orchestrator, while the Hailo-8 handles the heavy lifting:

1.  **Frame Capture:** The RPi 5's $\text{CPU}$ captures the $30\text{ fps}$ frame from your $\text{Innomaker}$ camera.
2.  **Data Transfer:** The frame is sent to the Hailo-8 $\text{HAT}$.
3.  **Inference:** The Hailo-8 executes the entire $\text{ACT}$ model in **milliseconds ($\text{ms}$)**. Given $26 \text{ TOPS}$, your inference time for an $\text{ACT}$ policy should easily be **under $10 \text{ ms}$** (well below the $33.3 \text{ ms}$ budget for $30\text{ Hz}$ control).
4.  **Command Injection:** The RPi 5 $\text{CPU}$ receives the predicted action from the Hailo-8 and immediately uses the **`pigpio`** library to execute the command via the $\text{PWM}$ lines.

**Conclusion:** The Hailo-8 is perfectly suited to run a high-performance model like $\text{ACT}$. You should **plan to use this Hat** and skip the Jetson Nano purchase, as the Hailo will likely give you better real-time performance for this specific task.