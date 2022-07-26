# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

# Simple demo of the TCS34725 color sensor.
# Will detect the color from the sensor and print it out every second.
import time
import board
import adafruit_tcs34725
from math import dist
import RPi.GPIO as GPIO
import sys

line = sys.stdin.readline().strip()
if line.__contains__("READ_CONTINOUSLY"):
    READ_CONTINOUSLY = True
    destination = 0
    direction = 0
    
else: 
    READ_CONTINOUSLY = False
    destination = line.split('_')[0]
    direction = line.split('_')[1]
    
#GPIO.setmode(GPIO.BOARD)
control_pins = [4,17,27,22]
for pin in control_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, 0)

halfstep_seq = [
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1],
    [1,0,0,1]
]

print("Destination is {0} by turning {1}".format(
            destination, direction
        ))


# Create sensor object, communicating over the board's default I2C bus
i2c = board.I2C()  # uses board.SCL and board.SDA
sensor = adafruit_tcs34725.TCS34725(i2c)


myColors = {
    "BLOCKED" :     (321, 149, 137, 615),   # Red
    "BLURRED" :   (170, 183, 118, 493),   # Green  
    "MASKED" :     (238, 236, 244, 740),  # Blue 
    "OPEN" :   (182, 141, 111, 454) # Black
}

GPIO.setup(26, GPIO.OUT)  # PIN to disable RGB sensor LED

# Change sensor integration time to values between 2.4 and 614.4 milliseconds
# sensor.integration_time = 150

# Change sensor gain to 1, 4, 16, or 60
sensor.gain = 60
GPIO.output(26,True)

MAX_STEPS = 1024
CURRENT_STEPS = 0
STEP_CHUNK = 16
DISTANCE_THRESHOLD = 30
WAIT_BETWEEN_STEPS = 0.005
WAIT_BETWEEN_CHUNK = 1

if READ_CONTINOUSLY:
    while True:
        color_rgbc = sensor.color_raw
        print("{0}".format(
                color_rgbc
            ))

        for x in myColors:
            myTuple = myColors[x]
            if myColors[x] == "OPEN":
                distance = dist(myTuple, color_rgbc)
            else: 
                distance = dist(myTuple[:-1], color_rgbc[:-1])
            if distance <= DISTANCE_THRESHOLD:
                print(x, "\n ", distance) 
    
        time.sleep(0.5)
else:
    while MAX_STEPS > CURRENT_STEPS:
        color_rgbc = sensor.color_raw
        print("rgb{0}".format(
                    color_rgbc
                ))

        myTuple = myColors[destination]
        if destination == "OPEN":
            distance = dist(myTuple, color_rgbc)
        else: 
            distance = dist(myTuple[:-1], color_rgbc[:-1])
        if distance <= DISTANCE_THRESHOLD:
            print("Reached destination!")
            break

        if direction == "LEFT":
            for i in range(STEP_CHUNK):
                for halfstep in range(8):
                    for pin in range(4):
                        GPIO.output(control_pins[pin], halfstep_seq[halfstep][pin])
                    time.sleep(WAIT_BETWEEN_STEPS)
            

        elif direction == "RIGHT":
            for i in range(STEP_CHUNK):
                for halfstep in reversed(range(8)):
                    for pin in range(4):
                        GPIO.output(control_pins[pin], halfstep_seq[halfstep][pin])
                    time.sleep(WAIT_BETWEEN_STEPS)    

        CURRENT_STEPS += STEP_CHUNK
        time.sleep(WAIT_BETWEEN_CHUNK)    

sensor.active = False
GPIO.output(26,False)
print("Disabled")

