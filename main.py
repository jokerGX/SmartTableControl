# main.py
import sys
import cv2
import time
import math
import numpy as np

from config import ROI_X1, ROI_X2, ROI_Y1, ROI_Y2, CAMERA_INDEX, PIXEL_THRESHOLD
from gantry import Gantry
from detection import Detector

def distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def detect_red_lights_in_frame(frame, debug=False):
    """
    Detect red lights in a frame (numpy array) and return their coordinates.
    The frame should already be cropped and rotated if needed to maintain
    coordinate consistency.
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Define range for red color
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])

    # Create masks for red color
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)

    # Noise reduction
    kernel = np.ones((3,3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    red_light_coordinates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 5:
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                red_light_coordinates.append((cx, cy))

    if debug:
        debug_frame = frame.copy()
        for (x,y) in red_light_coordinates:
            cv2.circle(debug_frame, (x, y), 5, (0,255,0), -1)
        cv2.imshow("Red Light Detection", debug_frame)
        cv2.waitKey(1)

    return red_light_coordinates

def main():
    gantry = Gantry(initial_x=0.0, initial_y=0.0)
    detector = Detector()

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Error: Cannot open webcam.")
        sys.exit(1)

    # Validate ROI
    ret, test_frame = cap.read()
    if not ret:
        print("Error: Cannot read from webcam.")
        cap.release()
        sys.exit(1)
    frame_height, frame_width = test_frame.shape[:2]
    if not (0 <= ROI_X1 < ROI_X2 <= frame_width) or not (0 <= ROI_Y1 < ROI_Y2 <= frame_height):
        print("Error: ROI coordinates are out of frame bounds.")
        cap.release()
        sys.exit(1)

    # Calculate rotated_frame dimensions
    roi_width = ROI_X2 - ROI_X1
    roi_height = ROI_Y2 - ROI_Y1
    rotated_frame_width = roi_height
    rotated_frame_height = roi_width

    # Define charging pads
    charging_pads = [
        {"coords": (0, 0), "available": True},
        {"coords": (rotated_frame_width - 1, 0), "available": True},
        {"coords": (0, rotated_frame_height - 1), "available": True},
        {"coords": (rotated_frame_width - 1, rotated_frame_height - 1), "available": True}
    ]

    # Track where pads have been placed: {(px, py): pad_index}
    placed_pads = {}

    # Track occupied zones for charged phones:
    # {(px, py): radius} - currently using radius=70
    occupied_zones = {}

    while True:
        ########################################
        # 1) PHONE DETECTION (DOUBLE DETECTION) 
        ########################################
        print("Performing first detection...")
        first_phones = []
        start_time = time.time()
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame.")
                if time.time() - start_time > 10:
                    break
                continue
            detected_frame, phones = detector.detect(frame)
            if phones:
                first_phones = phones
                # Optional display
                if detected_frame is not None:
                    cv2.imshow('First Detection', detected_frame)
                    cv2.waitKey(1)
                print(f"First detection found {len(first_phones)} phone(s).")
                break
            else:
                if time.time() - start_time > 5:
                    # No phones found for 5 seconds, continue loop
                    break
                continue

        if not first_phones:
            # No phones found, skip double detection and proceed to red light detection
            pass
        else:
            print("Performing second detection for confirmation...")
            second_phones = []
            start_time = time.time()
            while True:
                ret, frame = cap.read()
                if not ret:
                    if time.time() - start_time > 6:
                        break
                    continue
                detected_frame, phones = detector.detect(frame)
                second_phones = phones if phones else []
                
                # Match second detection to first detection by proximity
                final_phones = []
                unmatched_second = second_phones[:]

                for (fx, fy, fconf) in first_phones:
                    matched = False
                    for s in unmatched_second:
                        sx, sy, sconf = s
                        if abs(sx - fx) <= PIXEL_THRESHOLD and abs(sy - fy) <= PIXEL_THRESHOLD:
                            final_phones.append((sx, sy))
                            unmatched_second.remove(s)
                            matched = True
                            break
                    if not matched:
                        final_phones.append((fx, fy))

                # Filter out phones that fall inside any occupied zone
                # If a phone is within radius 70 of any occupied zone center, ignore it
                filtered_phones = []
                for (px, py) in final_phones:
                    in_occupied_zone = False
                    for (ox, oy), radius in occupied_zones.items():
                        if distance((px, py), (ox, oy)) <= radius:
                            in_occupied_zone = True
                            break
                    if not in_occupied_zone:
                        filtered_phones.append((px, py))

                if filtered_phones:
                    # Optional display
                    if detected_frame is not None:
                        cv2.imshow('Final Detection', detected_frame)
                        cv2.waitKey(1)
                    print(f"Final confirmed {len(filtered_phones)} phone(s) (after filtering occupied zones).")

                    # For each confirmed phone, find closest available charging pad and execute sequence:
                    for (px, py) in filtered_phones:
                        available_pads = [p for p in charging_pads if p["available"]]
                        if not available_pads:
                            print("No available charging pads. Skipping this phone...")
                            continue

                        # Closest pad by Euclidean distance
                        closest_pad = min(available_pads, key=lambda p: distance(p["coords"], (px, py)))
                        cpx, cpy = closest_pad["coords"]
                        pad_index = charging_pads.index(closest_pad)

                        # Move sequence:
                        print(f"Moving gantry to charging pad at ({cpx}, {cpy}) horizontally...")
                        gantry.goTo(cpx, cpy)
                        time.sleep(1)

                        print("Moving vertical to pick the charging pad...")
                        gantry.moveVertical()  
                        time.sleep(1)

                        print(f"Moving gantry to phone location at ({px}, {py}) horizontally...")
                        gantry.goTo(px, py)
                        time.sleep(1)

                        print("Moving vertical to place the charging pad on the phone location...")
                        gantry.moveVertical()  
                        time.sleep(1)

                        # Mark the pad as unavailable and record its placed location
                        closest_pad["available"] = False
                        placed_pads[(px, py)] = pad_index

                        # Add an occupied zone around this phone location
                        occupied_zones[(px, py)] = 70

                        print("Returning gantry to home position (0,0)...")
                        gantry.goTo(0, 0)
                        time.sleep(1)

                    break
                else:
                    # No final phones determined or all filtered out by occupied zones
                    if time.time() - start_time > 10:
                        break

        ########################################
        # 2) RED LIGHT DETECTION
        ########################################
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame for red light detection.")
            continue

        # Crop and rotate frame
        cropped_frame = frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]
        rotated_frame = cv2.rotate(cropped_frame, cv2.ROTATE_90_CLOCKWISE)

        red_lights = detect_red_lights_in_frame(rotated_frame, debug=False)
        RED_LIGHT_THRESHOLD = 30
        to_retrieve = []
        for (px, py), pad_index in placed_pads.items():
            if pad_index < len(charging_pads):
                pad_info = charging_pads[pad_index]
                if not pad_info["available"]:
                    for (rx, ry) in red_lights:
                        if distance((rx, ry), (px, py)) <= RED_LIGHT_THRESHOLD:
                            # Found a red light at the placed pad location -> Retrieve pad
                            to_retrieve.append(((px, py), pad_index))
                            break

        # Retrieve pads for all matched red lights
        for ((px, py), pad_index) in to_retrieve:
            pad_info = charging_pads[pad_index]
            if not pad_info["available"]:
                # Retrieve pad sequence:
                print(f"Going to placed pad at ({px},{py}) to retrieve it.")
                gantry.goTo(px, py)
                time.sleep(1)

                print("Moving vertical down to pick up the pad...")
                gantry.moveVertical()
                time.sleep(1)

                original_px, original_py = pad_info["coords"]
                print(f"Moving pad back to original location at ({original_px},{original_py})...")
                gantry.goTo(original_px, original_py)
                time.sleep(1)

                print("Moving vertical up to release the pad...")
                gantry.moveVertical()
                time.sleep(1)

                # Mark pad as available again
                pad_info["available"] = True

                # Remove from placed_pads
                del placed_pads[(px, py)]

                # Remove occupied zone for this location
                if (px, py) in occupied_zones:
                    del occupied_zones[(px, py)]

                print("Returning to home (0,0)...")
                gantry.goTo(0, 0)
                time.sleep(1)

        time.sleep(0.5)

    # Cleanup if ever breaks
    gantry.cleanup()
    cap.release()
    cv2.destroyAllWindows()
    print("Pipeline finished.")

if __name__ == "__main__":
    main()
