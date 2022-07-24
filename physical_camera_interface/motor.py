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
destination = line.split('_')[0]
direction = line.split('_')[1]
    

print("Destination is {0} by turning {1}".format(
            destination, direction
        ))


# Create sensor object, communicating over the board's default I2C bus
i2c = board.I2C()  # uses board.SCL and board.SDA
sensor = adafruit_tcs34725.TCS34725(i2c)


myColors = {
    "BLOCKED" :     (438, 268, 216, 903),   # Red
    "BLURRED" :   (309, 301, 216, 1024),   # Green  
    "MASKED" :    (291, 289, 273, 1000),  # Blue 
    "OPEN" :   (311, 250, 193, 794) # Black
}

GPIO.setup(26, GPIO.OUT)  # PIN to disable RGB sensor LED

# Change sensor integration time to values between 2.4 and 614.4 milliseconds
# sensor.integration_time = 150

# Change sensor gain to 1, 4, 16, or 60
sensor.gain = 60
GPIO.output(26,True)

MAX_STEPS = 512
CONTINOUS_READ = False
CURRENT_STEPS = 0
STEP_CHUNK = 16
DISTANCE_THRESHOLD = 50

while MAX_STEPS > CURRENT_STEPS:
    color_rgbc = sensor.color_raw
    print("rgb{0}".format(
                color_rgbc[:-1]
            ))

    myTuple = myColors[destination]
    if dist(myTuple[:-1], color_rgbc[:-1]) <= DISTANCE_THRESHOLD:
        print("Reached destination!")
        break

    # for x in myColors:
    #     myTuple = myColors[x]
    #     if dist(myTuple[:-1], color_rgbc[:-1]) <= DISTANCE_THRESHOLD:
    #         print(x) 


    if CONTINOUS_READ:
            time.sleep(1.0)    
    else:
        break

for x in myColors:
    if dist(myColors[x][:-1], color_rgbc[:-1]) <= 50:
        print(x) 

   

    
sensor.active = False
GPIO.output(26,False)
print("disabled")

