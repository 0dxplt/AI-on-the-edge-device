# AI on the Edge - Auto Calibration API

This tool provides an automated, machine-learning-driven backend to calibrate "AI on the Edge" ROIs and Alignment Markers.

Instead of manually drawing bounding boxes (ROIs) on the web interface, this FastAPI server receives a raw image from the ESP32, uses a custom **YOLOv8** model to detect digits, analog dials, and alignment markers, and automatically pushes the newly generated `config.ini` and reference images back to the ESP32 SD card.

## 🏗️ System Overview & Architecture Flow

The system is completely plug-and-play. It dynamically fetches your current configurations from the ESP32-CAM, updates the coordinates based on AI vision, and syncs everything back securely.

1. **Capture**: The ESP32 takes a picture (with flashlight) and sends it via HTTP POST to this server.
2. **Config Download**: The server automatically connects to the ESP32 and downloads the current `config.ini` to preserve your existing Wi-Fi, MQTT, and system settings.
3. **Inference (YOLO)**: The server saves the image and passes it to the YOLOv8 model.
4. **Data Extraction & Config Update**: Bounding boxes for digits and analog dials are extracted. Alignment markers are located, and image crops (`ref0.jpg`, `ref1.jpg`) are generated. The downloaded `config.ini` is parsed and updated with the exact coordinates.
5. **Synchronization**: The updated `config.ini`, the cropped markers, and the full reference image are pushed back to the ESP32 via its hidden `/upload` API endpoint.
6. **Reboot**: A 3-second delay ensures SD card persistence, followed by an automated `/reboot` command sent to the ESP32 to load the new config.

## 📁 Directory Structure

The project structure is organized under `tools/auto-calibration`:

```text
tools/auto-calibration/
├── .gitignore             # Git ignore file for venv, caches, and images
├── best.pt                # YOLOv8 trained weights
├── file_manager.py        # Handles downloading/uploading files via HTTP to the ESP32
├── guide.md               # This documentation file
├── image_processor.py     # YOLO inference, image cropping, and config.ini parsing/updating
├── requirements.txt       # Python dependencies
├── .env.example           # Venv example file
└── server.py              # FastAPI application entry point
```

*(Note: standard Python directories like `venv` and `__pycache__` are excluded from version control, alongside auto-generated `imgs/` and `config/` folders created during execution).*

## 🧠 YOLO Training via Roboflow

To replicate the model training:

1. Gather images of your target meter.
2. Upload the dataset to [Roboflow](https://roboflow.com/).
3. Annotate 3 distinct classes:
   * `digit` (the mechanical rotating numbers)
   * `analog` (the red spinning dials)
   * `marker` (fixed text or logos on the meter used for software alignment)
4. Export the dataset in **YOLOv8 format**.
5. Train the model using the Ultralytics library (e.g., via Google Colab).
6. Download the `best.pt` file from the `runs/detect/weights/` directory and place it in the root of this project.

You could also improve the dataset used for this version at [Dataset](https://universe.roboflow.com/simone-castelli/water-meter-rzq0y)

## 🚀 Setup & Execution Guide

### 1. Prerequisites

* Python 3.9+
* Your ESP32-CAM must be initialized with the base AI on the Edge firmware, connected to your local Wi-Fi, and accessible via its IP address.

### 2. Installation

Clone the repository and navigate to the tools directory:

```bash
git clone https://github.com/0dxplt/AI-on-the-edge-device.git
cd AI-on-the-edge-device/tools/auto-calibration
```

Create a virtual environment and install the required dependencies:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Server Configuration

Write the `.env` based on the `.env.example` file.

### 4. Running the Server

Start the server using Python. It will automatically read the port from your `.env` file (default is 8000) and listen for incoming requests:

```bash
python server.py
```

### 5. Triggering the Calibration

Open the "Ai on the Edge" web interface running on your ESP32-CAM, hover on to the `Settings` list and choose the `Automatic ROIS` option.

The server will automatically fetch the ESP32 config, process the image, write the new parameters, upload the updated files, and trigger the device reboot. Check your terminal output for real-time logs of the synchronization process!
