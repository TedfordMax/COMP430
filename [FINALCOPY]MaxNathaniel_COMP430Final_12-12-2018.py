
#!/usr/bin/env python
# -----------------
# Modified 2018-09-30 to use Matt Hawkins' LCD library for I2C available
# from https://bitbucket.org/MattHawkinsUK/rpispy-misc/raw/master/python/lcd_i2c.py
#######################################################################################
## Digital Theremin COMP430 Final Project
## Finished 12-12-2018
## Created by Max Tedford and Nathaniel Dwyer
#######################################################################################
import RPi.GPIO as GPIO
import time
from array import array  # need a newline between normal text and code, edited to make it so
from time import sleep

import pygame
from pygame.mixer import Sound, get_init, pre_init

# Additional stuff for LCD
import smbus


ButtonPin = 22 # Button assinged to GPIO22


distList = [0] # list used to take rolling averag for raw distance readings
distAvgIntList = [] # list used to store rounded rolling average readings

playModes = ["default", "bells", "cat"] # list that keeps track of how many possible sound libraries (or rather, types of sounds) availible to the user
mode = 0 # variable used to index the playModes list
currentPlayMode = playModes[mode] # determines what set of sounds will be played

keyOfC = [261.63, 293.66, 329.63, 349.23, 392, 440, 493.88, 523.25] # list of note frequencies in the key of C
keyOfG = [392, 440, 493.88, 523.25, 587.33, 659.25, 739.99, 783.99] # list of note frequencies in the key of G

bellSounds = ["261-C.wav", "293-D.wav", "329-E.wav", "349-F.wav", "392-G.wav", "440-A.wav", "494-B.wav", "523-C.wav"] # list of bell sounds
catSounds = ["Cat-C-01.wav", "Cat-D-02.wav", "Cat-E-03.wav", "Cat-F-04.wav", "Cat-G-05.wav", "Cat-A-06.wav", "Cat-B-07.wav", "Cat-C-08.wav"] # list of cat sounds

currentKey = keyOfC # default  musical key

#LCD pin assignments, constants, etc
I2C_ADDR  = 0x27 # I2C device address
LCD_WIDTH = 16   # Maximum characters per line

# Define some device constants
LCD_CHR = 1 # Mode - Sending data
LCD_CMD = 0 # Mode - Sending command

LCD_LINE_1 = 0x80 # LCD RAM address for the 1st line
LCD_LINE_2 = 0xC0 # LCD RAM address for the 2nd line
LCD_LINE_3 = 0x94 # LCD RAM address for the 3rd line
LCD_LINE_4 = 0xD4 # LCD RAM address for the 4th line

LCD_BACKLIGHT  = 0x08  # On
#LCD_BACKLIGHT = 0x00  # Off

ENABLE = 0b00000100 # Enable it

# Timing constants
E_PULSE = 0.0005
E_DELAY = 0.0005


# Ultrasonic pin assignments
SR04_trigger_pin = 20
SR04_echo_pin = 21

# LCD commands
LCD_CMD_4BIT_MODE = 0x28   # 4 bit mode, 2 lines, 5x8 font
LCD_CMD_CLEAR = 0x01
LCD_CMD_HOME = 0x02   # goes to position 0 in line 0
LCD_CMD_POSITION = 0x80  # Add this to DDRAM address

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)       # Numbers GPIOs by standard marking
GPIO.setup(ButtonPin, GPIO.IN, pull_up_down = GPIO.PUD_UP) # assign button as an input

GPIO.setup(SR04_trigger_pin, GPIO.OUT)
GPIO.setup(SR04_echo_pin, GPIO.IN)
GPIO.output(SR04_trigger_pin, GPIO.LOW)

#Open I2C interface
#bus = smbus.SMBus(0)  # Rev 1 Pi uses 0
bus = smbus.SMBus(1) # Rev 2 Pi uses 1

class Note(Sound):

    def __init__(self, frequency, volume=.1):
        self.frequency = frequency
        Sound.__init__(self, self.build_samples())
        self.set_volume(volume)

    def build_samples(self):
        period = int(round(get_init()[0] / self.frequency))
        samples = array("h", [0] * period)
        amplitude = 2 ** (abs(get_init()[1]) - 1) - 1
        for time in range(period):
            if time < period / 2:
                samples[time] = amplitude
            else:
                samples[time] = -amplitude
        return samples


def distance(metric):
        # set Trigger to HIGH
        GPIO.output(SR04_trigger_pin, GPIO.HIGH)

        # set Trigger after 0.01ms to LOW
        time.sleep(0.00001)
        GPIO.output(SR04_trigger_pin, GPIO.LOW)
         
        startTime = time.time()
        stopTime = time.time()

        # Get the returnb pulse start time
        while 0 == GPIO.input(SR04_echo_pin):
                startTime = time.time()
         
        # Get the pulse length
        while 1 == GPIO.input(SR04_echo_pin):
                stopTime = time.time()
         
        elapsedTime = stopTime - startTime
        # The speed of sound is 33120 cm/S or 13039.37 inch/sec.
        # Divide by 2 since this is a round trip
        if (1 == metric):
                d = (elapsedTime * 33120.0) / 2   # metric
        else:
                d = (elapsedTime * 13039.37) / 2   # english
         
        return d

def lcd_init():
  # Initialise display
  lcd_byte(0x33,LCD_CMD) # 110011 Initialise
  lcd_byte(0x32,LCD_CMD) # 110010 Initialise
  lcd_byte(0x06,LCD_CMD) # 000110 Cursor move direction
  lcd_byte(0x0C,LCD_CMD) # 001100 Display On,Cursor Off, Blink Off 
  lcd_byte(0x28,LCD_CMD) # 101000 Data length, number of lines, font size
  lcd_byte(0x01,LCD_CMD) # 000001 Clear display
  time.sleep(E_DELAY)

def lcd_byte(bits, mode):
  # Send byte to data pins
  # bits = the data
  # mode = 1 for data
  #        0 for command

  bits_high = mode | (bits & 0xF0) | LCD_BACKLIGHT
  bits_low = mode | ((bits<<4) & 0xF0) | LCD_BACKLIGHT

  # High bits
  bus.write_byte(I2C_ADDR, bits_high)
  lcd_toggle_enable(bits_high)

  # Low bits
  bus.write_byte(I2C_ADDR, bits_low)
  lcd_toggle_enable(bits_low)

def lcd_toggle_enable(bits):
  # Toggle enable
  time.sleep(E_DELAY)
  bus.write_byte(I2C_ADDR, (bits | ENABLE))
  time.sleep(E_PULSE)
  bus.write_byte(I2C_ADDR,(bits & ~ENABLE))
  time.sleep(E_DELAY)

def lcd_string(message,line):
  # Send string to display

  message = message.ljust(LCD_WIDTH," ")

  lcd_byte(line, LCD_CMD)

  for i in range(LCD_WIDTH):
    lcd_byte(ord(message[i]),LCD_CHR)

# functions not in the original library
def lcd_xy(col, row):
        lcd_byte(LCD_CMD_POSITION+col+(64*row), LCD_CMD)

def lcd_msg(msg_string):
        for i in range(0, len(msg_string)):
                lcd_byte(ord(msg_string[i]), LCD_CHR)

# Remember what the button was so we can see if it changed
prevButton = GPIO.input(ButtonPin)
prevPressTime = time.time()
nextDist = time.time() - 1

#####################################--Executable Code--##################################

pre_init(44100, -16, 1, 1024)
pygame.init()
pygame.mixer.set_num_channels(1)
lcd_init()
lcd_string("  Current Note:", LCD_LINE_1)
while True:
        # append most recent reading to list, then delete the oldest reading, then take the average
        distList.append(distance(False)) # Appends the newest reading to distList
        del distList[0] # Delets the oldest reading from distList
        distAvg = sum(distList) / len(distList) # take the average of all items in distList (take the rolling average)
        distAvgInt = int(distAvg) # take the rolling average and round it to the nearest whole integer
        distAvgIntList.append(distAvgInt) # take the rounded rolling average and append it to distAvgIntList
        print(distAvgInt) # display the current rounded rolling average to the screen
        if abs(distAvgInt - distAvgIntList[-1]) >= 1: # if the reading has changed "note zones"....
            pygame.mixer.stop() # ....stop playing sound

        # if button pressed, change sound mode:
        if 0 == GPIO.input(ButtonPin): # if buton is pressed....
            time.sleep(0.5) # ....wait half a second....
            mode = mode + 1 # ....cycle through to the next set of sounds....
            if mode > (len(playModes) - 1): # ....if the index is more than the length of the list of possible sounds....
                mode = 0 # ....reset the index to 0....
                time.sleep(0.5) # ....then wait half a second

        currentPlayMode = playModes[mode]
        print(currentPlayMode) # debug
            
            # [WIP] Key change toggle notated below:
       ## if 0  == GPIO.input(ButtonPin):
          ##  if currentKey == keyOfC:
          ##      currentKey = keyOfG
       ##     elif currentKey == keyOfG:
        ##        currentKey = keyOfC
       ##     time.sleep(.5)
        #plays notes at distances between 0 and 15 (15 inches is the length of box):
        if distAvgInt <= 1: # if the obstuction (in this case the cardboard paddle) is within the specified distance....
            pygame.mixer.stop() # ....stop playing....
            if currentPlayMode == "bells": # ....if the current set of selected sounds is bells....
                pygame.mixer.Sound(bellSounds[0]).play(-1) # ....play the bell sound....
                lcd_string("Bells       C4", LCD_LINE_2) # ....and display what is being played on the LCD....
                time.sleep(0.8) #....then wait until the sound effect ends....
            if currentPlayMode =="cat": # ....if the current set of selected sounds is cats....
                pygame.mixer.Sound(catSounds[0]).play(-1) # ....play the cat sound....
                lcd_string("Cats       C4", LCD_LINE_2) # ....and display what is being played on the LCD....
                time.sleep(1) #....then wait until the sound effect ends....
            else: # ....if the current set of selected sounds is default....
                Note(currentKey[0]).play(-1) # ....play the default sound.... # Note: c4/g4
                lcd_string("       C4", LCD_LINE_2) # ....and display what is being played on the LCD (this code structure continues for each specified section within the cardbaord box housing)
        elif distAvgInt <= 3 and distAvgInt >= 2:
            pygame.mixer.stop()
            if currentPlayMode == "bells":
                pygame.mixer.Sound(bellSounds[1]).play(-1)
                lcd_string("Bells       D4", LCD_LINE_2)
                time.sleep(0.8)
            if currentPlayMode == "cat":
                pygame.mixer.Sound(catSounds[1]).play(-1)
                lcd_string("Cats       D4", LCD_LINE_2)
                time.sleep(1)
            else:
                Note(currentKey[1]).play(-1) # Note: d4/a4
                lcd_string("       D4", LCD_LINE_2)
        elif distAvgInt <= 5 and distAvgInt >= 4:
            pygame.mixer.stop()
            if currentPlayMode == "bells":
                pygame.mixer.Sound(bellSounds[2]).play(-1)
                lcd_string("Bells       E4", LCD_LINE_2)
                time.sleep(0.8)
            if currentPlayMode == "cat":
                pygame.mixer.Sound(catSounds[2]).play(-1)
                lcd_string("Cats       E4", LCD_LINE_2)
                time.sleep(1)
            else:
                Note(currentKey[2]).play(-1) # Note: e4/b4
                lcd_string("       E4", LCD_LINE_2)
        elif distAvgInt <= 7 and distAvgInt >= 6:
            pygame.mixer.stop()
            if currentPlayMode == "bells":
                pygame.mixer.Sound(bellSounds[3]).play(-1)
                lcd_string("Bells       F4", LCD_LINE_2)
                time.sleep(0.8)
            if currentPlayMode == "cat":
                pygame.mixer.Sound(catSounds[3]).play(-1)
                lcd_string("Cats       F4", LCD_LINE_2)
                time.sleep(1)
            else:
                Note(currentKey[3]).play(-1) # Note: f4/c5
                lcd_string("       F4", LCD_LINE_2)
        elif distAvgInt <= 9 and distAvgInt >= 8:
            pygame.mixer.stop()
            if currentPlayMode == "bells":
                pygame.mixer.Sound(bellSounds[4]).play(-1)
                lcd_string("Bells       G4", LCD_LINE_2)
                time.sleep(0.8)
            if currentPlayMode == "cat":
                pygame.mixer.Sound(catSounds[4]).play(-1)
                lcd_string("Cats       G4", LCD_LINE_2)
                time.sleep(1)
            else:
                Note(currentKey[4]).play(-1) # Note: g4/d5
                lcd_string("       G4", LCD_LINE_2)
        elif distAvgInt <= 11 and distAvgInt >= 10:
            pygame.mixer.stop()
            if currentPlayMode == "bells":
                pygame.mixer.Sound(bellSounds[5]).play(-1)
                lcd_string("Bells       A4", LCD_LINE_2)
                time.sleep(0.8)
            if currentPlayMode == "cat":
                pygame.mixer.Sound(catSounds[5]).play(-1)
                lcd_string("Cats       A4", LCD_LINE_2)
                time.sleep(1)
            else:
                Note(currentKey[5]).play(-1) # Note: a4/e5
                lcd_string("       A4", LCD_LINE_2)
        elif distAvgInt <= 13 and distAvgInt >= 12:
            pygame.mixer.stop()
            if currentPlayMode == "bells":
                pygame.mixer.Sound(bellSounds[6]).play(-1)
                lcd_string("Bells       B4", LCD_LINE_2)
                time.sleep(0.8)
            if currentPlayMode == "cat":
                pygame.mixer.Sound(catSounds[6]).play(-1)
                lcd_string("Cats       B4", LCD_LINE_2)
                time.sleep(1)
            else:
                Note(currentKey[6]).play(-1) # Note: b4/fsharp5
                lcd_string("       B4", LCD_LINE_2)
        elif distAvgInt <= 15 and distAvgInt >= 14:
            pygame.mixer.stop()
            if currentPlayMode == "bells":
                pygame.mixer.Sound(bellSounds[7]).play(-1)
                lcd_string("Bells       C5", LCD_LINE_2)
                time.sleep(0.8)
            if currentPlayMode == "cat":
                pygame.mixer.Sound(catSounds[7]).play(-1)
                lcd_string("Cats       C5", LCD_LINE_2)
                time.sleep(1)
            else:
                Note(currentKey[7]).play(-1) # Note: c5/g5
                lcd_string("       C5", LCD_LINE_2)
        elif distAvgInt > 15:
            lcd_string("     None", LCD_LINE_2)
            pass # continue playing the note you are currently playing; do nothing more
        else: # if anything goes wrong, stop playing
            pygame.mixer.stop()
            Note(1).play(-1) # "play" silence (unhearable tone)
