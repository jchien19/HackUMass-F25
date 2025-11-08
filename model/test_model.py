import cv2
import mediapipe as mp
import numpy as np
import serial
import time

class EyeTracker:
    def __init__(self, arduino_port='COM3', use_arduino=True):
        # Initialize MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.4,
            min_tracking_confidence=0.4
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Eye landmark indices for MediaPipe Face Mesh
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        
        # Define screen attention zone
        self.looking_at_screen = False
        
        # Arduino integration
        self.use_arduino = use_arduino
        self.arduino = None
        if self.use_arduino:
            try:
                self.arduino = serial.Serial(arduino_port, 9600)
                time.sleep(2)  # Wait for Arduino to reset
                print(f"Connected to Arduino on {arduino_port}")
            except Exception as e:
                print(f"Warning: Could not connect to Arduino: {e}")
                print("Continuing without Arduino...")
                self.use_arduino = False
        
        # Timer for looking away detection
        self.look_away_start_time = None
        self.look_away_threshold = 0.5  # 0.5 seconds
        self.signal_sent = False
        
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
        return dx, dy
    
    def is_looking_at_screen(self, left_eye_center, right_eye_center, 
                            left_iris, right_iris, frame_shape):
        """Check if user is looking at screen based on iris-to-eye-center distance"""
        left_dx, left_dy = self.calculate_gaze_ratio(left_eye_center, left_iris)
        right_dx, right_dy = self.calculate_gaze_ratio(right_eye_center, right_iris)
        
        # Thresholds for "looking at screen"
        horizontal_threshold = 4  # pixels
        vertical_threshold = 2    # pixels
        
        # Check if iris is relatively centered in both eyes
        left_centered = (abs(left_dx) < horizontal_threshold and 
                        abs(left_dy) < vertical_threshold)   
        right_centered = (abs(right_dx) < horizontal_threshold and 
                         abs(right_dy) < vertical_threshold)
        
        return left_centered and right_centered
    
    def send_arduino_signal(self):
        """Send trigger signal to Arduino"""
        if self.use_arduino and self.arduino:
            try:
                self.arduino.write(b'1')
                print("Signal sent to Arduino!")
                
                # Read Arduino response
                time.sleep(0.1)
                while self.arduino.in_waiting > 0:
                    response = self.arduino.readline().decode('utf-8').strip()
                    print(f"Arduino: {response}")
                    
            except Exception as e:
                print(f"Error sending signal to Arduino: {e}")
    
    def process_frame(self, frame):
        """Process a single frame and detect eye position"""
        img_h, img_w = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        current_time = time.time()
        
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
            cv2.circle(frame, left_eye_center, 8, (0, 255, 255), 2)
            cv2.circle(frame, right_eye_center, 8, (0, 255, 255), 2)
            
            # Draw iris positions
            cv2.circle(frame, left_iris, 5, (255, 0, 0), -1)
            cv2.circle(frame, right_iris, 5, (255, 0, 0), -1)
            
            # Draw lines from eye center to iris
            cv2.line(frame, left_eye_center, left_iris, (0, 255, 0), 2)
            cv2.line(frame, right_eye_center, right_iris, (0, 255, 0), 2)
            
            # Check if looking at screen
            self.looking_at_screen = self.is_looking_at_screen(
                left_eye_center, right_eye_center, 
                left_iris, right_iris, 
                frame.shape
            )
            
            # Handle looking away timer
            if not self.looking_at_screen:
                # Start timer if just looked away
                if self.look_away_start_time is None:
                    self.look_away_start_time = current_time
                    self.signal_sent = False
                    print("Started looking away...")
                
                # Check if looked away for 2 seconds
                elapsed_time = current_time - self.look_away_start_time
                
                if elapsed_time >= self.look_away_threshold and not self.signal_sent:
                    print(f"Looked away for {self.look_away_threshold} seconds!")
                    self.send_arduino_signal()
                    self.signal_sent = True
                
                # Display timer
                status = f"Not looking: {elapsed_time:.1f}s"
                color = (0, 0, 255)
                
            else:
                # Reset timer when looking at screen
                self.look_away_start_time = None
                self.signal_sent = False
                status = "Looking at screen"
                color = (0, 255, 0)
            
            cv2.putText(frame, status, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            return frame, self.looking_at_screen
        
        # No face detected - treat as looking away
        if self.look_away_start_time is None:
            self.look_away_start_time = current_time
            self.signal_sent = False
        
        elapsed_time = current_time - self.look_away_start_time
        if elapsed_time >= self.look_away_threshold and not self.signal_sent:
            print(f"No face detected for {self.look_away_threshold} seconds!")
            self.send_arduino_signal()
            self.signal_sent = True
        
        cv2.putText(frame, f"No face: {elapsed_time:.1f}s", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        return frame, False
    
    def run(self, camera_index=1):
        """Main loop to run the eye tracker"""
        # Try to open camera with different backends
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        
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
        time.sleep(1)
        
        print("Eye Tracker started. Press 'q' to quit.")
        print(f"Camera opened successfully at index {camera_index}")
        if self.use_arduino:
            print("Arduino signal will be sent after 2 seconds of looking away")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame")
                break
            
            # Flip frame horizontally for mirror view
            frame = cv2.flip(frame, 1)
            
            # Process the frame
            processed_frame, looking = self.process_frame(frame)
            
            # Display the frame
            cv2.imshow('Eye Tracker', processed_frame)
            
            # Exit on 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        # Close Arduino connection
        if self.arduino:
            self.arduino.close()
            print("Arduino connection closed")

if __name__ == "__main__":
    # Create and run the eye tracker
    # Set use_arduino=False to run without Arduino
    # Change 'COM3' to your actual Arduino port
    tracker = EyeTracker(arduino_port='COM3', use_arduino=True)
    tracker.run(camera_index=0)  # Change camera_index as needed