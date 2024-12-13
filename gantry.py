import RPi.GPIO as GPIO
import time

class Gantry:
    MOTOR_A_DIR_PIN = 20
    MOTOR_A_STEP_PIN = 21
    MOTOR_B_DIR_PIN = 19
    MOTOR_B_STEP_PIN = 26
    MOTOR_C_DIR_PIN = 5
    MOTOR_C_STEP_PIN = 6

    STEPS_PER_UNIT = 38.5  
    STEPS_PER_UNIT_Y = 39.9
    STEPS_Z = 27500
    STEP_DELAY = 60e-6

    def __init__(self, initial_x=0.0, initial_y=0.0):
        self.current_x = initial_x
        self.current_y = initial_y
        self.current_z = 0
        self.initGantry()

    def initGantry(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.MOTOR_A_DIR_PIN, GPIO.OUT)
        GPIO.setup(self.MOTOR_A_STEP_PIN, GPIO.OUT)
        GPIO.setup(self.MOTOR_B_DIR_PIN, GPIO.OUT)
        GPIO.setup(self.MOTOR_B_STEP_PIN, GPIO.OUT)
        GPIO.setup(self.MOTOR_C_DIR_PIN, GPIO.OUT)
        GPIO.setup(self.MOTOR_C_STEP_PIN, GPIO.OUT)

    def setDirection(self, direction):
        # direction: 1=forward, 2=backward, 3=left, 4=right
        if direction == 1:  # forward (+Y)
            GPIO.output(self.MOTOR_A_DIR_PIN, GPIO.LOW)
            GPIO.output(self.MOTOR_B_DIR_PIN, GPIO.LOW)
        elif direction == 2: # backward (-Y)
            GPIO.output(self.MOTOR_A_DIR_PIN, GPIO.HIGH)
            GPIO.output(self.MOTOR_B_DIR_PIN, GPIO.HIGH)
        elif direction == 3: # left (-X)
            GPIO.output(self.MOTOR_A_DIR_PIN, GPIO.LOW)
            GPIO.output(self.MOTOR_B_DIR_PIN, GPIO.HIGH)
        elif direction == 4: # right (+X)
            GPIO.output(self.MOTOR_A_DIR_PIN, GPIO.HIGH)
            GPIO.output(self.MOTOR_B_DIR_PIN, GPIO.LOW)
        else:
            raise ValueError("Invalid direction specified.")
    
    def moveVertical(self):
        if self.current_z == 0:
            GPIO.output(self.MOTOR_C_DIR_PIN, GPIO.LOW)
            self.current_z = 1
        else:
            GPIO.output(self.MOTOR_C_DIR_PIN, GPIO.HIGH)
            self.current_z = 0

        count = 0
        while count <= self.STEPS_Z:
            GPIO.output(self.MOTOR_C_STEP_PIN, GPIO.LOW)                                                                                                                                                            
            GPIO.output(self.MOTOR_C_STEP_PIN, GPIO.HIGH)
            count += 1
            time.sleep(self.STEP_DELAY)

    def move2D(self, direction, dist):
        self.setDirection(direction)
        if direction in (1, 2):  # forward/backward (Y-axis)
            total_steps = int(self.STEPS_PER_UNIT_Y * dist)
        else:  # left/right (X-axis)
            total_steps = int(self.STEPS_PER_UNIT * dist)

        for _ in range(total_steps):
            GPIO.output(self.MOTOR_A_STEP_PIN, GPIO.LOW)
            GPIO.output(self.MOTOR_A_STEP_PIN, GPIO.HIGH)
            GPIO.output(self.MOTOR_B_STEP_PIN, GPIO.LOW)
            GPIO.output(self.MOTOR_B_STEP_PIN, GPIO.HIGH)
            time.sleep(self.STEP_DELAY)

        if direction == 1:  # forward (+Y)
            self.current_y -= dist
        elif direction == 2:  # backward (-Y)
            self.current_y += dist
        elif direction == 3:  # left (-X)
            self.current_x += dist
        elif direction == 4:  # right (+X)
            self.current_x -= dist

    def goTo(self, x, y):
        dx = x - self.current_x
        if dx > 0:  
            self.move2D(3, abs(dx))
        elif dx < 0:
            self.move2D(4, abs(dx))

        dy = y - self.current_y
        if dy > 0:
            self.move2D(2, abs(dy))
        elif dy < 0:
            self.move2D(1, abs(dy))

    def cleanup(self):
        GPIO.cleanup()
