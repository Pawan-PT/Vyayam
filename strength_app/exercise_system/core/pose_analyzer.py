"""
Pose detection and analysis - EXACT COPY from working code
"""

import cv2
import mediapipe as mp
import numpy as np


class PoseAnalyzer:
    """EXACT COPY from your working code"""
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )
        self.angle_history = {'left': [], 'right': []}
        self.last_angles = {'left': None, 'right': None}
        self.movement_history = []
        
    def detect_pose(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return self.pose.process(rgb)
    
    def calculate_angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        return 360 - angle if angle > 180 else angle
    
    def smooth_angle(self, angle, leg='left'):
        self.angle_history[leg].append(angle)
        if len(self.angle_history[leg]) > 5:
            self.angle_history[leg].pop(0)
        return float(np.median(self.angle_history[leg]))
    
    def check_wild_movement(self, left, right):
        if self.last_angles['left'] is None:
            self.last_angles['left'], self.last_angles['right'] = left, right
            return False, ""
        
        left_change = abs(left - self.last_angles['left'])
        right_change = abs(right - self.last_angles['right'])
        max_change = max(left_change, right_change)
        
        self.movement_history.append(max_change)
        if len(self.movement_history) > 8:
            self.movement_history.pop(0)
        
        avg_speed = np.mean(self.movement_history) if self.movement_history else 0
        self.last_angles['left'], self.last_angles['right'] = left, right
        
        if max_change > 18:
            return True, "Too fast - slow down now"
        if avg_speed > 10:
            return True, "Control your speed"
        
        return False, ""
    
    def get_coords(self, results, idx, shape):
        if not results.pose_landmarks:
            return (0, 0)
        lm = results.pose_landmarks.landmark[idx]
        h, w = shape[:2]
        return (int(lm.x * w), int(lm.y * h))