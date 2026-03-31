"""
Lateral Gait Training V2 - Side-to-side walking exercise

NEW EXERCISE for lateral movement and stability

Level: Foundation
Category: Gait, Balance
Target: Hip abductors, lateral stability
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class LateralGaitTrainingV2:
    """
    Lateral Gait Training - Side-to-side stepping pattern
    
    Level: Foundation
    Category: Gait, Balance
    Target: Hip abductors, glute medius, lateral stability
    
    Reference Video: https://www.youtube.com/watch?v=8c_JKxm8SfI
    (Lateral Gait Training - Physical Therapy)
    
    Biomechanics:
    - Primary: Lateral weight shift and stepping
    - Detect: Which foot is on ground (weight bearing)
    - Knee angle: Should stay relatively straight (165-175°)
    - Hip abduction: Stepping leg moves sideways
    - Count: Each complete step cycle = 1 "rep"
    
    Movement Pattern:
    1. Start center, feet together
    2. Step left (left foot moves, weight shifts left)
    3. Bring right foot to left (back to center)
    4. Step right (right foot moves, weight shifts right)
    5. Bring left foot to right (back to center)
    6. = 1 complete cycle (2 steps)
    
    Phases:
    - Center (feet together)
    - Stepping Left
    - Stepping Right
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=8c_JKxm8SfI"
    
    def __init__(self, target_steps=20):
        self.target_steps = target_steps  # Total steps (not cycles)
        self.step_count = 0
        
        self.phase = "center"
        self.last_phase = "center"
        
        # No practice mode for gait training (too dynamic)
        self.probation_mode = False
        
        self.form_scores = []
        self.current_step_form_scores = []
        
        self.stability_detector = StabilityDetector(history_size=10)
        
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """Calculate angles and positions"""
        # Get ankles (for weight detection)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        # Get knees and hips
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        
        # Knee angles
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        # Smooth
        left_knee = analyzer.smooth_angle(left_knee, 'left')
        right_knee = analyzer.smooth_angle(right_knee, 'right')
        
        # Lateral separation (distance between feet)
        feet_distance = abs(la[0] - ra[0])
        
        # Weight detection (lower ankle = on ground)
        weight_on_left = la[1] > ra[1]
        weight_on_right = ra[1] > la[1]
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': (left_knee + right_knee) / 2,
            'feet_distance': feet_distance,
            'weight_on_left': weight_on_left,
            'weight_on_right': weight_on_right,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra
            }
        }
    
    def get_target_poses(self):
        """Target angles for each phase"""
        return {
            'center': {
                'avg_knee': 175,  # Standing straight
                'feet_distance': 50,  # Feet close together
                'tolerance': 15
            },
            'stepping': {
                'avg_knee': 170,  # Slight bend OK
                'feet_distance': 150,  # Feet apart during step
                'tolerance': 20
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate form"""
        feedback = {}
        targets = self.get_target_poses()[phase]
        
        # Knee angle (should stay mostly straight)
        knee_angle = angles.get('avg_knee', 0)
        
        if knee_angle >= 165:
            feedback['knee'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=knee_angle,
                message="Good posture"
            )
        else:
            feedback['knee'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=knee_angle,
                message="Stand straighter"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """Update step counter"""
        step_done = False
        warnings = []
        
        feet_distance = angle  # Using feet_distance as primary metric
        
        # Simple step detection based on feet separation
        if self.phase == "center" and feet_distance > 100:
            self.phase = "stepping"
        
        elif self.phase == "stepping" and feet_distance < 80:
            # Step complete (feet back together)
            step_done = True
            self.step_count += 1
            self.phase = "center"
            
            form_score = self._calculate_step_form_score()
            
            # Announce every 5 steps
            if self.step_count % 5 == 0:
                voice.announce_rep(self.step_count, self.target_steps, form_score)
        
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return step_done, self.phase, warnings
    
    def _calculate_step_form_score(self):
        """Calculate form score"""
        if self.current_step_form_scores:
            avg = sum(self.current_step_form_scores) / len(self.current_step_form_scores)
            self.current_step_form_scores = []
            return avg
        return 85.0
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score"""
        self.stability_detector.update(joints_coords)
        
        target_angles = self.get_target_poses()[self.phase]
        stability_data = self.stability_detector.get_stability_data()
        tempo_data = {'too_fast': False, 'too_slow': False}
        
        form_score = FormCalculator.calculate_form_score(
            angles={'avg_knee': angles.get('avg_knee', 175)},
            target_angles={'avg_knee': 175, 'tolerance': 15},
            stability=stability_data,
            tempo=tempo_data
        )
        
        self.current_step_form_scores.append(form_score)
        return form_score
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        """Draw AR overlay"""
        frame = self.ar.draw_counted_mode(
            frame=frame,
            joints=joints_coords,
            form_score=form_score
        )
        
        # Draw step counter
        cv2.rectangle(frame, (10, 10), (200, 60), (50, 50, 50), -1)
        cv2.putText(frame, f"Steps: {self.step_count}/{self.target_steps}",
                   (20, 45),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return frame
    
    def get_stats(self):
        """Get statistics"""
        avg_form = (sum(self.form_scores) / len(self.form_scores) 
                   if self.form_scores else 0)
        
        return {
            'steps_completed': self.step_count,
            'target_steps': self.target_steps,
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores
        }


if __name__ == "__main__":
    print("LATERAL GAIT TRAINING V2 - Side-to-side stepping")
    print("Lateral stability and hip abductor training")
    print("Ready to run!")