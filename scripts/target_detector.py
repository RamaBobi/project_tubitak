import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import cv2
import numpy as np

# --- THE SHAPE DETECTION LOGIC ---
def detect_square_target(mask, frame, color_name):
    # 1. Clean the noise
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # 2. Find the contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 50: # Lowered the threshold to catch it further away
            continue

        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)

        if hull_area == 0:
            continue

        solidity = float(area) / hull_area

        if solidity > 0.85:
            rect = cv2.minAreaRect(contour)
            center_x = int(rect[0][0])
            center_y = int(rect[0][1])

            # Draw the rotated box for visuals
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            cv2.drawContours(frame, [box], 0, (0, 255, 0), 2)
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            
            return center_x, center_y, frame
    return None, None, frame

# --- THE ROS 2 NODE ---
class TargetDetector(Node):
    def __init__(self):
        super().__init__('target_detector')
        
        self.subscription = self.create_subscription(Image, '/camera/image', self.image_callback, 10)
        self.bridge = CvBridge()
        
        # Blue HSV Limits
        self.lower_blue = np.array([100, 150, 50])
        self.upper_blue = np.array([150, 255, 255])
        
        # Red HSV Limits (Requires two ranges)
        self.lower_red1 = np.array([0, 150, 50])
        self.upper_red1 = np.array([10, 255, 255])
        self.lower_red2 = np.array([170, 150, 50])
        self.upper_red2 = np.array([179, 255, 255])
        
        self.get_logger().info("Dual-Target Vision Node Started. Scanning for Red and Blue...")

    def image_callback(self, msg):
        try:
            bgr_frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except CvBridgeError as e:
            self.get_logger().error(f"CV Bridge Error: {e}")
            return

        resized_frame = cv2.resize(bgr_frame, (640, 480))
        hsv_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2HSV)

        # 1. Process Blue
        blue_mask = cv2.inRange(hsv_frame, self.lower_blue, self.upper_blue)
        blue_x, blue_y, processed_frame = detect_square_target(blue_mask, resized_frame, "Blue")

        # 2. Process Red (Stitch the two masks together)
        mask_red1 = cv2.inRange(hsv_frame, self.lower_red1, self.upper_red1)
        mask_red2 = cv2.inRange(hsv_frame, self.lower_red2, self.upper_red2)
        red_mask = cv2.bitwise_or(mask_red1, mask_red2)
        red_x, red_y, processed_frame = detect_square_target(red_mask, processed_frame, "Red")

        # 3. Log Detections
        if blue_x is not None:
            self.get_logger().info(f"Blue Target at X: {blue_x}, Y: {blue_y}")
        if red_x is not None:
            self.get_logger().info(f"Red Target at X: {red_x}, Y: {red_y}")

        # Debug Visuals (Disable for flight)
       # --- DEBUG VISUALS ---
        # WARNING: Disable these before the actual flight to save CPU
        cv2.imshow("Drone Targeting Camera", processed_frame)
        cv2.imshow("Blue Binary Mask", blue_mask)
        cv2.imshow("Red Binary Mask", red_mask)
        cv2.waitKey(1)

def main(args=None):
    rclpy.init(args=args)
    node = TargetDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
