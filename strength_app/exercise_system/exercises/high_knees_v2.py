"""
High Knees V2 - Cardio exercise

NEW EXERCISE for cardiovascular endurance

Level: Foundation
Category: Cardio
Target: Hip flexors, cardiovascular endurance
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class HighKneesV2:
    """
    High Knees - Fast-paced cardio exercise
    
    Level: Foundation
    Category: Cardio
    Target: Hip flexors, quadriceps, cardiovascular endurance
    
    Reference Video: https://www.youtube.com/watch?v=lsK-vKhG-jE
    (High Knees Exercise - Proper Form)
    
    Biomechanics:
    - Primary: Hip flexion (alternating knees up)
    - Target: Knee reaches hip height or above
    - Hip angle: <90° when knee is raised
    - Tempo: Fast movement (60-80 raises per minute)
    - Count: Each knee raise = 1 rep
    
    Movement Pattern:
    - Alternate left and right knee raises
    - Knee should reach at least hip height
    - Fast, controlled movement
    - Stay on balls of feet
    
    Phases:
    - Down (knee lowered)
    - Raising (knee coming up)
    - Up (knee at hip height)
    - Lowering (knee going back down)
    
    SPECIAL: No practice mode for cardio (speed is priority)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=lsK-vKhG-jE"
    
    def __init__(self, target_raises=50):
        self.target_raises = target_raises  # Total knee raises
        self.raise_count = 0
        
        self.phase = "down"
        self.last_phase = "down"
        
        # NO PRACTICE MODE for cardio exercises
        self.probation_mode = False
        
        self.form_scores = []
        self.current_raise_form_scores = []
        
        self.stability_detector = StabilityDetector(history_size=5)  # Shorter for fast movement
        
        # Track which leg just raised
        self.last_raised_leg = None
        
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
        self.start_time = time.time()
    
    def calculate_angles(self, analyzer, results, shape):
        """Calculate hip flexion angles and knee heights"""
        # Get joints
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        # Hip angles (shoulder → hip → knee)
        left_hip = analyzer.calculate_angle(ls, lh, lk)
        right_hip = analyzer.calculate_angle(rs, rh, rk)
        
        # Knee heights (relative to hip)
        left_knee_height = lh[1] - lk[1]  # Positive = knee above hip
        right_knee_height = rh[1] - rk[1]
        
        # Determine which knee is raised
        left_knee_raised = left_knee_height > 50  # Threshold for "raised"
        right_knee_raised = right_knee_height > 50
        
        # Use the more raised knee
        if left_knee_raised and left_knee_height > right_knee_height:
            active_hip_angle = left_hip
            active_knee_height = left_knee_height
            raised_leg = "left"
        elif right_knee_raised:
            active_hip_angle = right_hip
            active_knee_height = right_knee_height
            raised_leg = "right"
        else:
            # Neither raised significantly
            active_hip_angle = max(left_hip, right_hip)
            active_knee_height = max(left_knee_height, right_knee_height)
            raised_leg = None
        
        return {
            'left_hip': left_hip,
            'right_hip': right_hip,
            'active_hip_angle': active_hip_angle,
            'left_knee_height': left_knee_height,
            'right_knee_height': right_knee_height,
            'active_knee_height': active_knee_height,
            'raised_leg': raised_leg,
            'joints_coords': {
                'ls': ls, 'rs': rs,
                'lh': lh, 'rh': rh,
                'lk': lk, 'rk': rk,
                'la': la, 'ra': ra
            }
        }
    
    def get_target_poses(self):
        """Target angles for each phase"""
        return {
            'down': {
                'active_hip_angle': 175,  # Leg straight down
                'active_knee_height': 0,
                'tolerance': 20
            },
            'raising': {
                'active_hip_angle': 120,  # Mid raise
                'active_knee_height': 30,
                'tolerance': 25
            },
            'up': {
                'active_hip_angle': 75,   # Knee high (hip flexed)
                'active_knee_height': 60,  # Above hip level
                'tolerance': 20
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate form - relaxed for cardio"""
        feedback = {}
        
        # Check knee height
        knee_height = angles.get('active_knee_height', 0)
        
        if knee_height >= 50:
            feedback['knee_height'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=knee_height,
                message="Good height"
            )
        elif knee_height >= 30:
            feedback['knee_height'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=knee_height,
                message="Higher"
            )
        else:
            feedback['knee_height'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=knee_height,
                message="Knees higher"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """Update raise counter"""
        raise_done = False
        warnings = []
        
        knee_height = angle  # Using knee height as primary metric
        raised_leg = feedback.get('raised_leg')
        
        # Fast cardio - simplified detection
        if self.phase == "down" and knee_height > 40:
            self.phase = "raising"
        
        elif self.phase == "raising" and knee_height > 55:
            self.phase = "up"
        
        elif self.phase == "up" and knee_height < 45:
            # Knee raise complete
            # Only count if alternating legs (prevent double-counting)
            if raised_leg and raised_leg != self.last_raised_leg:
                raise_done = True
                self.raise_count += 1
                self.last_raised_leg = raised_leg
                
                form_score = self._calculate_raise_form_score()
                
                # Voice feedback every 10 raises
                if self.raise_count % 10 == 0:
                    voice.announce_rep(self.raise_count, self.target_raises, form_score)
            
            self.phase = "down"
        
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return raise_done, self.phase, warnings
    
    def _calculate_raise_form_score(self):
        """Calculate form score - relaxed for cardio"""
        if self.current_raise_form_scores:
            avg = sum(self.current_raise_form_scores) / len(self.current_raise_form_scores)
            self.current_raise_form_scores = []
            return avg
        return 80.0  # Default good for cardio
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score - relaxed for cardio"""
        self.stability_detector.update(joints_coords)
        
        # Simplified scoring for fast cardio
        knee_height = angles.get('active_knee_height', 0)
        
        if knee_height >= 60:
            form_score = 90.0  # Excellent
        elif knee_height >= 50:
            form_score = 85.0  # Good
        elif knee_height >= 40:
            form_score = 75.0  # Acceptable
        else:
            form_score = 60.0  # Too low
        
        self.current_raise_form_scores.append(form_score)
        return form_score
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        """Draw AR overlay"""
        # Always counted mode for cardio
        frame = self.ar.draw_counted_mode(
            frame=frame,
            joints=joints_coords,
            form_score=form_score
        )
        
        # Draw raise counter and pace
        elapsed = time.time() - self.start_time
        pace = (self.raise_count / elapsed * 60) if elapsed > 0 else 0
        
        cv2.rectangle(frame, (10, 10), (250, 90), (50, 50, 50), -1)
        cv2.putText(frame, f"Raises: {self.raise_count}/{self.target_raises}",
                   (20, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Pace: {int(pace)}/min",
                   (20, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame
    
    def get_stats(self):
        """Get statistics"""
        elapsed = time.time() - self.start_time
        avg_pace = (self.raise_count / elapsed * 60) if elapsed > 0 else 0
        
        avg_form = (sum(self.form_scores) / len(self.form_scores) 
                   if self.form_scores else 0)
        
        return {
            'raises_completed': self.raise_count,
            'target_raises': self.target_raises,
            'duration_seconds': round(elapsed, 1),
            'avg_pace_per_minute': round(avg_pace, 1),
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores
        }


if __name__ == "__main__":
    print("HIGH KNEES V2 - Cardio exercise")
    print("Fast alternating knee raises")
    print("Target pace: 60-80 raises/minute")
    print("Ready to run!")