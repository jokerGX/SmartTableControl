import requests
import cv2
import json
import time
import numpy as np
from config import API_URL, API_KEY, ROI_X1, ROI_Y1, ROI_X2, ROI_Y2

class Detector:
    def __init__(self):
        pass

    def rotate_image(self, image: np.ndarray, angle: int = 90) -> np.ndarray:
        if angle == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, -angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h))
            return rotated

    def send_image(self, image: bytes):
        headers = {"api_key": API_KEY}
        files = {"file": ("frame.jpg", image, "image/jpeg")}
        try:
            print("Sending frame to the API...")
            start_time = time.perf_counter()
            response = requests.post(API_URL, headers=headers, files=files, timeout=60)
            end_time = time.perf_counter()
            time_taken = end_time - start_time
            response.raise_for_status()
            print(f"Frame sent successfully. Received response in {time_taken:.2f} seconds.")
            return response.json(), time_taken
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            if response and response.content:
                print(f"Response content: {response.text}")
            return None, None
        except requests.exceptions.ConnectionError:
            print("Error: Failed to connect to the API server. Please check your network connection and API endpoint.")
            return None, None
        except requests.exceptions.Timeout:
            print("Error: The request timed out. The server may be busy or unresponsive.")
            return None, None
        except requests.exceptions.RequestException as err:
            print(f"An unexpected error occurred: {err}")
            return None, None

    def process_response(self, response: dict, cropped_frame: np.ndarray):
        if not response:
            return []

        print("\n--- Detection Results ---")
        detected_phones = []

        if "phones" in response:
            phones = response["phones"]
            if phones:
                print(f"\nDetected {len(phones)} phone(s) in the frame:\n")
                for idx, phone in enumerate(phones, start=1):
                    coords = phone.get("coordinates", {})
                    center = phone.get("center", {})
                    confidence = phone.get("confidence", 0)
                    required_keys = {'x1', 'y1', 'x2', 'y2'}
                    if not required_keys.issubset(coords.keys()) or not {'x', 'y'}.issubset(center.keys()):
                        print(f"Phone {idx}: Incomplete coordinate data. Skipping.")
                        continue

                    try:
                        x1 = int(round(coords['x1']))
                        y1 = int(round(coords['y1']))
                        x2 = int(round(coords['x2']))
                        y2 = int(round(coords['y2']))
                        center_x = int(round(center['x']))
                        center_y = int(round(center['y']))

                        print(f"Phone {idx}:")
                        print(f"  Bounding Box -> x1: {x1}, y1: {y1}, x2: {x2}, y2: {y2}")
                        print(f"  Center -> x: {center_x}, y: {center_y}")
                        print(f"  Confidence: {confidence:.2f}\n")

                        cv2.rectangle(cropped_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.circle(cropped_frame, (center_x, center_y), 5, (0, 0, 255), -1)
                        label_confidence = f"Conf: {confidence:.2f}"
                        cv2.putText(cropped_frame, label_confidence, (x1, y1 - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                        label_coords = f"Box: ({x1}, {y1}), ({x2}, {y2})"
                        text_size, _ = cv2.getTextSize(label_coords, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                        text_width, text_height = text_size
                        text_x = x1
                        text_y = y1 - 25 if y1 - 25 > text_height else y1 + text_height + 25

                        cv2.rectangle(cropped_frame, (text_x, text_y - text_height - 5), 
                                      (text_x + text_width + 10, text_y + 5), (0, 255, 0), cv2.FILLED)
                        cv2.putText(cropped_frame, label_coords, (text_x + 5, text_y), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

                        label_center = f"Center: ({center_x}, {center_y})"
                        text_size_center, _ = cv2.getTextSize(label_center, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                        text_width_center, text_height_center = text_size_center
                        text_x_center = center_x + 10 if center_x + 10 + text_width_center < cropped_frame.shape[1] else center_x - text_width_center - 10
                        text_y_center = center_y + 10 if center_y + 10 + text_height_center < cropped_frame.shape[0] else center_y - 10

                        cv2.rectangle(cropped_frame, (text_x_center, text_y_center - text_height_center - 5), 
                                      (text_x_center + text_width_center + 10, text_y_center + 5), 
                                      (0, 0, 255), cv2.FILLED)

                        cv2.putText(cropped_frame, label_center, (text_x_center + 5, text_y_center), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                        detected_phones.append((center_x, center_y, confidence))

                    except (ValueError, TypeError) as e:
                        print(f"Error processing phone {idx} coordinates: {e}")
                        continue
            else:
                print("No phones detected in the frame.")
        elif "message" in response:
            print(f"Message from API: {response['message']}")
        else:
            print("Unexpected response format:")
            print(json.dumps(response, indent=4))

        return detected_phones

    def detect(self, frame: np.ndarray):
        cropped_frame = frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]
        rotated_frame = self.rotate_image(cropped_frame, angle=90)

        # Encode rotated frame
        ret, buffer = cv2.imencode('.jpg', rotated_frame)
        if not ret:
            print("Failed to encode frame.")
            return None, None

        image_bytes = buffer.tobytes()
        response, _ = self.send_image(image_bytes)
        detected_phones = self.process_response(response, rotated_frame)

        return rotated_frame, detected_phones
