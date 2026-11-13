# AI Smart Dustbin

An AI-enabled waste-sorting prototype that uses a camera and a YOLO
model to classify waste, an Arduino Uno to control two servo-driven
lids, and three ultrasonic sensors for distance monitoring.

> **Project status:** Prototype integration in progress. The AI webcam
> detection, motor command communication, individual motor operation,
> and standalone ultrasonic sensor readings have been tested. Full
> simultaneous integration of the webcam, both motors, and all three
> ultrasonic readings still needs final verification.

## 1. Project overview

### Intended behavior

  Detected object   Intended action
  ----------------- --------------------------
  Paper             Motor 1 turns to 90°
  Plastic           Motor 2 turns to 90°
  `home` command    Both motors return to 0°

The physical concept uses a bin with **two independently opening and
closing lids**. The current temporary CAD proposal leaves the front
panel solid. A display/screen and its cutout are **not included yet**,
because the display hardware is not currently available.

## 2. Current project status

### Hardware status

  -----------------------------------------------------------------------
  Component               Current configuration / Status
                          connection              
  ----------------------- ----------------------- -----------------------
  Jetson Nano             Runs Python, OpenCV,    Used for AI application
                          and YOLO webcam         
                          application             

  Arduino Uno             USB serial connection   Tested for serial
                          to Jetson Nano; 9600    communication
                          baud                    

  Motor 1                 MG995 servo, signal on  Individual movement
                          Arduino D10             tested; AI command path
                                                  tested

  Motor 2                 9g servo, signal on     Individual movement
                          Arduino D3              tested; AI command path
                                                  tested

  Ultrasonic sensor 1     TRIG D4, ECHO D5        Distance readings
                                                  observed

  Ultrasonic sensor 2     TRIG D6, ECHO D7        Distance readings
                                                  observed

  Ultrasonic sensor 3     TRIG D8, ECHO D9        Distance readings
                                                  observed

  USB webcam              Camera index 0 in       Webcam feed and object
                          Python test             detection tested

  Breadboard              Used for prototype      In use; exact physical
                          wiring                  dimensions not measured

  Display                 Not currently available Not installed; no
                                                  display cutout in
                                                  temporary CAD
  -----------------------------------------------------------------------

**Observed ultrasonic test readings** (sample values from the bench
test, not accuracy specifications):

-   S1: approximately 5.2--8.8 cm
-   S2: approximately 7.4--8.4 cm
-   S3: approximately 3.9--5.2 cm

The readings changed during testing. Recheck at known distances such as
10 cm, 20 cm, and 30 cm before relying on them for bin-full detection.

### Software status

  -----------------------------------------------------------------------
  Software / module       Purpose                 Status
  ----------------------- ----------------------- -----------------------
  Python 3                Main application on     In use
                          Jetson Nano             

  OpenCV (`cv2`)          Webcam capture and      Webcam test passed
                          display                 

  Ultralytics YOLO        Waste object detection  Model loads and detects
                                                  paper/plastic

  PySerial                USB serial              Installed in Python
                          communication with      virtual environment
                          Arduino                 

  Arduino sketch          Reads serial commands,  Individual motor
                          controls servos, reads  commands and standalone
                          ultrasonic sensors      sensor output tested

  Combined Python webcam  Detects waste and sends Paper/plastic
  application             motor commands          detections and Arduino
                                                  ACK responses observed;
                                                  sensor text in webcam
                                                  was still showing
                                                  `Sensors: waiting...`
                                                  in the last shared test
  -----------------------------------------------------------------------

### AI model

-   Model file currently used: `Old.pt`
-   Previously configured path:
    `/home/intrino/garbage_classifier/Old.pt`
-   Camera index: `0`
-   Detection confidence threshold used in the test: `0.5`
-   Detected labels observed: `paper` and `plastic_bottle`

The trained model file is not included in this repository by default.
Add it only if repository size and dataset/model licensing allow it.
Otherwise keep it outside Git and document where the authorized model
can be obtained.

## 3. Hardware pin map

  Device                      Arduino pin
  --------------------------- -------------
  Motor 1 (MG995) signal      D10
  Motor 2 (9g servo) signal   D3
  Ultrasonic S1 TRIG / ECHO   D4 / D5
  Ultrasonic S2 TRIG / ECHO   D6 / D7
  Ultrasonic S3 TRIG / ECHO   D8 / D9

### Power and wiring notes

-   Power the servos from a suitable regulated external supply sized for
    the servo load; do not power the MG995 from the Arduino 5 V pin.
-   Connect external servo-supply ground to Arduino GND (common ground).
-   Check servo polarity and signal wiring before powering the circuit.
-   Disconnect power before changing wiring.
-   Stop testing immediately if the Arduino, wiring, or power supply
    becomes unusually hot, smells, smokes, or behaves unexpectedly.
-   The Arduino serial connection is normally configured for **9600
    baud**.
-   The serial device may appear as `/dev/ttyACM0`, `/dev/ttyACM1`, or
    another device. Check the actual device before running Python.

## 4. Software setup on Jetson Nano

Use the project Python virtual environment (example path shown below):

``` bash
source ~/ai_env/bin/activate
```

Install the Python packages used by the application inside that
environment:

``` bash
python -m pip install pyserial opencv-python ultralytics
```

> Jetson Nano compatibility can depend on the installed JetPack, CUDA,
> Python, and PyTorch versions. If Ultralytics/PyTorch is already
> installed and working in the project environment, do not reinstall it
> unnecessarily.

Check the serial device:

``` bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

If the port differs from the configured value, update `ARDUINO_PORT` in
the Python application.

Run the application from the folder containing the Python file:

``` bash
cd ~/Videos
python3 smartbin_webcam_test.py
```

Use the actual filename saved in the repository if it differs. The
webcam application should be the only process using the Arduino serial
port while it is running. Close Arduino IDE Serial Monitor before
starting the Python application.

## 5. Arduino serial command protocol

The tested combined sketch has used these commands:

  Command   Expected action
  --------- ------------------------
  `m1 90`   Move Motor 1 to 90°
  `m2 90`   Move Motor 2 to 90°
  `home`    Move both motors to 0°

Expected acknowledgement examples:

``` text
ACK:MOTOR1_90
ACK:MOTOR2_90
ACK:BOTH_HOME
```

An acknowledgement confirms that the Arduino received and processed the
command; it does not by itself prove that the servo physically moved.
Confirm movement visually during testing.

## 6. Temporary bin CAD proposal

The following are **proposed starting dimensions for a temporary Fusion
360 model**, not dimensions measured from a completed physical bin:

  Feature                           Proposed dimension
  ------------------------------- --------------------
  Overall bin width (X)                         400 mm
  Overall bin depth (Y)                         300 mm
  Overall bin height (Z)                        500 mm
  Lid A                                   200 × 300 mm
  Lid B                                   200 × 300 mm
  Suggested lid panel thickness                3--4 mm
  Suggested body wall thickness                   3 mm

### Two-lid arrangement

-   Use two separate lid panels.
-   Each lid should have its own hinge arrangement.
-   Each lid should open and close independently.
-   Servo brackets must be designed around the actual motor mounting
    tabs, horn, hinge position, and lid load.
-   Check that the servo does not force a lid against a hard mechanical
    stop.

### Display status

The display is **temporarily omitted**. Do not create a display opening
in the current enclosure revision. Add the display and its cutout only
after the actual display module is available and measured.

### CAD verification required

Before printing or fabrication, confirm the overall bin capacity,
internal compartment dimensions, lid clearances, hinge positions, actual
servo dimensions, and the mounting locations of the camera and sensors.
The proposed enclosure dimensions should be treated as a placeholder
until confirmed against the project requirements.

## 7. Known issues and next tasks

-   [ ] Confirm the correct serial port each time the Arduino is
    connected to the Jetson Nano.
-   [ ] Verify paper detection physically moves Motor 1 to 90°.
-   [ ] Verify plastic detection physically moves Motor 2 to 90°.
-   [ ] Verify both lids can return safely to the closed position.
-   [ ] Integrate the three ultrasonic sensor readings into the webcam
    application's display (the last shared webcam screen showed
    `Sensors: waiting...`).
-   [ ] Test all three sensors at known distances and document their
    usable range.
-   [ ] Test the complete system repeatedly with the Arduino Serial
    Monitor closed.
-   [ ] Confirm bin dimensions and internal compartment layout.
-   [ ] Design and test the two independent lid hinges and servo
    linkages.
-   [ ] Measure the actual webcam and breadboard before designing final
    holders.
-   [ ] Add the display module and front-panel cutout in a later
    revision when hardware is available.
-   [ ] Update this README after each successful hardware/software
    milestone.

## 8. Suggested repository structure

``` text
AI-Smart-Dustbin/
├── README.md
├── arduino/
│   └── smart_dustbin_controller/
│       └── smart_dustbin_controller.ino
├── python/
│   ├── smartbin_webcam_test.py
│   └── requirements.txt
├── models/
│   └── README.md
├── cad/
│   └── README.md
├── docs/
│   ├── wiring/
│   ├── test-results/
│   └── design-measurements/
└── .gitignore
```

This is a suggested layout. Move your existing files into these folders
only after checking their actual filenames and paths.

## 9. Git and GitHub version-control setup

From the project root folder:

``` bash
git init
git add README.md
git commit -m "Add project README and current status"
```

After adding the source files:

``` bash
git add arduino/ python/ cad/ docs/ .gitignore
git commit -m "Add smart dustbin source and design files"
```

Connect to a GitHub repository (replace the URL with your own repository
URL):

``` bash
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

For later updates:

``` bash
git status
git add .
git commit -m "Describe the change"
git push
```

### Suggested `.gitignore`

Create a `.gitignore` file in the repository root:

``` gitignore
# Python
__pycache__/
*.py[cod]
.venv/
ai_env/
.env

# Local model weights and datasets (keep large/private files out of Git)
*.pt
datasets/
runs/

# Editor and OS files
.vscode/
.DS_Store
Thumbs.db

# Temporary output
*.log
*.tmp
```

Do not commit passwords, API keys, private credentials, or large
model/dataset files accidentally. If you want to version CAD files, add
the intended Fusion 360 exports (for example STEP/STL) deliberately and
keep source design files organized.

## 10. Development log

Update this section whenever a milestone is completed.

  -----------------------------------------------------------------------
  Date                    Work / milestone        Status
  ----------------------- ----------------------- -----------------------
  2026-11-13              Paper and plastic       Tested
                          detection observed with 
                          webcam/YOLO             

  2026-11-13              Arduino received Motor  Tested
                          1 and Motor 2 commands  
                          and returned ACK        
                          messages                

  2026-11-13              Both servo motors       Reported working
                          tested individually     

  2026-11-13              Three ultrasonic        Tested
                          sensors produced        
                          changing distance       
                          readings in Arduino     
                          Serial Monitor          

  2026-11-13              Sensor readings         Pending; last shared
                          displayed inside webcam display showed waiting
                          window                  message

  2026-11-13              Two-lid enclosure CAD   Temporary proposal;
                          dimensions              needs confirmation

  Pending                 Display integration     Deferred until display
                                                  hardware is available
  -----------------------------------------------------------------------

------------------------------------------------------------------------

**Project note:** This README records the status demonstrated or
reported during prototype testing. Items marked proposed, approximate,
pending, or requiring verification should not be presented as completed
final specifications.
