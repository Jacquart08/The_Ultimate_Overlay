import keyboard
import time

print("Press Ctrl (Ctrl+C to exit)")
while True:
    if keyboard.is_pressed('ctrl'):
        print("Ctrl is pressed")
    else:
        print("Ctrl is not pressed")
    time.sleep(0.5)