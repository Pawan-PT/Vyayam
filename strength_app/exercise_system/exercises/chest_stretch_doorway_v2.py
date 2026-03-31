"""
Chest Stretch Doorway V2 - Pectoral flexibility

Reference Video: https://www.youtube.com/watch?v=3L_qVQrx7r0
(Doorway Chest Stretch - Proper Technique)
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


class ChestStretchDoorwayV2:
    """
    Doorway Chest Stretch - Pectoral flexibility
    
    Level: Foundation
    Category: Stretching
    Target: Pectorals, anterior deltoids, biceps
    
    Reference Video: https://www.youtube.com/watch?v=3L_qVQrx7r0
    (Doorway Chest Stretch Technique)
    
    Biomechanics:
    - Stand in doorway, arms raised to sides at shoulder height
    - Elbows bent 90°, forearms against door frame
    - Step forward through doorway to stretch
    - Target: Arms spread wide (>160° shoulder angle)
    - Hold: 30 seconds
    - Keep chest up, shoulders back
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=3L_qVQrx7r0"
    
    def __init__(self, target_holds=3):
        # Exercise parameters
        self.target_holds = target_holds
        self.hold_count = 0
        self.rejected_count = 0
        
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
        """Calculate chest stretch angles"""
        # Get joint coordinates
        ls = analyzer.get_coords(results, 11, frame_shape)  # left shoulder
        rs = analyzer.get_coords(results, 12, frame_shape)  # right shoulder
        le = analyzer.get_coords(results, 13, frame_shape)  # left elbow
        re = analyzer.get_coords(results, 14, frame_shape)  # right elbow
        lw = analyzer.get_coords(results, 15, frame_shape)  # left wrist
        rw = analyzer.get_coords(results, 16, frame_shape)  # right wrist
        lh = analyzer.get_coords(results, 23, frame_shape)  # left hip
        rh = analyzer.get_coords(results, 24, frame_shape)  # right hip
        
        # Calculate elbow angles (should be ~90° in doorway stretch)
        left_elbow = analyzer.calculate_angle(ls, le, lw)
        right_elbow = analyzer.calculate_angle(rs, re, rw)
        avg_elbow = (left_elbow + right_elbow) / 2
        
        # Shoulder spread (wider = better stretch)
        # Calculate angle between left arm and right arm
        shoulder_spread = abs(le[0] - re[0])  # Horizontal distance between elbows
        shoulder_width = abs(ls[0] - rs[0])
        spread_ratio = shoulder_spread / max(shoulder_width, 1)
        
        # Arms should be wide (ratio > 1.5 means good spread)
        arms_spread_wide = spread_ratio > 1.5
        
        # Back posture
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        back_angle = 180 - abs(analyzer.calculate_angle(
            (hip_mid[0], hip_mid[1] + 100), hip_mid, shoulder_mid
        ))
        
        # Stability tracking
        self.stability_detector.update(hip_mid[0], hip_mid[1])
        
        return {
            'left_elbow': left_elbow,
            'right_elbow': right_elbow,
            'avg_elbow': avg_elbow,
            'shoulder_spread': shoulder_spread,
            'spread_ratio': spread_ratio,
            'arms_spread_wide': arms_spread_wide,
            'back': back_angle,
            'joints_coords': {
                'ls': ls, 'rs': rs, 'le': le, 're': re,
                'lw': lw, 'rw': rw, 'lh': lh, 'rh': rh
            }
        }
    
    def get_target_poses(self) -> Dict:
        """Target angles for AR overlay"""
        return {
            'holding': {
                'avg_elbow': 90,  # Elbows at 90°
                'spread_ratio': 1.5,  # Arms spread wide
                'back': 165,
                'tolerance': 15
            }
        }
    
    def validate_form(self, angles: Dict) -> Dict:
        """Validate chest stretch form"""
        feedback = {}
        
        # Elbow position (should be ~90°)
        elbow = angles.get('avg_elbow', 0)
        if 80 <= elbow <= 110:
            feedback['elbows'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=elbow,
                message="Good elbow position"
            )
        elif elbow < 70 or elbow > 120:
            feedback['elbows'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=elbow,
                message="Elbows at 90 degrees"
            )
        
        # Arm spread (wider = better stretch)
        if angles.get('arms_spread_wide', False):
            feedback['spread'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles.get('spread_ratio', 0),
                message="Good chest opening"
            )
        else:
            feedback['spread'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=angles.get('spread_ratio', 0),
                message="Spread arms wider"
            )
        
        # Back posture
        back = angles.get('back', 0)
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
                message="Chest up"
            )
        else:
            feedback['posture'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=back,
                message="Too much lean"
            )
        
        return feedback
    
    def update_hold_counter(self, angles: Dict, feedback: Dict) -> Tuple[bool, List[str]]:
        """Update hold timer"""
        hold_complete = False
        warnings = []
        now = time.time()
        
        # Start hold when in position
        if self.hold_start_time is None:
            # Check if in stretch position (arms spread)
            if angles.get('arms_spread_wide', False):
                self.hold_start_time = now
                self.voice.speak("Hold chest stretch", priority=True)
        
        if self.hold_start_time is not None:
            # Calculate hold duration
            self.current_hold_duration = now - self.hold_start_time
            seconds_held = int(self.current_hold_duration)
            
            warnings.append(f"Hold: {seconds_held}s / {self.target_hold_duration}s")
            
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
                            self.voice.give_atomic_command('maintain_posture', priority=True)
                
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
                    angles={'avg_elbow': angles.get('avg_elbow', 90)},
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
                    self.voice.announce_rep(self.hold_count, self.target_holds, form_score)
                
                # Reset for next hold
                self.hold_start_time = None
                self.current_hold_duration = 0
                self.critical_errors_this_hold = 0
                self.stability_detector = StabilityDetector()
                
                if self.hold_count < self.target_holds:
                    self.voice.speak("Rest briefly", priority=True)
        else:
            warnings.append("Spread arms in doorway")
        
        self.frame_counter += 1
        return hold_complete, warnings
    
    def is_complete(self) -> bool:
        """Check if target holds reached"""
        return self.hold_count >= self.target_holds
    
    def get_stats(self) -> Dict:
        """Get exercise statistics"""
        avg_form = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        return {
            'holds': self.hold_count,
            'target_holds': self.target_holds,
            'rejected_holds': self.rejected_count,
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("Chest Stretch Doorway V2 initialized")
    print("Hold: 30 seconds")
    print("Ready to run!")
