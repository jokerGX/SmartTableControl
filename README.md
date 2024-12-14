# Smart Charging Table

## Overview
The **Smart Charging Table** is a solution to modern charging problems. Place your phone anywhere on the table, and it automatically detects your phone's position, moves a charging pad to it, and starts charging. No wires, no precise alignment needed.

## Key Features
- **Automatic Detection:** YOLOv5 detects your phone's location.
- **Dynamic Charging:** Gantry system moves the charging pad to your phone.
- **Multiple Charging:** Supports up to 4 phones at once.
- **Non-Phone Filtering:** Ignores objects like laptops or books.
- **Auto Reset:** Charging pads return to home position when not in use.
- **Real-Time Monitoring:** Check status via iOS, macOS, or web apps.

## How It Works
### General Explanation
1. Place your phone anywhere on the table.
2. The system detects the phone and moves the charging pad to it.
3. Charging starts automatically.
4. Use our apps to monitor progress.
5. When charging is done or the phone is removed, the pad resets.

### Technical Details
- **Vision System:** Uses YOLOv5, a state-of-the-art object detection model, to identify phones and their precise location on the table. The model is deployed on the cloud to ensure fast and accurate detection.
- **Gantry System:** The system features a 3-DOF (three degrees of freedom) gantry controlled by stepper motors. A PID controller ensures precise and smooth movement of the charging pad.
- **Object Filtering:** Non-phone objects like laptops, books, or coffee mugs are ignored using advanced classification algorithms.
- **Concurrent Charging:** The table supports up to 4 charging pads, each operating independently to maximize efficiency.
- **Auto Reset Mechanism:** An embedded controller detects when a phone is removed or fully charged and sends the pad back to the home position to conserve energy and minimize wear.

## Why It’s Better
- **No cables:** Freedom from cable length constraints.
- **No alignment hassle:** Charge your phone anywhere on the table.
- **Efficient Multi-Device Support:** Charge multiple devices without interference.
- **Real-Time Monitoring:** Stay informed about charging progress at all times.

## Apps
- **iOS App:** [GitHub Repository](https://github.com/jokerGX/chargingApp)
  - Monitor your phone’s charging status in real time.
- **macOS App:** [GitHub Repository](https://github.com/jokerGX/chargingMonitor)
  - Manage and monitor multiple devices on your Mac.
- **Web App:** [GitHub Repository](https://github.com/jokerGX/Device-DashBoard)
  - Access charging details from any browser.

## Technologies Used
- **YOLOv5:** Phone detection and classification.
- **Gantry System:** High-precision movement for charging pads.
- **PID Control:** Ensures smooth and accurate gantry movement.
- **Firebase:** Real-time updates and data synchronization.
- **Cloud Computing:** Enables fast detection and system responsiveness.

## Repository
GitHub: [SmartTableControl](https://github.com/jokerGX/SmartTableControl)

## Contact
For support, email [your_email@example.com].

