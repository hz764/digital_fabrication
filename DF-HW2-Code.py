import board
import busio
import adafruit_mpr121
import pygame
import RPi.GPIO as GPIO
import time

AUDIO_P1_ONE  = "R1.mp3"
AUDIO_P1_TWO  = "R2.mp3"
AUDIO_P1_PALM = "R3.mp3"
AUDIO_P2_ONE  = "L1.mp3"
AUDIO_P2_TWO  = "L2.mp3"
AUDIO_P2_PALM = "L3.mp3"

MPR121_ELE_PART1 = 0
MPR121_ELE_PART2 = 1

MOTOR_PIN_LEFT  = 11
MOTOR_PIN_RIGHT = 13

GPIO.setmode(GPIO.BOARD)
GPIO.setup(MOTOR_PIN_LEFT,  GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(MOTOR_PIN_RIGHT, GPIO.OUT, initial=GPIO.LOW)

pygame.mixer.init()
sound_p1_one  = pygame.mixer.Sound(AUDIO_P1_ONE)
sound_p1_two  = pygame.mixer.Sound(AUDIO_P1_TWO)
sound_p1_palm = pygame.mixer.Sound(AUDIO_P1_PALM)
sound_p2_one  = pygame.mixer.Sound(AUDIO_P2_ONE)
sound_p2_two  = pygame.mixer.Sound(AUDIO_P2_TWO)
sound_p2_palm = pygame.mixer.Sound(AUDIO_P2_PALM)

audio_channel = pygame.mixer.Channel(0)

SOUNDS = {
    ("PART1", "ONE_TOUCH"):  sound_p1_one,
    ("PART1", "TWO_TOUCH"):  sound_p1_two,
    ("PART1", "PALM_TOUCH"): sound_p1_palm,
    ("PART2", "ONE_TOUCH"):  sound_p2_one,
    ("PART2", "TWO_TOUCH"):  sound_p2_two,
    ("PART2", "PALM_TOUCH"): sound_p2_palm,
}

i2c    = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

current_key  = ("NONE", "NONE")
current_part = "NONE"

def read_touch_part():
    if mpr121[MPR121_ELE_PART1].value:
        return "PART1"
    elif mpr121[MPR121_ELE_PART2].value:
        return "PART2"
    return "NONE"

def update_motors(part):
    global current_part
    if part == current_part:
        return
    current_part = part
    if part == "PART1":
        GPIO.output(MOTOR_PIN_LEFT,  GPIO.HIGH)
        GPIO.output(MOTOR_PIN_RIGHT, GPIO.LOW)
    elif part == "PART2":
        GPIO.output(MOTOR_PIN_LEFT,  GPIO.LOW)
        GPIO.output(MOTOR_PIN_RIGHT, GPIO.HIGH)
    else:
        GPIO.output(MOTOR_PIN_LEFT,  GPIO.LOW)
        GPIO.output(MOTOR_PIN_RIGHT, GPIO.LOW)

def switch_music(new_part, new_gesture):
    global current_key
    new_key = (new_part, new_gesture)
    if new_key == current_key:
        return
    current_key = new_key
    audio_channel.stop()
    if new_key in SOUNDS:
        audio_channel.play(SOUNDS[new_key], loops=-1)

try:
    while True:
        active_part = read_touch_part()
        update_motors(active_part)
        if active_part != "NONE":
            switch_music(active_part, "ONE_TOUCH")
        else:
            switch_music("NONE", "NONE")
        time.sleep(0.05)

except KeyboardInterrupt:
    pass

finally:
    audio_channel.stop()
    GPIO.output(MOTOR_PIN_LEFT,  GPIO.LOW)
    GPIO.output(MOTOR_PIN_RIGHT, GPIO.LOW)
    GPIO.cleanup()
    pygame.mixer.quit()
