"""
IT Band Stretch Standing V2 - IT band and hip flexibility

Reference Video: https://www.youtube.com/watch?v=5YYb9dvuQ3A
(Standing IT Band Stretch - Proper Technique)
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


class ITBandStretchStandingV2:
    """
    Standing IT Band Stretch - IT band flexibility
    
    Level: Foundation
    Category: Stretching
    Target: IT band, hip abductors, tensor fasciae latae
    
    Reference Video: https://www.youtube.com/watch?v=5YYb9dvuQ3A
    (Standing IT Band Stretch Technique)
    
    Biomechanics:
    - Stand with feet crossed (stretch leg behind)
    - Lean away from stretch side (create lateral bend)
    - Raise arm overhead on stretch side
    - Target: Lateral trunk lean >20° from vertical
    - Hold: 30 seconds per side
    - Feel stretch along outer hip/thigh
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=5YYb9dvuQ3A"
    
    def __init__(self, target_holds=2):
        # Exercise parameters (1 hold per side)
        self.target_holds_per_side = target_holds
        self.hold_count = 0
        self.rejected_count = 0
        self.current_side = 'right'  # Stretching right IT band first
        
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
        """Calculate IT band stretch angles"""
        # Get joint coordinates
        ls = analyzer.get_coords(results, 11, frame_shape)  # left shoulder
        rs = analyzer.get_coords(results, 12, frame_shape)  # right shoulder
        lh = analyzer.get_coords(results, 23, frame_shape)  # left hip
        rh = analyzer.get_coords(results, 24, frame_shape)  # right hip
        lk = analyzer.get_coords(results, 25, frame_shape)  # left knee
        rk = analyzer.get_coords(results, 26, frame_shape)  # right knee
        la = analyzer.get_coords(results, 27, frame_shape)  # left ankle
        ra = analyzer.get_coords(results, 28, frame_shape)  # right ankle
        
        # Calculate lateral lean (trunk bending to side)
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        
        # Lateral offset (horizontal distance between shoulder and hip centers)
        lateral_offset = abs(shoulder_mid[0] - hip_mid[0])
        
        # Vertical height (for calculating lean angle)
        vertical_height = abs(shoulder_mid[1] - hip_mid[1])
        if vertical_height < 1:
            vertical_height = 1
        
        # Lean angle (degrees from vertical)
        lean_ratio = lateral_offset / vertical_height
        lean_angle = np.degrees(np.arctan(lean_ratio))
        
        # Determine lean direction (which side they're leaning to)
        if shoulder_mid[0] > hip_mid[0]:
            lean_side = 'right'
        else:
            lean_side = 'left'
        
        # Good lean = >20° from vertical
        good_lean = lean_angle > 20
        
        # Feet position (check if crossed or close together)
        feet_horizontal_distance = abs(la[0] - ra[0])
        feet_close = feet_horizontal_distance < 30  # Feet close together or crossed
        
        # Standing check (both ankles on similar Y coordinate = standing)
        both_feet_down = abs(la[1] - ra[1]) < 30
        
        # Stability tracking
        self.stability_detector.update(hip_mid[0], hip_mid[1])
        
        return {
            'lateral_offset': lateral_offset,
            'lean_angle': lean_angle,
            'lean_side': lean_side,
            'good_lean': good_lean,
            'feet_close': feet_close,
            'both_feet_down': both_feet_down,
            'joints_coords': {
                'ls': ls, 'rs': rs, 'lh': lh, 'rh': rh,
                'lk': lk, 'rk': rk, 'la': la, 'ra': ra
            }
        }
    
    def get_target_poses(self) -> Dict:
        """Target angles for AR overlay"""
        return {
            'holding': {
                'lean_angle': 25,  # Good lateral lean
                'feet_close': True,
                'both_feet_down': True,
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles: Dict) -> Dict:
        """Validate IT band stretch form"""
        feedback = {}
        
        # Check if standing
        if not angles.get('both_feet_down', False):
            feedback['standing'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=0,
                message="Stand on both feet"
            )
        else:
            feedback['standing'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=0,
                message="Good standing position"
            )
        
        # Feet position
        if not angles.get('feet_close', False):
            feedback['feet'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=0,
                message="Cross or close feet"
            )
        
        # Lateral lean (stretch depth)
        lean = angles.get('lean_angle', 0)
        if lean >= 25:
            feedback['lean'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=lean,
                message="Good stretch depth"
            )
        elif lean >= 15:
            feedback['lean'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=lean,
                message="Lean more to side"
            )
        else:
            feedback['lean'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=lean,
                message="Lean sideways"
            )
        
        return feedback
    
    def update_hold_counter(self, angles: Dict, feedback: Dict) -> Tuple[bool, List[str]]:
        """Update hold timer"""
        hold_complete = False
        warnings = []
        now = time.time()
        
        # Start hold when in position
        if self.hold_start_time is None:
            if angles.get('good_lean', False) and angles.get('both_feet_down', False):
                self.hold_start_time = now
                lean_side = angles.get('lean_side', 'left')
                # Stretching opposite side IT band (lean left = stretch right IT band)
                stretch_side = 'right' if lean_side == 'left' else 'left'
                self.voice.speak(f"Hold {stretch_side.upper()} IT band stretch", priority=True)
        
        if self.hold_start_time is not None:
            # Calculate hold duration
            self.current_hold_duration = now - self.hold_start_time
            seconds_held = int(self.current_hold_duration)
            
            lean_side = angles.get('lean_side', 'left')
            stretch_side = 'RIGHT' if lean_side == 'left' else 'LEFT'
            
            warnings.append(f"Hold: {seconds_held}s / {self.target_hold_duration}s")
            warnings.append(f"Stretching: {stretch_side} IT band")
            
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
                            self.voice.give_atomic_command('maintain_position', priority=True)
                
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
                    angles={'lean_angle': angles.get('lean_angle', 25)},
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
                    self.voice.speak(f"Switch to other side", priority=True)
        else:
            warnings.append("Lean to the side")
        
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
    print("IT Band Stretch Standing V2 initialized")
    print("Hold: 30 seconds per side")
    print("Ready to run!")
