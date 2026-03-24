import cv2
import math
import time
import mediapipe as mp
import pygame
from collections import deque, Counter

AUDIO_ONE  = "one_finger.mp3"
AUDIO_TWO  = "two_finger.mp3"
AUDIO_PALM = "palm.mp3"

CAM_W, CAM_H = 640, 480
STABLE_FRAMES    = 7
STABLE_MIN_COUNT = 5

pygame.mixer.init()
sound_one  = pygame.mixer.Sound(AUDIO_ONE)
sound_two  = pygame.mixer.Sound(AUDIO_TWO)
sound_palm = pygame.mixer.Sound(AUDIO_PALM)
audio_channel = pygame.mixer.Channel(0)

# 让每首歌循环播放
SOUNDS = {
    "ONE_TOUCH":  sound_one,
    "TWO_TOUCH":  sound_two,
    "PALM_TOUCH": sound_palm,
}

mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=1,
    min_detection_confidence=0.75,
    min_tracking_confidence=0.80,
)

label_buffer     = deque(maxlen=STABLE_FRAMES)
current_label    = "NONE"   # 当前正在播放的姿势

# ── Helpers ────────────────────────────────────────────────────────────────
def get_px(lm, idx, w, h):
    return int(lm[idx].x * w), int(lm[idx].y * h)

def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

FINGER_TIPS = [8, 12, 16, 20]
FINGER_PIPS = [6, 10, 14, 18]

def count_extended_fingers(lm, w, h):
    wrist = get_px(lm, 0, w, h)
    count = 0
    for tip_id, pip_id in zip(FINGER_TIPS, FINGER_PIPS):
        tip = get_px(lm, tip_id, w, h)
        pip = get_px(lm, pip_id, w, h)
        if dist(tip, wrist) > dist(pip, wrist):
            count += 1
    # 拇指
    thumb_tip  = get_px(lm, 4, w, h)
    thumb_ip   = get_px(lm, 3, w, h)
    index_mcp  = get_px(lm, 5, w, h)
    wrist_pt   = get_px(lm, 0, w, h)
    if index_mcp[0] > wrist_pt[0]:
        if thumb_tip[0] < thumb_ip[0]:
            count += 1
    else:
        if thumb_tip[0] > thumb_ip[0]:
            count += 1
    return count

def classify_gesture(lm, w, h):
    n = count_extended_fingers(lm, w, h)
    if n == 1:
        return "ONE_TOUCH", n
    elif n == 2:
        return "TWO_TOUCH", n
    elif n >= 4:
        return "PALM_TOUCH", n
    return "NONE", n

def get_stable_label(current):
    label_buffer.append(current)
    if len(label_buffer) < STABLE_FRAMES:
        return "NONE"
    best, votes = Counter(label_buffer).most_common(1)[0]
    return best if votes >= STABLE_MIN_COUNT else "NONE"

def palm_center(lm, w, h):
    pts = [get_px(lm, i, w, h) for i in [0,1,5,9,13,17]]
    return int(sum(p[0] for p in pts)/6), int(sum(p[1] for p in pts)/6)

# ── 切歌核心函数 ────────────────────────────────────────────────────────────
def switch_music(new_label):
    """只在 label 发生变化时调用，立刻停止旧歌、播新歌（循环）"""
    global current_label
    if new_label == current_label:
        return
    current_label = new_label
    audio_channel.stop()
    if new_label in SOUNDS:
        audio_channel.play(SOUNDS[new_label], loops=-1)  # -1 = 无限循环
    # new_label == "NONE" 时只停止，不播放

# ── Main loop ──────────────────────────────────────────────────────────────
while True:
    ok, frame = cap.read()
    if not ok:
        break

    frame    = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result   = hands.process(rgb)

    label        = "NONE"
    finger_count = 0

    if result.multi_hand_landmarks:
        hl = result.multi_hand_landmarks[0]
        mp_draw.draw_landmarks(frame, hl, mp_hands.HAND_CONNECTIONS)
        lm = hl.landmark

        raw_label, finger_count = classify_gesture(lm, w, h)
        label = get_stable_label(raw_label)

        # 可视化
        if label == "ONE_TOUCH":
            cv2.circle(frame, get_px(lm, 8, w, h), 12, (0,255,255), -1)
        elif label == "TWO_TOUCH":
            cv2.circle(frame, get_px(lm, 8, w, h),  10, (0,255,255), -1)
            cv2.circle(frame, get_px(lm, 12, w, h), 10, (0,255,255), -1)
        elif label == "PALM_TOUCH":
            cv2.circle(frame, palm_center(lm, w, h), 14, (255,0,255), -1)

    else:
        label_buffer.clear()

    # ★ 核心：label 变了就切歌
    switch_music(label)

    # HUD
    colors = {
        "ONE_TOUCH":  (0,255,0),
        "TWO_TOUCH":  (255,255,0),
        "PALM_TOUCH": (0,200,255),
        "NONE":       (180,180,180),
    }
    col = colors.get(label, (180,180,180))
    cv2.putText(frame, f"Fingers : {finger_count}", (20,40),  cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
    cv2.putText(frame, f"Pose    : {label}",        (20,80),  cv2.FONT_HERSHEY_SIMPLEX, 1.0, col, 2)
    cv2.putText(frame, f"Playing : {current_label}",(20,115), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,200,0),  2)

    cv2.imshow("Gesture Audio System", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
hands.close()