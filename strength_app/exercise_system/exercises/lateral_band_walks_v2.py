"""
Lateral Band Walks V2 - Hip abduction strength training

Reference Video: https://www.youtube.com/watch?v=B3nZPwcTnDs
(Lateral Band Walks - Gluteus Medius Activation)
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


class LateralBandWalksV2:
    """
    Lateral Band Walks - Hip abduction training
    
    Level: Intermediate
    Category: Strength
    Target: Gluteus medius, hip abductors, TFL
    
    Reference Video: https://www.youtube.com/watch?v=B3nZPwcTnDs
    (Lateral Band Walk Technique)
    
    Biomechanics:
    - Maintain quarter-squat position (145° knee angle)
    - Band around knees or ankles provides resistance
    - Step sideways - maintain tension throughout
    - CRITICAL: No knee valgus (collapse inward)
    - 10 steps per direction = 1 set
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=B3nZPwcTnDs"
    
    def __init__(self, target_sets=3):
        # Exercise parameters
        self.target_steps = 10  # 10 steps per set
        self.target_sets = target_sets
        self.set_count = 0
        self.steps_taken = 0
        self.rejected_count = 0
        
        # Lateral movement tracking
        self.last_hip_center_x = None
        
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
        self.phase = "squat_position"
    
    def calculate_angles(self, analyzer: PoseAnalyzer, results, frame_shape) -> Dict:
        """Calculate angles with lateral movement detection"""
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
        
        # Detect lateral movement (stepping)
        hip_center_x = (lh[0] + rh[0]) / 2
        hip_center_y = (lh[1] + rh[1]) / 2
        
        lateral_step_detected = False
        if self.last_hip_center_x is not None:
            lateral_movement = abs(hip_center_x - self.last_hip_center_x)
            if lateral_movement > 30:  # Significant lateral shift = step
                lateral_step_detected = True
                self.steps_taken += 1
        
        self.last_hip_center_x = hip_center_x
        
        # Knee width (band tension check)
        knee_width = abs(lk[0] - rk[0])
        ankle_width = abs(la[0] - ra[0])
        knee_collapsed = knee_width < (ankle_width * 0.9)
        
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
            'knee_width': knee_width,
            'ankle_width': ankle_width,
            'knee_collapsed': knee_collapsed,
            'lateral_step_detected': lateral_step_detected,
            'steps_taken': self.steps_taken,
            'joints_coords': {
                'lh': lh, 'rh': rh, 'lk': lk, 'rk': rk,
                'la': la, 'ra': ra, 'ls': ls, 'rs': rs
            }
        }
    
    def get_target_poses(self) -> Dict:
        """Target angles for AR overlay"""
        return {
            'squat_position': {
                'avg_knee': 145,
                'left_knee': 145,
                'right_knee': 145,
                'back': 165,
                'knee_separation': 'wide',
                'tolerance': 12
            },
            'stepping': {
                'avg_knee': 145,
                'left_knee': 145,
                'right_knee': 145,
                'back': 165,
                'knee_separation': 'wide',
                'tolerance': 15
            }
        }
    
    def validate_form(self, angles: Dict) -> Dict:
        """Validate lateral band walk form"""
        feedback = {}
        avg_knee = angles.get('avg_knee', 0)
        
        # Must maintain squat position
        if 135 <= avg_knee <= 160:
            feedback['squat'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=avg_knee,
                message="Good quarter squat"
            )
        elif avg_knee > 165:
            feedback['squat'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=avg_knee,
                message="Stay in squat"
            )
        elif avg_knee < 120:
            feedback['squat'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=avg_knee,
                message="Not too deep"
            )
        
        # CRITICAL: No knee collapse
        if angles.get('knee_collapsed', False):
            feedback['valgus'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=0,
                message="Knees collapsing"
            )
        else:
            feedback['valgus'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles.get('knee_width', 0),
                message="Good band tension"
            )
        
        # Back posture
        back = angles.get('back', 0)
        if back >= 155:
            feedback['posture'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=back,
                message="Good posture"
            )
        elif back >= 145:
            feedback['posture'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=back,
                message="Chest up"
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
        
        if has_critical:
            self.critical_errors_this_set += 1
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if self.frame_counter % 40 == 0:
                        self.voice.give_atomic_command('knees_out', priority=True)
            
            # More lenient - allow some errors during movement
            if self.critical_errors_this_set >= 10:
                self.rejected_count += 1
                self.steps_taken = 0
                self.critical_errors_this_set = 0
                self.last_hip_center_x = None
                self.voice.speak("Set rejected", priority=True)
                return False, warnings
        
        # Voice coaching at milestones
        if self.steps_taken == 0 and self.frame_counter == 30:
            self.voice.speak("Step sideways", priority=True)
        elif self.steps_taken == 5 and not self.probation_mode:
            self.voice.speak("Halfway", priority=False)
        
        # Check if set complete
        if self.steps_taken >= self.target_steps:
            # Calculate form score
            targets = self.get_target_poses()['squat_position']
            stability_data = self.stability_detector.get_stability_data()
            
            form_score = FormCalculator.calculate_form_score(
                angles={'avg_knee': angles.get('avg_knee', 145), 'back': angles.get('back', 165)},
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
            self.critical_errors_this_set = 0
            self.last_hip_center_x = None
            self.stability_detector = StabilityDetector()
            
            if self.set_count < self.target_sets:
                self.voice.speak("Rest briefly", priority=True)
        
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
    print("Lateral Band Walks V2 initialized")
    print("10 steps per set - maintain tension")
    print("Ready to run!")