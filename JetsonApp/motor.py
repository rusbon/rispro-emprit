import serial

class Motor:
    AXIS_YAW = 0
    AXIS_PITCH = 1
    AXIS_FOCUS = 2
    AXIS_APERTURE = 3

    SCANNING = 10
    ABSOLUTE = 11
    RELATIVE = 12
    FOCUS_REL = 13
    FOCUS_ABS = 14
    APERTURE_REL = 15
    RESET = 20

    def __init__(self):
        self.ser = serial.Serial(
            port="/dev/ttyUSB0",
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
            )

        self.mode = 0
        self.sMode = " "

        self.axis = -1

        self.yaw = 0.0
        self.pitch = 0.0
        self.focus = 0.0
        self.aperture = 0.0

        self.directionYaw = 0
        self.directionPitch = 0
        self.directionFocus = 0
        self.directionAperture = 0

        self.focusScale = 1.0

    def set_mode(self, mode):
        self.mode = mode

        if mode == Motor.SCANNING:
            self.sMode = "F"
        if mode == Motor.ABSOLUTE:
            self.sMode = "M"
        if mode == Motor.RELATIVE:
            self.sMode = "R"
        if mode == Motor.FOCUS_REL or \
           mode == Motor.APERTURE_REL:
            self.sMode = "Y"
        if mode == Motor.FOCUS_ABS:
            self.sMode = "H"
        if mode == Motor.RESET:
            self.sMode = "S"

    def set_focus(self, position, mode=None):
        if mode == None:
            mode = Motor.FOCUS_ABS

        if position > 0:
            self.directionFocus = 1
        else:
            self.directionFocus = 0
            position = position * -1

        position = position * self.focusScale
        self.focus = position

        self.set_mode(mode)
        self.send_command()

    def set_aperture(self, position):
        if position < 0:
            self.directionAperture = 1
            position = position * -1
        else:
            self.directionAperture = 0

        self.aperture = position

        self.setmode(Motor.APERTURE_REL)
        self.send_command()

    def set_scanning(self, yaw, pitch, step):
        # Set Maximum value
        if yaw > 999.9:
            yaw = 999.9
        if pitch > 999.9:
            pitch = 999.9
        if step > 999:
            step = 999

        self.yaw = yaw
        self.pitch = pitch

        self.set_mode(Motor.SCANNING)
        self.send_command()

    def set_position(self, yaw, pitch, mode=None):
        if mode == None:
            mode = Motor.ABSOLUTE

        # Set direction
        if yaw < 0:
            self.directionYaw = 1
            yaw = yaw * -1
        else:
            self.directionYaw = 0

        if pitch < 0:
            self.directionPitch = 1
            pitch = pitch * -1
        else:
            self.direcitonPitch = 0

        # Set Maximum value to 99.99
        if yaw > 999.9:
            yaw = 999.9
        if pitch > 999.9:
            pitch = 999.9

        self.yaw = yaw
        self.pitch = pitch

        self.set_mode(mode)
        self.send_command()

    def reset(self, axis):
        self.axis = axis

        self.set_mode(Motor.RESET)
        self.send_command()

    def send_command(self):
        if self.mode == Motor.SCANNING:
            command = str(int(self.yaw * 100)).zfill(4) + \
                      str(int(self.pitch * 100)).zfill(4) + \
                      str(self.scanningStep).zfill(3)

        if self.mode == Motor.FOCUS_ABS or \
           self.mode == Motor.FOCUS_REL:
            command = str(self.directionFocus) + \
                      str(int(self.focus * 10)).zfill(4) + \
                      "0000000"

        if self.mode == Motor.APERTURE_REL:
            command = "00000" + \
                      str(self.directionAperture) + \
                      str(int(self.aperture * 10)).zfill(4) + \
                      "00"

        if self.mode == Motor.ABSOLUTE or \
           self.mode == Motor.RELATIVE:
             command = str(self.directionYaw)   + str(int(self.yaw * 100)).zfill(4) + \
                       str(self.directionPitch) + str(int(self.pitch * 100)).zfill(4) + \
                       "00"

        if self.mode == Motor.RESET:
            command = str(int(self.axis)) + "00000000000"

        command = self.sMode + command + "t"
        #print(command)

        self.ser.write(command.encode())
