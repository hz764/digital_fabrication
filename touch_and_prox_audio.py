import time
import threading

import board
import busio
import pygame

import adafruit_mpr121
from adafruit_apds9960.apds9960 import APDS9960

TOUCH_WAV = "0213.wav"
PROX_WAV  = "0206.wav"

MPR121_ADDR = 0x5A
APDS_ADDR   = 0x39

PROX_TRIGGER = 60
PROX_RELEASE = 40

TOUCH_COOLDOWN = 0.30
PROX_COOLDOWN  = 0.60

LOCK_WHILE_PLAYING = True
POLL_DELAY = 0.02


class AudioPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.lock = threading.Lock()
        self.last = {"touch": 0.0, "prox": 0.0}

    def play(self, path, key, cooldown):
        now = time.time()
        if now - self.last[key] < cooldown:
            return
        if LOCK_WHILE_PLAYING and pygame.mixer.get_busy():
            return
        with self.lock:
            self.last[key] = now
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()


def i2c_scan(i2c):
    while not i2c.try_lock():
        time.sleep(0.01)
    try:
        return list(i2c.scan())
    finally:
        i2c.unlock()


def init_mpr121(i2c, addrs):
    if MPR121_ADDR not in addrs:
        print(f"MPR121 not found at {hex(MPR121_ADDR)}")
        return None
    try:
        dev = adafruit_mpr121.MPR121(i2c, address=MPR121_ADDR)
        print("MPR121 ready")
        return dev
    except Exception as e:
        print("MPR121 init failed:", e)
        return None


def init_apds(i2c, addrs):
    if APDS_ADDR not in addrs:
        print(f"APDS9960 not found at {hex(APDS_ADDR)}")
        return None
    try:
        dev = APDS9960(i2c)
        dev.enable_proximity = True
        print("APDS9960 ready")
        return dev
    except Exception as e:
        print("APDS9960 init failed:", e)
        return None


def main():
    i2c = busio.I2C(board.SCL, board.SDA)

    addrs = i2c_scan(i2c)
    print("I2C scan:", [hex(a) for a in addrs])

    mpr = init_mpr121(i2c, addrs)
    apds = init_apds(i2c, addrs)

    player = AudioPlayer()

    last_touch = False
    prox_armed = True

    while True:
        if mpr is not None:
            touched = any(mpr[i].value for i in range(12))
            if touched and not last_touch:
                player.play(TOUCH_WAV, "touch", TOUCH_COOLDOWN)
            last_touch = touched

        if apds is not None:
            try:
                prox = apds.proximity
            except Exception:
                prox = 0

            if prox_armed and prox >= PROX_TRIGGER:
                player.play(PROX_WAV, "prox", PROX_COOLDOWN)
                prox_armed = False

            if (not prox_armed) and prox <= PROX_RELEASE:
                prox_armed = True

        time.sleep(POLL_DELAY)


if __name__ == "__main__":
    main()
