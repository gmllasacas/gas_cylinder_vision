# Gas Tank Model Training Workflow (ZIP File Method)

This directory contains the training videos and tools to prepare your dataset for training custom YOLOv8 models (`best.pt`).

---

## 1. Directory Structure

```text
training/
├── videos/                   # Place all raw CCTV recordings here (.mp4, .avi)
│   └── A08_20260812190000_2min.mp4
├── dataset/                  # Generated extraction folder
│   └── raw_images/           # Extracted JPG frames ready for annotation
├── extract_frames.py         # Frame extraction script
└── README.md                 # This workflow guide
```

---

## 2. Extract Frames

Run the extraction script from your project root:

```bash
# Default extraction (1 frame every 1.5s):
python training/extract_frames.py

# Higher density sampling (1 frame every 1.0s):
python training/extract_frames.py --interval 1.0
```

---

## 3. Label & Export ZIP on Roboflow

1. Upload `.jpg` images from `training/dataset/raw_images/` to Roboflow.
2. Label the gas tanks (`gas_tank`).
3. Click **Export Dataset** -> Select **YOLOv8** -> Select **Download ZIP to computer**.
4. You will get a file like `gas_tank_dataset.zip`.

---

## 4. Google Colab Training with ZIP File (Free T4 GPU)

1. Open a new notebook on **[Google Colab](https://colab.research.google.com)**.
2. Set runtime to GPU: **Runtime > Change runtime type > T4 GPU**.
3. Run the following steps:

### Cell 1: Upload Your ZIP File & Install Ultralytics
```python
# 1. Install YOLOv8 library
!pip install -q ultralytics

# 2. Upload your downloaded zip file from your computer
from google.colab import files
uploaded = files.upload()

# 3. Unzip into dataset/ folder
!mkdir -p dataset
!unzip -q *.zip -d dataset/
!ls -la dataset/
```

*(Alternatively, you can simply drag & drop the `.zip` file into the left "Files" panel in Colab, then run `!unzip -q *.zip -d dataset/`)*

---

### Cell 2: Train YOLOv8 on GPU
```python
from ultralytics import YOLO
import os

# Find data.yaml path inside dataset/
data_yaml = "dataset/data.yaml"
if not os.path.exists(data_yaml):
    # Check if zipped inside a subfolder
    for root, dirs, files_list in os.walk("dataset"):
        if "data.yaml" in files_list:
            data_yaml = os.path.join(root, "data.yaml")
            break

print(f"Using configuration: {data_yaml}")

# Load base pre-trained model (yolov8n.pt is fastest, yolov8s.pt is slightly more accurate)
model = YOLO('yolov8n.pt')

# Train
results = model.train(
    data=data_yaml,
    epochs=100,          # 100 epochs is recommended for ~100-300 images
    imgsz=640,
    batch=16,
    device=0,            # Uses Colab T4 GPU
    patience=25,         # Early stopping if no improvement
    save=True,
    plots=True
)
```

---

### Cell 3: Download `best.pt` to Your Computer
```python
# Automatically trigger browser download for the trained best.pt
from google.colab import files

files.download('runs/detect/train/weights/best.pt')
```

---

## 5. Deploy to Your Local Project

1. Move the downloaded `best.pt` file to the `models/` directory:
   `d:\laragon_6\www\gas_stream\models\best.pt`
2. Start or reload your FastAPI application:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
3. Open `http://localhost:8000` to inspect live bounding box detections and tracking accuracy with the debug overlay!
