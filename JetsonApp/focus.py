import cv2 as cv
import numpy as np


class Focus:
    FORWARD = 0
    BACKWARD = 1
    FRAC_FORWARD = 3
    FRAC_BACKWARD = 2
    SMALL_OPPOSITE = 2

    def __init__(self, epsilon, threshold):
        self.currentPosition = 0
        self.beforePosition = 0

        self.currentScore = 0
        self.beforeScore = 0
        self.optimumScore = 0

        self.direction = 0

        self.isScanning = False
        self.isDirected = False
        self.isOptimum = False
        self.isOvershoot = False

        self.epsilon = epsilon
        self.threshold = threshold

        self.stepSize = 10
        acceleration = 1.2

        self.wasd = [1, 2, 3, 4]
        self.candidate = [None, None, None, None]
        self.candidate[0] = acceleration
        self.candidate[1] = -acceleration
        self.candidate[2] = -1 / acceleration
        self.candidate[3] = 1 / acceleration

    # Showing Value
    def show(self):
        print("currentPosition  : " + str(self.currentPosition))
        print("beforePosition   : " + str(self.beforePosition))

        print("currentScore     : " + str(self.currentScore))
        print("beforeScore      : " + str(self.beforeScore))

        print("isScanning       : " + str(self.isScanning))
        print("isDirected       : " + str(self.isDirected))
        print("isOptimum        : " + str(self.isOptimum))
        print("isOvershoot      : " + str(self.isOvershoot))

    # Sharpness Evaluation
    def evaluation(self, input):
        #height, width, channel = input.shape
        #input = input[int(height/2 - 200) : int(height/2 + 200), \
        #              int(width/2 - 200) : int(height/2 + 200)]

        gaussian = cv.GaussianBlur(input, (5, 5), 0)
        sobel = cv.Sobel(gaussian, -1, 1, 1)
        sobel = np.sum(sobel)
        return sobel

    def request(self, img):
        self.beforePosition = self.currentPosition
        self.beforeScore = self.currentScore

        self.currentScore = self.evaluation(img)

        ## Search Algorithm (Continuous Space Hill Climbing Algorithm)
        if not self.isOptimum and self.isDirected:
            if self.isOvershoot:
                if self.currentScore < self.beforeScore:
                    self.isOptimum = True
                    self.optimumScore = self.beforeScore
                    self.currentPosition = self.beforePosition
                    return self.currentPosition

            # Step Direction & Size Calculation
            if self.currentScore < self.beforeScore:
                self.direction = self.direction + Focus.SMALL_OPPOSITE
                self.isOvershoot = True

            step = self.stepSize * self.candidate[self.direction]
            self.currentPosition = self.beforePosition + step

            # Set maximum value
            if self.currentPosition > 240:
                self.currentPosition = 240

        # Directional Finding
        if not self.isScanning:
            step = self.stepSize * self.candidate[Focus.FORWARD]
            self.currentPosition = self.beforePosition + step

            # Set maximum value
            if self.currentPosition > 240:
                self.currentPosition = 240

            self.isScanning = True

            return self.currentPosition

        if not self.isDirected:
            if self.currentScore > self.beforeScore:
                self.direction = Focus.FORWARD
            else:
                self.direction = Focus.BACKWARD

            self.isDirected = True

        # Scene Change Detection
        if self.isOptimum:
            if (self.optimumScore - self.currentScore) > self.threshold:
                self.isScanning = False
                self.isDirected = False
                self.isOptimum = False
                self.isOvershoot = False

                # return self.request(img)

        return self.currentPosition

