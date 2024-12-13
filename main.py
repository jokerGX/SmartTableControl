import sys
import cv2
import time
from config import ROI_X1, ROI_X2, ROI_Y1, ROI_Y2, CAMERA_INDEX, PIXEL_THRESHOLD
from gantry import Gantry
from detection import Detector

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

    # Main loop
    first_phone_detected = False
    first_x, first_y, first_conf = None, None, None
    first_frame = None

    while True:
        # Grab a frame
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            continue  # Continue trying until a frame is grabbed

        # If no phone was detected yet, try detecting
        if not first_phone_detected:
            detected_frame, phones = detector.detect(frame)
            if phones:
                # Store the first detection
                first_x, first_y, first_conf = phones[0]
                first_frame = detected_frame
                first_phone_detected = True
                print(f"First phone detected at ({first_x}, {first_y}), Confidence: {first_conf:.2f}")
            else:
                # No phone detected, just continue looping
                continue
        else:
            # A phone was detected before, now attempt second detection
            detected_frame, phones = detector.detect(frame)
            final_x, final_y = first_x, first_y
            if phones:
                second_x, second_y, second_conf = phones[0]
                if abs(second_x - first_x) <= PIXEL_THRESHOLD and abs(second_y - first_y) <= PIXEL_THRESHOLD:
                    print("Second detection matched within pixel threshold. Using second detection coords.")
                else:
                    print("Warning: Second detection does not match first detection coordinates. Still using second coords.")
                final_x, final_y = second_x, second_y
            else:
                print("Warning: No phone detected on second attempt. Using first detection coordinates.")

            # Display final detection frame
            final_display_frame = detected_frame if detected_frame is not None else first_frame
            if final_display_frame is not None:
                cv2.imshow('Final Detection', final_display_frame)
                cv2.waitKey(1)  # Non-blocking show

            # Move gantry
            print(f"Moving gantry to coordinates: ({final_x}, {final_y})")
            gantry.moveVertical()
            time.sleep(1)
            gantry.goTo(final_x, final_y)
            time.sleep(3)
            gantry.moveVertical()
            time.sleep(1)
            gantry.goTo(0, 0)
            
            
            
            # Once done, you may decide to break or continue
            # For this example, we'll break after one successful move
            break

    time.sleep(2)
    gantry.cleanup()
    cap.release()
    cv2.destroyAllWindows()
    print("Pipeline finished.")

if __name__ == "__main__":
    main()
