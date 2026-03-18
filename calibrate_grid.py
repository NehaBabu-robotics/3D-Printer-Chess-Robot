import cv2
import numpy as np
import json
import os

# --- SETTINGS ---
STREAM_URL = 'http://localhost:8080/?action=stream'
CALIB_FILE = 'calibration_settings.json' # Stores the 4 math numbers
GAME_FILE = 'grid_config.json'           # Stores the 64 square points

def load_settings():
    if os.path.exists(CALIB_FILE):
        with open(CALIB_FILE, 'r') as f:
            return json.load(f)
    # Default starting point
    return {"offset_x": 100, "offset_y": 50, "scale_x": 200, "scale_y": 200}

def save_everything(settings, field_positions):
    # Save the math settings so we can run the script again
    with open(CALIB_FILE, 'w') as f:
        json.dump(settings, f)
    # Save the final points for the actual chess game
    with open(GAME_FILE, 'w') as f:
        json.dump(field_positions, f)
    print(f"Saved calibration to {CALIB_FILE} and grid to {GAME_FILE}")

def main():
    settings = load_settings()
    cap = cv2.VideoCapture(STREAM_URL)
    
    print("\n--- GRID CALIBRATION ---")
    print("WASD : Move Grid")
    print("IKJL : Stretch/Shrink Grid")
    print("Shift + S : Save and Exit")
    print("Q : Quit without saving")

    while True:
        ret, frame = cap.read()
        if not ret: 
            print("Failed to grab frame. Check OctoPrint stream.")
            break

        field_positions = {}
        for i in range(8):
            for j in range(8):
                # Calculate coordinates based on scale and offset
                px = int(settings["offset_x"] + (j * (settings["scale_x"] / 7)))
                py = int(settings["offset_y"] + (i * (settings["scale_y"] / 7)))
                
                label = chr(ord('a') + j) + str(8 - i)
                field_positions[label] = [px, py]
                
                # Draw visual aids
                cv2.circle(frame, (px, py), 4, (0, 255, 0), -1)
                cv2.putText(frame, label, (px + 5, py - 5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

        cv2.imshow("Calibrate Grid", frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        # Move Grid (WASD)
        if key == ord('w'): settings["offset_y"] -= 1
        if key == ord('s'): settings["offset_y"] += 1
        if key == ord('a'): settings["offset_x"] -= 1
        if key == ord('d'): settings["offset_x"] += 1
        
        # Scale Grid (IKJL)
        if key == ord('i'): settings["scale_y"] -= 1
        if key == ord('k'): settings["scale_y"] += 1
        if key == ord('j'): settings["scale_x"] -= 1
        if key == ord('l'): settings["scale_x"] += 1
        
        # --- Save and Exit (Press 'ENTER' or 'v') ---
        elif key == 13 or key == ord('v'): 
            save_everything(settings, field_positions)
            print("Save triggered!")
            break
            
        # --- Quit (Press 'ESC' or 'q') ---
        elif key == 27 or key == ord('q'):
            print("Exit without saving.")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()