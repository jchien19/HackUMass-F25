import cv2
import mediapipe as mp
import numpy as np

class EyeTracker:
    def __init__(self):
        # Initialize MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Eye landmark indices for MediaPipe Face Mesh, look for these online
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        
        # Define screen attention zone (center box)
        self.looking_at_screen = False
        
    def get_eye_center(self, landmarks, eye_indices, img_w, img_h):
        """Calculate the center point of eye landmarks"""
        x_coords = [landmarks[idx].x * img_w for idx in eye_indices]
        y_coords = [landmarks[idx].y * img_h for idx in eye_indices]
        return (int(np.mean(x_coords)), int(np.mean(y_coords)))
    
    def get_iris_position(self, landmarks, iris_indices, img_w, img_h):
        """Get iris center position"""
        x_coords = [landmarks[idx].x * img_w for idx in iris_indices]
        y_coords = [landmarks[idx].y * img_h for idx in iris_indices]
        return (int(np.mean(x_coords)), int(np.mean(y_coords)))
    
    def calculate_gaze_ratio(self, eye_center, iris_center):
        """Calculate the ratio of iris offset from eye center"""
        dx = iris_center[0] - eye_center[0]
        dy = iris_center[1] - eye_center[1]
        # distance = np.sqrt(dx**2 + dy**2)
        return dx, dy #, distance
    
    def is_looking_at_screen(self, left_eye_center, right_eye_center, 
                            left_iris, right_iris, frame_shape):
        """Check if user is looking at screen based on iris-to-eye-center distance"""
        # Calculate gaze ratios for both eyes
        # left_dx, left_dy, left_dist = self.calculate_gaze_ratio(left_eye_center, left_iris)
        # right_dx, right_dy, right_dist = self.calculate_gaze_ratio(right_eye_center, right_iris)
        left_dx, left_dy = self.calculate_gaze_ratio(left_eye_center, left_iris)
        right_dx, right_dy = self.calculate_gaze_ratio(right_eye_center, right_iris)
        
        # Thresholds for "looking at screen" (adjust these based on testing)
        # Lower values = more strict (must look more directly)
        # Higher values = more lenient
        horizontal_threshold = 4  # pixels
        vertical_threshold = 3    # pixels
        
        # Check if iris is relatively centered in both eyes
        left_centered = (abs(left_dx) < horizontal_threshold and 
                        abs(left_dy) < vertical_threshold)
        right_centered = (abs(right_dx) < horizontal_threshold and 
                         abs(right_dy) < vertical_threshold)
        
        return left_centered and right_centered
    
    def process_frame(self, frame):
        """Process a single frame and detect eye position"""
        img_h, img_w = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]
            landmarks = face_landmarks.landmark
            
            # Get eye centers
            left_eye_center = self.get_eye_center(landmarks, self.LEFT_EYE, img_w, img_h)
            right_eye_center = self.get_eye_center(landmarks, self.RIGHT_EYE, img_w, img_h)
            
            # Get iris positions
            left_iris = self.get_iris_position(landmarks, self.LEFT_IRIS, img_w, img_h)
            right_iris = self.get_iris_position(landmarks, self.RIGHT_IRIS, img_w, img_h)
            
            # Draw eye regions (larger circles for eye centers)
            cv2.circle(frame, left_eye_center, 8, (0, 255, 255), 2)
            cv2.circle(frame, right_eye_center, 8, (0, 255, 255), 2)
            
            # Draw iris positions
            cv2.circle(frame, left_iris, 5, (255, 0, 0), -1)
            cv2.circle(frame, right_iris, 5, (255, 0, 0), -1)
            
            # Draw lines from eye center to iris (showing offset)
            cv2.line(frame, left_eye_center, left_iris, (0, 255, 0), 2)
            cv2.line(frame, right_eye_center, right_iris, (0, 255, 0), 2)
            
            # Check if looking at screen
            self.looking_at_screen = self.is_looking_at_screen(
                left_eye_center, right_eye_center, 
                left_iris, right_iris, 
                frame.shape
            )
        
            # Display status
            status = "Looking at screen" if self.looking_at_screen else "Not looking at screen"
            color = (0, 255, 0) if self.looking_at_screen else (0, 0, 255)
            cv2.putText(frame, status, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            return frame, self.looking_at_screen
        
        # No face detected
        cv2.putText(frame, "No face detected", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        return frame, False
    
    # For Jonathan use camera_index = 1
    # For Owen use camera_index = 0
    def run(self, camera_index=1):
        """Main loop to run the eye tracker"""
        # Try to open camera with different backends
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)  # DirectShow on Windows
        
        if not cap.isOpened():
            print(f"Trying camera index {camera_index} with default backend...")
            cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print(f"Error: Could not open camera at index {camera_index}")
            print("Trying to find available cameras...")
            for i in range(5):
                test_cap = cv2.VideoCapture(i)
                if test_cap.isOpened():
                    print(f"Found camera at index {i}, change the camera_index variable")
                    test_cap.release()
                else:
                    break
            return
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Give camera time to warm up
        import time
        time.sleep(1)
        
        print("Eye Tracker started. Press 'q' to quit.")
        print(f"Camera opened successfully at index {camera_index}")
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"Error: Could not read frame {frame_count}")
                print("This might mean:")
                print("1. Camera disconnected")
                print("2. Camera driver issue")
                print("3. Insufficient permissions")
                break
            
            frame_count += 1
            
            # Flip frame horizontally for mirror view
            frame = cv2.flip(frame, 1)
            
            # Process the frame
            processed_frame, looking = self.process_frame(frame)
            
            # Here you can add your signal/callback when user looks away
            if not looking:
                # Send signal or trigger action
                print("not looking")  # Add your custom action here
            else:
                print("looking")
                
            # Display the frame
            cv2.imshow('Eye Tracker', processed_frame)
            
            # Exit on 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # Create and run the eye tracker
    tracker = EyeTracker()
    tracker.run()