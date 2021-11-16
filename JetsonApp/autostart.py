# Executed by ~/.config/autostart/yolo

import subprocess
import os
import sys
import time
import re
from datetime import datetime

print(datetime.now())

# Checking USB Serial availability
while(True):
    out = os.popen("ls /dev/ttyUSB*").read()
    out = re.match("\/dev\/ttyUSB*\d", out)
    if out == None:
        print("There are no usb serial available, searching again in 3s")
        time.sleep(3)
        continue

    print("found! " + str(out.group()))
    break

# Running yolo subprocess
sub_process = subprocess.Popen(["python3", "yolo.py"], cwd="/home/name/ai/yolo")

# Checking subprocess availability
while(True):
    poll = sub_process.poll()
    if poll is not None:
        break

    time.sleep(1)

print("-------------------------")

# Restarting Program
os.execv(sys.executable, ['python'] + sys.argv)
#os.startfile(__file__)
#sys.exit()
