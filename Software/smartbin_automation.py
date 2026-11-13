#!/usr/bin/env python3
"""
AI SMART DUSTBIN - JETSON NANO PYTHON PROGRAM

Features:
- Arduino USB serial communication
- S1 garbage distance and YOLO trigger
- S2 + S3 bin-full monitoring (same bin)
- Live webcam display (Camera 0)
- YOLO paper/plastic classification
- Motor commands and manual terminal control

Arduino firmware must be uploaded separately and must send:
S1:21.3,S2:18.2,S3:18.0

Arduino command strings used:
m1 90, m2 90, m1 0, m2 0, home
"""

import glob
import re
import sys
import threading
import time

import cv2
import serial
from ultralytics import YOLO


# -------------------- CONFIGURATION --------------------

MODEL_PATH = "/home/intrino/garbage_classifier/Old.pt"
CAMERA_ID = 0
BAUD_RATE = 9600

S1_TRIGGER_CM = 15.0
S2_FULL_LIMIT_CM = 8.0
S3_FULL_LIMIT_CM = 8.0
YOLO_CONFIDENCE = 0.50
SENSOR_TIMEOUT_SECONDS = 2.0

# Safety lock: keep False until MG995 is confirmed to stop
# at commanded angles and has a suitable external servo supply.
ENABLE_MOTOR1 = False
ENABLE_MOTOR2 = True


# -------------------- SHARED DATA --------------------

running = True
serial_lock = threading.Lock()
sensor_lock = threading.Lock()

distances = {"S1": -1.0, "S2": -1.0, "S3": -1.0}
last_sensor_update = 0.0

SENSOR_PATTERN = re.compile(
    r"S1:([-+]?\d+(?:\.\d+)?),"
    r"S2:([-+]?\d+(?:\.\d+)?),"
    r"S3:([-+]?\d+(?:\.\d+)?)"
)


# -------------------- ARDUINO CONNECTION --------------------

def find_arduino_port():
    ports = sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))
    if not ports:
        raise RuntimeError(
            "Arduino not detected. Check USB and run:\n"
            "ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null"
        )
    return ports[0]


def connect_arduino():
    port = find_arduino_port()
    print(f"[INFO] Arduino detected: {port}")
    device = serial.Serial(port, BAUD_RATE, timeout=0.2, write_timeout=1)
    time.sleep(2)  # Arduino may reset when serial opens
    print("[INFO] Arduino connected.")
    return device


# -------------------- MOTOR CONTROL --------------------

def send_motor_command(arduino, command):
    command = command.strip().lower()

    if command.startswith("m1") and not ENABLE_MOTOR1:
        print("[SAFETY] Motor 1 command blocked: MG995 safety lock is ON.")
        return

    if command.startswith("m2") and not ENABLE_MOTOR2:
        print("[SAFETY] Motor 2 is disabled.")
        return

    allowed = {"m1 90", "m2 90", "m1 0", "m2 0", "home"}
    if command not in allowed:
        print(f"[WARN] Unsupported command: {command}")
        return

    with serial_lock:
        arduino.write((command + "\n").encode("utf-8"))
        arduino.flush()

    print(f"[COMMAND] {command}")


# -------------------- SENSOR READER THREAD --------------------

def sensor_reader(arduino):
    global last_sensor_update

    while running:
        try:
            line = arduino.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            if line.startswith("ACK:") or line.startswith("UNKNOWN"):
                print("[ARDUINO]", line)
                continue

            match = SENSOR_PATTERN.search(line)
            if match:
                values = {
                    "S1": float(match.group(1)),
                    "S2": float(match.group(2)),
                    "S3": float(match.group(3)),
                }
                with sensor_lock:
                    distances.update(values)
                    last_sensor_update = time.time()

        except (serial.SerialException, OSError) as exc:
            if running:
                print("[SERIAL ERROR]", exc)
                time.sleep(0.5)
        except Exception as exc:
            if running:
                print("[SENSOR ERROR]", exc)
                time.sleep(0.2)


def get_sensor_snapshot():
    with sensor_lock:
        return distances.copy(), last_sensor_update


# -------------------- MANUAL COMMAND THREAD --------------------

def manual_control(arduino):
    global running
    print("\nManual commands: m1 | m2 | m1home | m2home | home | q")

    while running:
        try:
            command = input("Command> ").strip().lower()

            if command == "m1":
                send_motor_command(arduino, "m1 90")
            elif command == "m2":
                send_motor_command(arduino, "m2 90")
            elif command == "m1home":
                send_motor_command(arduino, "m1 0")
            elif command == "m2home":
                send_motor_command(arduino, "m2 0")
            elif command == "home":
                if ENABLE_MOTOR1 and ENABLE_MOTOR2:
                    send_motor_command(arduino, "home")
                else:
                    if ENABLE_MOTOR1:
                        send_motor_command(arduino, "m1 0")
                    if ENABLE_MOTOR2:
                        send_motor_command(arduino, "m2 0")
            elif command == "q":
                print("[INFO] Shutdown requested.")
                running = False
                break
            elif command:
                print("Use: m1, m2, m1home, m2home, home, q")

        except EOFError:
            break
        except Exception as exc:
            print("[MANUAL CONTROL ERROR]", exc)


# -------------------- BIN FULL LOGIC --------------------

def get_bin_status(s2, s3, fresh):
    if not fresh:
        return "SENSOR DATA LOST"
    if s2 <= 0 or s3 <= 0:
        return "CHECK S2/S3"
    if s2 <= S2_FULL_LIMIT_CM and s3 <= S3_FULL_LIMIT_CM:
        return "BIN FULL"
    return "BIN NOT FULL"


# -------------------- YOLO CLASSIFICATION --------------------

def detect_and_sort(frame, model, arduino):
    results = model(frame, verbose=False)
    annotated = frame.copy()
    label_found = "No recognized object"
    confidence_found = 0.0

    for result in results:
        annotated = result.plot()
        if result.boxes is None:
            continue

        boxes = sorted(
            result.boxes,
            key=lambda box: float(box.conf[0]),
            reverse=True
        )

        for box in boxes:
            confidence = float(box.conf[0])
            if confidence < YOLO_CONFIDENCE:
                continue

            class_id = int(box.cls[0])
            label = str(model.names[class_id]).lower()
            label_found = label
            confidence_found = confidence

            print(f"[YOLO] {label}, confidence={confidence:.2f}")

            if "paper" in label:
                send_motor_command(arduino, "m1 90")
                return annotated, label_found, confidence_found

            if "plastic" in label:
                send_motor_command(arduino, "m2 90")
                return annotated, label_found, confidence_found

    return annotated, label_found, confidence_found


# -------------------- MAIN APPLICATION --------------------

def main():
    global running

    arduino = None
    camera = None

    try:
        arduino = connect_arduino()

        print("[INFO] Loading YOLO model:", MODEL_PATH)
        model = YOLO(MODEL_PATH)
        print("[INFO] YOLO model loaded.")

        threading.Thread(
            target=sensor_reader, args=(arduino,), daemon=True
        ).start()

        threading.Thread(
            target=manual_control, args=(arduino,), daemon=True
        ).start()

        camera = cv2.VideoCapture(CAMERA_ID, cv2.CAP_V4L2)
        if not camera.isOpened():
            raise RuntimeError(f"Cannot open webcam camera index {CAMERA_ID}")

        print("\n========== AI SMART DUSTBIN STARTED ==========")
        print("S1: garbage distance / YOLO trigger")
        print("S2 + S3: bin fullness monitoring")
        print("Webcam: live feed")
        print("Press Q in the camera window to stop.")
        print("==============================================\n")

        object_armed = True
        last_detection_label = "Waiting for garbage"
        last_confidence = 0.0

        while running:
            ret, frame = camera.read()
            if not ret:
                print("[CAMERA ERROR] Could not read frame.")
                break

            sensor_values, updated_at = get_sensor_snapshot()
            s1, s2, s3 = (
                sensor_values["S1"],
                sensor_values["S2"],
                sensor_values["S3"],
            )

            fresh = (
                updated_at > 0
                and time.time() - updated_at <= SENSOR_TIMEOUT_SECONDS
            )

            garbage_near = fresh and 0 < s1 <= S1_TRIGGER_CM
            bin_status = get_bin_status(s2, s3, fresh)

            display = frame.copy()

            # Run YOLO once when a new object approaches S1.
            if garbage_near and object_armed:
                print(f"[S1] Object detected at {s1:.1f} cm; running YOLO.")
                display, last_detection_label, last_confidence = (
                    detect_and_sort(frame, model, arduino)
                )
                object_armed = False

            # Rearm after the object moves away beyond the trigger area.
            if not garbage_near and (s1 < 0 or s1 > S1_TRIGGER_CM + 5):
                object_armed = True

            s1_text = f"{s1:.1f} cm" if s1 > 0 else "No echo"
            s2_text = f"{s2:.1f} cm" if s2 > 0 else "No echo"
            s3_text = f"{s3:.1f} cm" if s3 > 0 else "No echo"

            cv2.putText(
                display, f"S1 Garbage Distance: {s1_text}",
                (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2
            )
            cv2.putText(
                display, f"S2 Bin Sensor: {s2_text}",
                (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 0), 2
            )
            cv2.putText(
                display, f"S3 Bin Sensor: {s3_text}",
                (20, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 0), 2
            )
            cv2.putText(
                display,
                "AI ACTIVE - GARBAGE NEAR" if garbage_near else "WAITING FOR GARBAGE",
                (20, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 255, 255), 2
            )

            bin_color = (0, 0, 255) if bin_status == "BIN FULL" else (0, 255, 0)
            cv2.putText(
                display, bin_status,
                (20, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.70, bin_color, 2
            )
            cv2.putText(
                display,
                f"YOLO: {last_detection_label} ({last_confidence:.2f})",
                (20, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2
            )

            cv2.imshow("AI SMART DUSTBIN", display)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")
    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        raise
    finally:
        running = False
        if camera is not None:
            camera.release()
        cv2.destroyAllWindows()
        if arduino is not None and arduino.is_open:
            arduino.close()
        print("[INFO] AI SMART DUSTBIN STOPPED.")


if __name__ == "__main__":
    main()
