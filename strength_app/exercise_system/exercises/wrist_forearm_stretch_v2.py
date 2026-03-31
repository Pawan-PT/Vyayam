"""
Wrist Forearm Stretch V2 - Wrist and forearm flexibility

Reference Video: https://www.youtube.com/watch?v=CLjtSyuE11I
(Wrist and Forearm Stretches - Proper Technique)
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


class WristForearmStretchV2:
    """
    Wrist and Forearm Stretch - Wrist flexibility
    
    Level: Foundation
    Category: Stretching
    Target: Wrist flexors, wrist extensors, forearms
    
    Reference Video: https://www.youtube.com/watch?v=CLjtSyuE11I
    (Wrist and Forearm Stretching Techniques)
    
    Biomechanics:
    - Extend one arm forward at shoulder height
    - Palm up or down (flexor or extensor stretch)
    - Use other hand to gently pull fingers back
    - Target: Elbow straight (170-180°)
    - Hold: 30 seconds per position per side
    - Keep shoulder relaxed
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=CLjtSyuE11I"
    
    def __init__(self, target_holds=2):
        # Exercise parameters (1 hold per side)
        self.target_holds_per_side = target_holds
        self.hold_count = 0
        self.rejected_count = 0
        self.current_side = 'right'  # Start with right wrist
        
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
        """Calculate wrist stretch angles"""
        # Get joint coordinates
        ls = analyzer.get_coords(results, 11, frame_shape)  # left shoulder
        rs = analyzer.get_coords(results, 12, frame_shape)  # right shoulder
        le = analyzer.get_coords(results, 13, frame_shape)  # left elbow
        re = analyzer.get_coords(results, 14, frame_shape)  # right elbow
        lw = analyzer.get_coords(results, 15, frame_shape)  # left wrist
        rw = analyzer.get_coords(results, 16, frame_shape)  # right wrist
        lh = analyzer.get_coords(results, 23, frame_shape)  # left hip
        rh = analyzer.get_coords(results, 24, frame_shape)  # right hip
        
        # Calculate elbow angles (should be straight for wrist stretch)
        left_elbow = analyzer.calculate_angle(ls, le, lw)
        right_elbow = analyzer.calculate_angle(rs, re, rw)
        
        # Determine which arm is stretching (arm more forward = lower elbow Y)
        if re[1] > le[1]:  # Right arm more forward
            stretching_elbow = right_elbow
            stretching_side = 'right'
            stretching_wrist_y = rw[1]
            stretching_shoulder_y = rs[1]
        else:
            stretching_elbow = left_elbow
            stretching_side = 'left'
            stretching_wrist_y = lw[1]
            stretching_shoulder_y = ls[1]
        
        # Check if arm is extended forward (wrist at similar height to shoulder)
        arm_extended = abs(stretching_wrist_y - stretching_shoulder_y) < 80
        
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
            'stretching_elbow': stretching_elbow,
            'stretching_side': stretching_side,
            'arm_extended': arm_extended,
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
                'stretching_elbow': 175,  # Straight arm
                'arm_extended': True,
                'back': 165,
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles: Dict) -> Dict:
        """Validate wrist stretch form"""
        feedback = {}
        
        # Elbow should be straight
        elbow = angles.get('stretching_elbow', 0)
        if elbow >= 170:
            feedback['elbow'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=elbow,
                message="Good arm extension"
            )
        elif elbow >= 160:
            feedback['elbow'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=elbow,
                message="Straighten arm"
            )
        else:
            feedback['elbow'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=elbow,
                message="Arm must be straight"
            )
        
        # Arm should be extended forward
        if angles.get('arm_extended', False):
            feedback['position'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=0,
                message="Good arm position"
            )
        else:
            feedback['position'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=0,
                message="Extend arm forward"
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
                message="Stand upright"
            )
        
        return feedback
    
    def update_hold_counter(self, angles: Dict, feedback: Dict) -> Tuple[bool, List[str]]:
        """Update hold timer"""
        hold_complete = False
        warnings = []
        now = time.time()
        
        # Start hold when in position
        if self.hold_start_time is None:
            if angles.get('arm_extended', False) and angles.get('stretching_elbow', 0) >= 160:
                self.hold_start_time = now
                side = angles.get('stretching_side', 'right').upper()
                self.voice.speak(f"Hold {side} wrist stretch", priority=True)
        
        if self.hold_start_time is not None:
            # Calculate hold duration
            self.current_hold_duration = now - self.hold_start_time
            seconds_held = int(self.current_hold_duration)
            
            warnings.append(f"Hold: {seconds_held}s / {self.target_hold_duration}s")
            warnings.append(f"Side: {angles.get('stretching_side', 'right').upper()}")
            
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
                    angles={'stretching_elbow': angles.get('stretching_elbow', 175)},
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
                    self.voice.speak(f"Switch to {self.current_side} wrist", priority=True)
        else:
            warnings.append("Extend arm forward")
        
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
    print("Wrist Forearm Stretch V2 initialized")
    print("Hold: 30 seconds per side")
    print("Ready to run!")
