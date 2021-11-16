
import cv2
import time
import os
import threading
from focus import Focus
from motor import Motor
from antares_http import antares
import RPi.GPIO as GPIO

IO_ACTUATOR = 20
MODE_AUTO = True
MODE_MANUAL = False

actuatorLastMove = 0
focusLastMove = 0
antaresCheckModeLastTime = 0
focusState = 0
checkModeStatus = 1

cap = None
focus = None
motor = None

setThreadLock = threading.Lock()
getThreadLock = threading.Lock()

# State Used for sending data only when changed
antares_isDetectedTrueSended = False
antares_isDetectedFalseSended = False

#
# Threading for Antares Communication
#
class antaresSetThreading(threading.Thread):
    def __init__(s, classes, boxes):
        threading.Thread.__init__(s)
        s.classes = classes
        s.boxes = boxes

    def run(s):
        setThreadLock.acquire()
        bird_detection(s.classes, s.boxes)
        setThreadLock.release()

class antaresGetThreading(threading.Thread):
    def __init__(s):
        threading.Thread.__init__(s)

    def run(s):
        getThreadLock.acquire()
        antares_check_mode()
        getThreadLock.release()

#
# Processing Yolo output for detecting bird
#
def bird_detection(classes, boxes):
    # returning when no object detected
    if len(classes) == 0:
        bird_detection_false()
        return
    if classes[0][0] == 0 or classes[0][0] == 2:
        bird_detection_true()
    else:
        bird_detection_false()

#
# Sending Antares When Bird Detected
#
def bird_detection_true():
    global antares_isDetectedTrueSended, antares_isDetectedFalseSended, actuatorLastMove

    actuatorLastMove = time.time()
    if not antares_isDetectedTrueSended:
        antares_send(True)

        antares_isDetectedTrueSended = True
        antares_isDetectedFalseSended = False

#
# Sending Antares When Bird not Detected
#
def bird_detection_false():
    global antares_isDetectedTrueSended, antares_isDetectedFalseSended
    if not antares_isDetectedFalseSended:
        antares_send(False)

        antares_isDetectedTrueSended = False
        antares_isDetectedFalseSended = True

#
# Antares Sending Function
#
def antares_send(state):
    data={
        "jetson":{
            "burung_terdeteksi": state
        }
    }
    antares.setAccessKey("c99552509917246b:5a8e2869cffd7e1c")
    antares.send(data, "Emprit","jetson")

#
# Antares Checking Operation Mode
#
def antares_check_mode():
    global checkModeStatus, MODE_AUTO, MODE_MANUAL

    antares.setAccessKey("c99552509917246b:5a8e2869cffd7e1c")
    data = antares.get("Emprit", "android")
    data = data["content"]
    print(data)

    if data["android"]["mode"] == "Auto":
        checkModeStatus = MODE_AUTO
        return

    elif data["android"]["mode"] == "Manual":
        if data["android"]["control_motor"] == "1":
            GPIO.output(IO_ACTUATOR, GPIO.HIGH)
        elif data["android"]["control_motor"] == "0":
            GPIO.output(IO_ACTUATOR, GPIO.LOW)

        checkModeStatus = MODE_MANUAL
        return

#
# Function for initializing camera capture
#
def gstreamer_pipeline(
    capture_width=640,
    capture_height=480,
    display_width=640,
    display_height=480,
    framerate=15,
    flip_method=2,
):
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )

#
# Set focus position program based on received image
#
def autofocus(img):
    global focus, motor
    position = focus.request(img)
    motor.set_focus(position)

#
# Set Focus to zero
#
def focus_zero():
    global motor
    motor.set_focus(0)

#
# Set Cyclic Discrete Focus Distance
#
def focus_distance_next():
    global motor, focusState

    if focusState == 0:
        motor.set_focus(146)
        focusState = 1
    elif focusState == 1:
        motor.set_focus(161)
        focusState = 0

#
# Object Detection using yolo and opencv
# Main Function
def yolo():
    global actuatorLastMove, antaresCheckModeLastTime, focusLastMove, checkModeStatus, MODE_AUTO, MODE_MANUAL

    CONFIDENCE_THRESHOLD = 0.2
    NMS_THRESHOLD = 0.4
    COLORS = [(0, 255, 255), (255, 255, 0), (0, 255, 0), (255, 0, 0)]

    class_names = []
    with open("yolo/emprit4.names", "r") as f:
        class_names = [cname.strip() for cname in f.readlines()]

    # Initializing DNN model
    net = cv2.dnn.readNet("yolo/emprit4.weights", "yolo/emprit4.cfg")
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA_FP16)

    model = cv2.dnn_DetectionModel(net)
    model.setInputParams(size=(416, 416), scale=1/255, swapRB=True)

    # Initialize Camera
    cap = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)
    # Checking camera
    if not cap.isOpened():
        print("Cannot detect camera")
        return

    # Set interval for focus positioning
    focusTime = time.time()
    focusInterval = 1.6

    # Init Mode Status
    checkModeStatus = MODE_AUTO

    cv2.namedWindow("Detection", cv2.WINDOW_AUTOSIZE)
    while cv2.getWindowProperty("Detection", 0) >=0:
        grabbed, frame = cap.read()

        # Checking Command Mode from antares
        if time.time() - antaresCheckModeLastTime > 4:
            getThread = antaresGetThreading()
            getThread.start()
            antaresCheckModeLastTime = time.time()

        if checkModeStatus == MODE_MANUAL:
            cv2.imshow("Detection", frame)
            # Listening for Escape Key to get out from loop
            keyCode = cv2.waitKey(30) & 0xFF
            if keyCode == 27:
                break

            continue

        # Detecting Object
        classes, scores, boxes = model.detect(frame, CONFIDENCE_THRESHOLD, NMS_THRESHOLD)

        # Autofocus
#        if focusTime + focusInterval < time.time():
#            focusTime = time.time()
#            autofocus(frame)

        # Focus Cycle
        if time.time() - focusLastMove > 10:
            focus_distance_next()
            focusLastMove = time.time()

        # Bird Detection
        setThread = antaresSetThreading(classes, boxes)
        setThread.start()
        # bird_detection(classes, boxes)

        # Labeling & Set Bound for object
        for (classid, score, box) in zip(classes, scores, boxes):
            color = COLORS[int(classid) % len(COLORS)]
            label = "%s : %f" % (class_names[classid[0]], score)
            cv2.rectangle(frame, box, color, 2)
            cv2.putText(frame, label, (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        cv2.imshow("Detection", frame)

        # Listening for Escape Key to get out from loop
        keyCode = cv2.waitKey(30) & 0xFF
        if keyCode == 27:
            break

        # Moving Actuator Based on detection
        #if time.time() - actuatorLastMove < 5:
        #    GPIO.output(IO_ACTUATOR, GPIO.HIGH)

        #else:
        #    GPIO.output(IO_ACTUATOR, GPIO.LOW)


    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    try:

        # Initialize focus
#        focus = Focus(1000, 10000)

        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(IO_ACTUATOR, GPIO.OUT, initial=GPIO.LOW)
        time.sleep(2)

        antares_check_mode()
        # Initialize motor
        motor = Motor()

        # Set Motor Focus Position
#        motor.set_focus(0)
#        time.sleep(15)

        # Set Actuator Timing
        actuatorLastMove = time.time() - 5
        antaresCheckModeLastTime = time.time()

        # Set Focus Timing
        focusLastMove = time.time() - 10

        # Run Yolo
        yolo()

    except Exception as e:
        print("Interrupted")
        print(str(e))
        try:
            if not cap == None:
                if cap.isOpened():
                    cap.release()

            cv2.destroyAllWindows()
            os._exit(0)
        except SystemExit:
            cap.release()
            cv2.destroyAllWindows()
            os._exit(0)




# TODO
# Design detailed Logic
