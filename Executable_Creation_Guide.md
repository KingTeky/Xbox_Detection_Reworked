# Xbox Color Tracker - Executable Creation Guide

## ✅ Executable Creation Complete

**📁 Location:** `C:\Users\Cedan\OneDrive\Desktop\Projects_Depot\Experimental_Code\LIVE_TestingGrounds`

**📦 Executable Name:** `Console_Detection_Live_TEST.exe`

**📊 File Size:** ~444 MB (includes all dependencies)

## 🔧 PyInstaller Command Used

The command used to create the standalone executable was:

```bash
pyinstaller --onefile --windowed --name "Console_Detection_Live_TEST" --distpath "C:\Users\Cedan\OneDrive\Desktop\Projects_Depot\Experimental_Code\LIVE_TestingGrounds" --add-data "yolov8n.pt;." --add-data "All_icons_pngs;All_icons_pngs" --icon="All_icons_pngs\KT_OD_App_iconV6.png" --hidden-import=vgamepad --hidden-import=inputs --hidden-import=ultralytics --hidden-import=mss --hidden-import=PIL --hidden-import=numpy --hidden-import=pygetwindow --hidden-import=psutil --collect-all=ultralytics Main_color_tracker.py
```

### Command Parameters Explained:
- **`--onefile`**: Creates a single executable file with all dependencies bundled
- **`--windowed`**: Runs without a console window (GUI application)
- **`--name "Console_Detection_Live_TEST"`**: Sets the executable name
- **`--distpath "..."`**: Specifies the output directory for the executable
- **`--add-data "yolov8n.pt;."`**: Includes the YOLO model file in the executable
- **`--add-data "All_icons_pngs;All_icons_pngs"`**: Includes all icon files in the executable
- **`--icon="All_icons_pngs\KT_OD_App_iconV6.png"`**: Sets the executable icon
- **`--hidden-import=...`**: Ensures specific libraries are included even if not detected automatically
- **`--collect-all=ultralytics`**: Includes all ultralytics submodules and data files

## 📋 Key Features Included

The executable includes the following key features:

### 🎯 Detection Capabilities
- **Color Detection**: Advanced HSV-based color tracking with adjustable tolerance
- **YOLO Object Detection**: YOLOv8n model for person detection and tracking
- **Multi-source Input**: Monitor capture, window capture, and capture card support

### 🎮 Controller Integration
- **Xbox Controller Input**: Real-time controller monitoring and input processing
- **Virtual Controller Output**: ViGEmBus-based virtual controller simulation
- **Automatic Reconnection**: Smart controller reconnection and error handling

### 🖥️ User Interface
- **Intuitive GUI**: Tkinter-based interface with real-time preview
- **System Monitoring**: Memory and CPU usage tracking
- **Status Logging**: Comprehensive logging system with timestamps

## 🚀 What's Included

The executable contains all dependencies from the requirements.txt file:

### 📦 Core Libraries
- **OpenCV** (`opencv-python==4.11.0.86`): Computer vision processing
- **YOLO/Ultralytics** (`ultralytics==8.2.35`): Object detection model
- **NumPy** (`numpy==1.26.4`): Numerical computing
- **PIL/Pillow** (`pillow==11.2.1`): Image processing

### 🎮 Gaming Libraries
- **inputs** (`inputs==0.5`): Xbox controller input handling
- **vgamepad** (`vgamepad==0.1.0`): Virtual controller output
- **PyAutoGUI** (`PyAutoGUI==0.9.54`): Additional automation support

### 🖥️ System Libraries
- **tkinter**: GUI framework (built into Python)
- **mss** (`mss==10.0.0`): Screen capture
- **PyGetWindow** (`PyGetWindow==0.0.9`): Window management
- **psutil** (`psutil==7.0.0`): System monitoring

### 🧠 AI/ML Libraries
- **torch** (`torch==2.3.1`): PyTorch deep learning framework
- **torchvision** (`torchvision==0.18.1`): Computer vision utilities
- **supervision** (`supervision==0.21.0`): Object detection utilities

### 📊 Data Processing
- **pandas** (`pandas==2.2.2`): Data manipulation
- **matplotlib** (`matplotlib==3.9.0`): Plotting and visualization
- **scipy** (`scipy==1.13.1`): Scientific computing

## 💡 Usage Notes

### 🚀 Running the Application
1. **Double-click** `Console_Detection_Live_TEST.exe` to launch
2. **No Python installation required** on the target machine
3. **No additional dependencies** need to be installed

### ⚠️ Important Requirements
Despite being a standalone executable, some system-level dependencies are still required:

#### 🔧 Driver Dependencies
- **ViGEmBus Driver**: Required for virtual controller functionality
  - The application includes automatic driver detection and installation prompts
  - Manual installation: Download from official ViGEmBus releases
- **Xbox Controller Drivers**: Required for physical controller input
  - Usually installed automatically by Windows
  - Can be manually installed via Device Manager

#### 🎯 YOLO Model
- **YOLOv8n Model**: The `yolov8n.pt` file is embedded in the executable
- **No separate download required**
- **Automatic model loading** on first run

### 🎮 Controller Setup
1. **Connect Xbox Controller**: Via USB or wireless
2. **Install ViGEmBus**: Follow prompts if not already installed
3. **Test Controller**: Use the application's controller status indicator

### 📱 Supported Video Sources
- **Monitor Capture**: Any connected monitor
- **Window Capture**: Specific application windows (e.g., Xbox Remote Play)
- **Capture Card**: USB capture devices (Elgato, etc.)

### 🔍 Detection Modes
- **Color Detection**: Track specific colors with adjustable tolerance
- **YOLO Detection**: Detect and track people using AI
- **Hybrid Mode**: Switch between modes as needed

## 🛠️ Troubleshooting

### 🚨 Common Issues
1. **Controller not detected**: Check driver installation
2. **No video capture**: Verify video source selection
3. **High CPU usage**: Adjust capture interval settings
4. **Memory warnings**: Monitor system resources in the application

### 📞 Support
- Check the status log within the application for detailed error messages
- Ensure all required drivers are properly installed
- Verify controller connectivity before use

## 📈 Performance Specifications

### 💻 System Requirements
- **OS**: Windows 10/11 (64-bit)
- **RAM**: 8GB minimum (16GB recommended)
- **CPU**: Multi-core processor recommended
- **Storage**: 500MB free space for executable

### ⚡ Performance Features
- **Optimized Frame Processing**: Adjustable capture intervals
- **Memory Management**: Automatic garbage collection
- **Multi-threading**: Separate threads for detection and UI
- **Resource Monitoring**: Real-time system usage tracking

---

*Generated on: July 11, 2025*
*Executable Version: Console_Detection_Live_TEST.exe*
*PyInstaller Version: 6.8.0*
