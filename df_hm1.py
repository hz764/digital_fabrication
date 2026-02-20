import time
import pygame
import board
import busio
import adafruit_mpr121

HORSE_FILE = "horse.mp3"
SWALLOW_FILE = "swallow.mp3"

MPR121_ADDR = 0x5A
COOLDOWN = 0.4

pygame.mixer.init()
pygame.mixer.music.set_volume(0.3)

i2c = busio.I2C(board.SCL, board.SDA)
mpr = adafruit_mpr121.MPR121(i2c, address=MPR121_ADDR)

last_trigger = 0

def play(file):
    global last_trigger
    now = time.time()
    if now - last_trigger < COOLDOWN:
        return
    last_trigger = now
    pygame.mixer.music.load(file)
    pygame.mixer.music.play()

print("Touch 6 for horse, 9 for swallow")

while True:
    if mpr[6].value:
        play(HORSE_FILE)
    if mpr[9].value:
        play(SWALLOW_FILE)
    time.sleep(0.02)
