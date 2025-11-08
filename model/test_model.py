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
        
        # Eye landmark indices for MediaPipe Face Mesh
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        
        # Define screen attention zone (center box)
        self.attention_zone = None
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
    
    def is_looking_at_screen(self, left_iris, right_iris, frame_shape):
        """Check if both irises are within the attention zone"""
        h, w = frame_shape[:2]
        
        # Define attention zone (center 60% of screen)
        if self.attention_zone is None:
            margin_w = int(w * 0.3)
            margin_h = int(h * 0.3)
            self.attention_zone = {
                'x1': margin_w,
                'y1': margin_h,
                'x2': w - margin_w,
                'y2': h - margin_h
            }
        
        zone = self.attention_zone
        
        # Check if both irises are in the zone
        left_in = (zone['x1'] <= left_iris[0] <= zone['x2'] and 
                   zone['y1'] <= left_iris[1] <= zone['y2'])
        right_in = (zone['x1'] <= right_iris[0] <= zone['x2'] and 
                    zone['y1'] <= right_iris[1] <= zone['y2'])
        
        return left_in and right_in
    
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
            
            # Draw eye regions
            cv2.circle(frame, left_eye_center, 5, (0, 255, 0), -1)
            cv2.circle(frame, right_eye_center, 5, (0, 255, 0), -1)
            
            # Draw iris positions
            cv2.circle(frame, left_iris, 3, (255, 0, 0), -1)
            cv2.circle(frame, right_iris, 3, (255, 0, 0), -1)
            
            # Check if looking at screen
            self.looking_at_screen = self.is_looking_at_screen(left_iris, right_iris, frame.shape)
            
            # Draw attention zone (bounding box)
            if self.attention_zone:
                zone = self.attention_zone
                color = (0, 255, 0) if self.looking_at_screen else (0, 0, 255)
                cv2.rectangle(frame, 
                            (zone['x1'], zone['y1']), 
                            (zone['x2'], zone['y2']), 
                            color, 2)
            
            # Display status
            status = "Looking at screen" if self.looking_at_screen else "Not looking at screen"
            color = (0, 255, 0) if self.looking_at_screen else (0, 0, 255)
            cv2.putText(frame, status, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            return frame, self.looking_at_screen
        
        # No face detected
        cv2.putText(frame, "NO FACE DETECTED", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        return frame, False
    
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
                    print(f"Found camera at index {i}")
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
                pass  # Add your custom action here
            
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