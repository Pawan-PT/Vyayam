"""
Backward Walking V2 - Proprioception and balance training

Reference Video: https://www.youtube.com/watch?v=wCRzwBzEXX8
(Backward Walking Exercise - Benefits and Technique)
"""

import cv2
import time
import numpy as np
from typing import Dict, Tuple, List
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class BackwardWalkingV2:
    """
    Backward Walking - Proprioception training
    
    Level: Advanced
    Category: Balance
    Target: Quadriceps, balance, proprioception
    
    Reference Video: https://www.youtube.com/watch?v=wCRzwBzEXX8
    (Backward Walking Technique)
    
    Biomechanics:
    - Walk backward with controlled steps
    - Land on ball of foot first, then heel
    - Keep knees slightly bent (170-180°)
    - Maintain upright posture
    - Low patellofemoral stress (good for PFPS)
    - 20 backward steps = 1 set
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=wCRzwBzEXX8"
    
    def __init__(self, target_sets=3):
        # Exercise parameters
        self.target_steps = 20  # 20 backward steps per set
        self.target_sets = target_sets
        self.set_count = 0
        self.steps_taken = 0
        self.rejected_count = 0
        
        # Backward movement tracking
        self.last_hip_center_y = None
        
        # Practice mode
        self.probation_mode = True
        self.practice_sets_needed = 1
        self.practice_sets_completed = 0
        
        # Form tracking
        self.form_scores = []
        self.stability_detector = StabilityDetector()
        self.critical_errors_this_set = 0
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        self.frame_counter = 0
        self.phase = "walking"
    
    def calculate_angles(self, analyzer: PoseAnalyzer, results, frame_shape) -> Dict:
        """Calculate angles with backward movement detection"""
        # Get joint coordinates
        lh = analyzer.get_coords(results, 23, frame_shape)
        rh = analyzer.get_coords(results, 24, frame_shape)
        lk = analyzer.get_coords(results, 25, frame_shape)
        rk = analyzer.get_coords(results, 26, frame_shape)
        la = analyzer.get_coords(results, 27, frame_shape)
        ra = analyzer.get_coords(results, 28, frame_shape)
        ls = analyzer.get_coords(results, 11, frame_shape)
        rs = analyzer.get_coords(results, 12, frame_shape)
        
        # Calculate knee angles
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right')
        avg_knee = (left_knee + right_knee) / 2
        
        # Detect backward movement (hip center moves backward = y increases in frame)
        hip_center_y = (lh[1] + rh[1]) / 2
        hip_center_x = (lh[0] + rh[0]) / 2
        
        backward_step_detected = False
        if self.last_hip_center_y is not None:
            movement = hip_center_y - self.last_hip_center_y
            if movement > 15:  # Moving backward (down in frame)
                backward_step_detected = True
                self.steps_taken += 1
        
        self.last_hip_center_y = hip_center_y
        
        # Back posture
        shoulder_mid_y = (ls[1] + rs[1]) / 2
        hip_mid_y = (lh[1] + rh[1]) / 2
        shoulder_mid_x = (ls[0] + rs[0]) / 2
        hip_mid_x = (lh[0] + rh[0]) / 2
        
        vertical_offset = abs(shoulder_mid_x - hip_mid_x)
        vertical_height = abs(hip_mid_y - shoulder_mid_y) if hip_mid_y > shoulder_mid_y else 1
        lean_ratio = vertical_offset / max(vertical_height, 1)
        back_angle = 180 - (lean_ratio * 60)
        back_angle = max(120, min(180, back_angle))
        
        # Update stability
        self.stability_detector.update(hip_center_x, hip_center_y)
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'back': back_angle,
            'backward_step_detected': backward_step_detected,
            'steps_taken': self.steps_taken,
            'joints_coords': {
                'lh': lh, 'rh': rh, 'lk': lk, 'rk': rk,
                'la': la, 'ra': ra, 'ls': ls, 'rs': rs
            }
        }
    
    def get_target_poses(self) -> Dict:
        """Target angles for AR overlay"""
        return {
            'walking': {
                'avg_knee': 175,
                'left_knee': 175,
                'right_knee': 175,
                'back': 165,
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles: Dict) -> Dict:
        """Validate backward walking form"""
        feedback = {}
        avg_knee = angles.get('avg_knee', 0)
        back = angles.get('back', 0)
        
        # Knees should stay slightly bent (not locked)
        if 165 <= avg_knee <= 180:
            feedback['knees'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=avg_knee,
                message="Good knee position"
            )
        elif avg_knee < 155:
            feedback['knees'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=avg_knee,
                message="Don't squat"
            )
        
        # Posture - stay upright
        if back >= 160:
            feedback['posture'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=back,
                message="Good posture"
            )
        elif back >= 150:
            feedback['posture'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=back,
                message="Stand upright"
            )
        else:
            feedback['posture'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=back,
                message="Too much lean"
            )
        
        return feedback
    
    def update_step_counter(self, angles: Dict, feedback: Dict) -> Tuple[bool, List[str]]:
        """Update step counter"""
        set_complete = False
        warnings = []
        self.frame_counter += 1
        
        steps_remaining = self.target_steps - self.steps_taken
        warnings.append(f"Steps: {self.steps_taken}/{self.target_steps}")
        
        # Error tracking
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        has_warning = any(f.status == FormStatus.NEEDS_ADJUSTMENT for f in feedback.values())
        
        if has_critical:
            self.critical_errors_this_set += 1
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if self.frame_counter % 40 == 0:
                        self.voice.give_atomic_command('maintain_posture', priority=True)
        
        if has_warning and self.frame_counter % 40 == 0:
            for fb in feedback.values():
                if fb.status == FormStatus.NEEDS_ADJUSTMENT:
                    warnings.append(fb.message)
        
        # Voice coaching at milestones
        if self.steps_taken == 0 and self.frame_counter == 30:
            self.voice.speak("Walk backward slowly", priority=True)
        elif self.steps_taken == 10:
            self.voice.speak("Halfway", priority=False)
        elif self.steps_taken == 15:
            self.voice.speak("Five more steps", priority=False)
        
        # Check if set complete
        if self.steps_taken >= self.target_steps:
            # Calculate form score
            targets = self.get_target_poses()['walking']
            stability_data = self.stability_detector.get_stability_data()
            
            form_score = FormCalculator.calculate_form_score(
                angles={'avg_knee': angles.get('avg_knee', 175), 'back': angles.get('back', 165)},
                target_angles=targets,
                stability=stability_data,
                tempo=None
            )
            
            if self.probation_mode:
                if form_score >= 85:
                    self.practice_sets_completed += 1
                    self.voice.speak("Good practice set", priority=True)
                    
                    if self.practice_sets_completed >= self.practice_sets_needed:
                        self.probation_mode = False
                        warnings.append("✅ Practice complete")
                        self.voice.announce_phase_transition(True)
                else:
                    self.voice.provide_ar_feedback(form_score)
                    self.rejected_count += 1
            else:
                self.set_count += 1
                self.form_scores.append(form_score)
                set_complete = True
                self.voice.announce_rep(self.set_count, self.target_sets, form_score)
            
            # Reset for next set
            self.steps_taken = 0
            self.last_hip_center_y = None
            self.critical_errors_this_set = 0
            self.stability_detector = StabilityDetector()
            
            if self.set_count < self.target_sets:
                self.voice.speak("Turn around and rest", priority=True)
        
        return set_complete, warnings
    
    def is_complete(self) -> bool:
        """Check if target sets reached"""
        return self.set_count >= self.target_sets
    
    def get_stats(self) -> Dict:
        """Get exercise statistics"""
        avg_form = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        return {
            'sets': self.set_count,
            'target_sets': self.target_sets,
            'rejected_sets': self.rejected_count,
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("Backward Walking V2 initialized")
    print("20 backward steps per set - good for PFPS")
    print("Ready to run!")