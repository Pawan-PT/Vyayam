"""
Trunk Rotation Stretch V2 - Spinal mobility and core flexibility

Reference Video: https://www.youtube.com/watch?v=xXxCwU8M5rE
(Seated Trunk Rotation Stretch - Proper Technique)
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


class TrunkRotationStretchV2:
    """
    Trunk Rotation Stretch - Spinal mobility
    
    Level: Foundation
    Category: Stretching
    Target: Obliques, spinal rotators, mid-back
    
    Reference Video: https://www.youtube.com/watch?v=xXxCwU8M5rE
    (Trunk Rotation Stretch Technique)
    
    Biomechanics:
    - Sit or stand upright
    - Rotate torso to one side
    - Look over shoulder
    - Target: Shoulder rotation angle >45° from center
    - Hold: 30 seconds per side
    - Keep hips facing forward (isolate upper body rotation)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=xXxCwU8M5rE"
    
    def __init__(self, target_holds=2):
        # Exercise parameters (1 hold per side)
        self.target_holds_per_side = target_holds
        self.hold_count = 0
        self.rejected_count = 0
        self.current_side = 'right'  # Rotating to right first
        
        # Hold tracking
        self.target_hold_duration = 30  # 30 seconds
        self.hold_start_time = None
        self.current_hold_duration = 0
        
        # Practice mode
        self.probation_mode = True
        self.practice_holds_needed = 1
        self.practice_holds_completed = 0
        
        # Form tracking
        self.form_scores = []
        self.stability_detector = StabilityDetector()
        self.critical_errors_this_hold = 0
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        self.frame_counter = 0
        self.phase = "holding"
    
    def calculate_angles(self, analyzer: PoseAnalyzer, results, frame_shape) -> Dict:
        """Calculate trunk rotation angles"""
        # Get joint coordinates
        ls = analyzer.get_coords(results, 11, frame_shape)  # left shoulder
        rs = analyzer.get_coords(results, 12, frame_shape)  # right shoulder
        lh = analyzer.get_coords(results, 23, frame_shape)  # left hip
        rh = analyzer.get_coords(results, 24, frame_shape)  # right hip
        nose = analyzer.get_coords(results, 0, frame_shape)  # nose (for head direction)
        
        # Calculate shoulder line angle (relative to horizontal)
        shoulder_line_vector = (rs[0] - ls[0], rs[1] - ls[1])
        shoulder_angle = np.degrees(np.arctan2(shoulder_line_vector[1], shoulder_line_vector[0]))
        
        # Calculate hip line angle (should stay relatively horizontal)
        hip_line_vector = (rh[0] - lh[0], rh[1] - lh[1])
        hip_angle = np.degrees(np.arctan2(hip_line_vector[1], hip_line_vector[0]))
        
        # Rotation amount (difference between shoulder and hip angles)
        rotation_angle = abs(shoulder_angle - hip_angle)
        
        # Determine rotation direction (which way they're rotating)
        shoulder_center_x = (ls[0] + rs[0]) / 2
        hip_center_x = (lh[0] + rh[0]) / 2
        
        if shoulder_center_x > hip_center_x:
            rotation_side = 'right'
        else:
            rotation_side = 'left'
        
        # Check if actually rotating (rotation > 15°)
        is_rotating = rotation_angle > 15
        
        # Good rotation depth (>45° rotation)
        deep_rotation = rotation_angle > 45
        
        # Back upright check
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        
        # Vertical alignment (should stay relatively upright)
        vertical_diff = abs(shoulder_mid[0] - hip_mid[0])
        upright = vertical_diff < 60
        
        # Stability tracking
        self.stability_detector.update(hip_mid[0], hip_mid[1])
        
        return {
            'shoulder_angle': shoulder_angle,
            'hip_angle': hip_angle,
            'rotation_angle': rotation_angle,
            'rotation_side': rotation_side,
            'is_rotating': is_rotating,
            'deep_rotation': deep_rotation,
            'upright': upright,
            'joints_coords': {
                'ls': ls, 'rs': rs, 'lh': lh, 'rh': rh, 'nose': nose
            }
        }
    
    def get_target_poses(self) -> Dict:
        """Target angles for AR overlay"""
        return {
            'holding': {
                'rotation_angle': 50,  # Good rotation depth
                'upright': True,
                'tolerance': 15
            }
        }
    
    def validate_form(self, angles: Dict) -> Dict:
        """Validate trunk rotation form"""
        feedback = {}
        
        # Check if rotating
        if not angles.get('is_rotating', False):
            feedback['rotation'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=0,
                message="Rotate torso"
            )
        else:
            # Check rotation depth
            rotation = angles.get('rotation_angle', 0)
            if rotation >= 45:
                feedback['rotation'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=rotation,
                    message="Good rotation depth"
                )
            elif rotation >= 30:
                feedback['rotation'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=rotation,
                    message="Rotate more"
                )
            else:
                feedback['rotation'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=rotation,
                    message="Deeper rotation"
                )
        
        # Upright posture
        if angles.get('upright', False):
            feedback['posture'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=0,
                message="Good posture"
            )
        else:
            feedback['posture'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=0,
                message="Stay upright"
            )
        
        return feedback
    
    def update_hold_counter(self, angles: Dict, feedback: Dict) -> Tuple[bool, List[str]]:
        """Update hold timer"""
        hold_complete = False
        warnings = []
        now = time.time()
        
        # Start hold when in position
        if self.hold_start_time is None:
            if angles.get('deep_rotation', False):
                self.hold_start_time = now
                side = angles.get('rotation_side', 'right').upper()
                self.voice.speak(f"Hold rotation to {side}", priority=True)
        
        if self.hold_start_time is not None:
            # Calculate hold duration
            self.current_hold_duration = now - self.hold_start_time
            seconds_held = int(self.current_hold_duration)
            
            warnings.append(f"Hold: {seconds_held}s / {self.target_hold_duration}s")
            warnings.append(f"Side: {angles.get('rotation_side', 'right').upper()}")
            
            # Count seconds aloud
            if seconds_held <= self.target_hold_duration:
                self.voice.count_hold_seconds(seconds_held, self.target_hold_duration)
            
            # Check for critical errors
            has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
            
            if has_critical:
                self.critical_errors_this_hold += 1
                for fb in feedback.values():
                    if fb.status == FormStatus.INCORRECT:
                        warnings.append(fb.message)
                        if self.frame_counter % 40 == 0:
                            self.voice.give_atomic_command('maintain_rotation', priority=True)
                
                # Reset if too many errors
                if self.critical_errors_this_hold >= 8:
                    self.rejected_count += 1
                    self.hold_start_time = None
                    self.current_hold_duration = 0
                    self.critical_errors_this_hold = 0
                    self.stability_detector = StabilityDetector()
                    self.voice.speak("Hold failed", priority=True)
                    return False, warnings
            
            # Check if hold complete
            if self.current_hold_duration >= self.target_hold_duration:
                # Calculate form score
                targets = self.get_target_poses()['holding']
                stability_data = self.stability_detector.get_stability_data()
                
                form_score = FormCalculator.calculate_form_score(
                    angles={'rotation_angle': angles.get('rotation_angle', 50)},
                    target_angles=targets,
                    stability=stability_data,
                    tempo=None
                )
                
                if self.probation_mode:
                    if form_score >= 85:
                        self.practice_holds_completed += 1
                        self.voice.speak("Good practice hold", priority=True)
                        
                        if self.practice_holds_completed >= self.practice_holds_needed:
                            self.probation_mode = False
                            warnings.append("✅ Practice complete")
                            self.voice.announce_phase_transition(True)
                    else:
                        self.voice.provide_ar_feedback(form_score)
                        self.rejected_count += 1
                else:
                    self.hold_count += 1
                    self.form_scores.append(form_score)
                    hold_complete = True
                    self.voice.announce_rep(self.hold_count, self.target_holds_per_side * 2, form_score)
                
                # Reset for next hold
                self.hold_start_time = None
                self.current_hold_duration = 0
                self.critical_errors_this_hold = 0
                self.stability_detector = StabilityDetector()
                
                # Switch sides
                if self.hold_count % 2 == 1:
                    self.current_side = 'left' if self.current_side == 'right' else 'right'
                    self.voice.speak(f"Rotate to {self.current_side}", priority=True)
        else:
            warnings.append("Rotate torso to side")
        
        self.frame_counter += 1
        return hold_complete, warnings
    
    def is_complete(self) -> bool:
        """Check if target holds reached"""
        return self.hold_count >= (self.target_holds_per_side * 2)
    
    def get_stats(self) -> Dict:
        """Get exercise statistics"""
        avg_form = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        return {
            'holds': self.hold_count,
            'target_holds': self.target_holds_per_side * 2,
            'rejected_holds': self.rejected_count,
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("Trunk Rotation Stretch V2 initialized")
    print("Hold: 30 seconds per side")
    print("Ready to run!")
