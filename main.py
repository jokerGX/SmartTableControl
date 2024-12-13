# main.py
import sys
import cv2
import time
from config import ROI_X1, ROI_X2, ROI_Y1, ROI_Y2, CAMERA_INDEX, PIXEL_THRESHOLD
from gantry import Gantry
from detection import Detector
import math

def distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

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
    # After rotation by 90 degrees clockwise:
    # rotated_frame width = roi_height
    # rotated_frame height = roi_width
    rotated_frame_width = roi_height
    rotated_frame_height = roi_width

    # Define charging pads at the four corners of the rotated frame
    charging_pads = [
        {"coords": (0, 0), "available": True},
        {"coords": (rotated_frame_width - 1, 0), "available": True},
        {"coords": (0, rotated_frame_height - 1), "available": True},
        {"coords": (rotated_frame_width - 1, rotated_frame_height - 1), "available": True}
    ]

    # Step 1: Perform first detection to find phones
    print("Performing first detection...")
    first_phones = []
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            continue
        detected_frame, phones = detector.detect(frame)
        if phones:
            first_phones = phones
            # Display intermediate detection (optional)
            if detected_frame is not None:
                cv2.imshow('First Detection', detected_frame)
                cv2.waitKey(1)
            print(f"First detection found {len(first_phones)} phone(s).")
            break
        else:
            continue

    # Step 2: Perform second detection to confirm phone positions
    print("Performing second detection for confirmation...")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
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

        if final_phones:
            # Display final detection frame
            if detected_frame is not None:
                cv2.imshow('Final Detection', detected_frame)
                cv2.waitKey(1)
            print(f"Final confirmed {len(final_phones)} phone(s).")

            # For each confirmed phone, find closest available charging pad and execute sequence:
            for (px, py) in final_phones:
                available_pads = [p for p in charging_pads if p["available"]]
                if not available_pads:
                    print("No available charging pads. Skipping...")
                    continue

                # Closest pad by Euclidean distance
                closest_pad = min(available_pads, key=lambda p: distance(p["coords"], (px, py)))
                cpx, cpy = closest_pad["coords"]

                # Sequence as requested:
                # 1) Go to charging pad horizontally (no vertical move)
                print(f"Moving gantry to charging pad at ({cpx}, {cpy}) horizontally...")
                gantry.goTo(cpx, cpy)
                time.sleep(1)

                # 2) Move vertical (down) to pick up the charging pad
                print("Moving vertical to pick the charging pad...")
                gantry.moveVertical()  
                time.sleep(1)

                # 3) Move directly to phone location horizontally (still down)
                print(f"Moving gantry to phone location at ({px}, {py}) horizontally...")
                gantry.goTo(px, py)
                time.sleep(1)

                # 4) Move vertical (up) to place the pad at the phone location
                print("Moving vertical to place the charging pad on the phone location...")
                gantry.moveVertical()  
                time.sleep(1)

                # Mark the pad as unavailable after placing
                closest_pad["available"] = False

                # 5) Return to home position horizontally
                print("Returning gantry to home position (0,0)...")
                gantry.goTo(0, 0)
                time.sleep(1)

            break
        else:
            # No final phones determined, try again (unlikely scenario)
            continue

    time.sleep(2)
    gantry.cleanup()
    cap.release()
    cv2.destroyAllWindows()
    print("Pipeline finished.")

if __name__ == "__main__":
    main()
