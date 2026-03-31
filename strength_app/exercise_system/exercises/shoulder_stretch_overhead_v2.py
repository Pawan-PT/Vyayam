"""
Shoulder Stretch Overhead V2 - Upper body flexibility

Reference Video: https://www.youtube.com/watch?v=2B4RwHvuMz8
(Overhead Shoulder Stretch - Proper Technique)
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


class ShoulderStretchOverheadV2:
    """
    Overhead Shoulder Stretch - Shoulder flexibility
    
    Level: Foundation
    Category: Stretching
    Target: Shoulders, triceps, upper back
    
    Reference Video: https://www.youtube.com/watch?v=2B4RwHvuMz8
    (Overhead Shoulder Stretch Technique)
    
    Biomechanics:
    - Stand upright, raise one arm overhead
    - Bend elbow, reach hand down back
    - Use other hand to gently pull elbow
    - Target: Elbow angle <90° (deep stretch)
    - Hold: 30 seconds per side
    - Keep back straight, no leaning
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=2B4RwHvuMz8"
    
    def __init__(self, target_holds=2):
        # Exercise parameters (1 hold per side)
        self.target_holds_per_side = target_holds
        self.hold_count = 0
        self.rejected_count = 0
        self.current_side = 'right'  # Start with right arm
        
        # Hold tracking
        self.target_hold_duration = 30  # 30 seconds
        self.hold_start_time = None
        self.current_hold_duration = 0
        
        # Practice mode
        self.probation_mode = True
        self.practice_holds_needed = 1  # Just 1 practice hold
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
        """Calculate shoulder stretch angles"""
        # Get joint coordinates
        ls = analyzer.get_coords(results, 11, frame_shape)  # left shoulder
        rs = analyzer.get_coords(results, 12, frame_shape)  # right shoulder
        le = analyzer.get_coords(results, 13, frame_shape)  # left elbow
        re = analyzer.get_coords(results, 14, frame_shape)  # right elbow
        lw = analyzer.get_coords(results, 15, frame_shape)  # left wrist
        rw = analyzer.get_coords(results, 16, frame_shape)  # right wrist
        lh = analyzer.get_coords(results, 23, frame_shape)  # left hip
        rh = analyzer.get_coords(results, 24, frame_shape)  # right hip
        
        # Calculate elbow angles (for stretch depth)
        left_elbow = analyzer.calculate_angle(ls, le, lw)
        right_elbow = analyzer.calculate_angle(rs, re, rw)
        
        # Determine which arm is stretching (arm overhead = lower Y coordinate)
        if re[1] < le[1]:  # Right arm higher (overhead)
            stretching_elbow = right_elbow
            stretching_side = 'right'
            stretching_elbow_y = re[1]
            stretching_shoulder_y = rs[1]
        else:
            stretching_elbow = left_elbow
            stretching_side = 'left'
            stretching_elbow_y = le[1]
            stretching_shoulder_y = ls[1]
        
        # Check if arm is actually overhead (elbow higher than shoulder)
        arm_overhead = stretching_elbow_y < stretching_shoulder_y
        
        # Back posture (should stay upright)
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
            'arm_overhead': arm_overhead,
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
                'stretching_elbow': 80,  # Deep stretch
                'back': 165,
                'arm_overhead': True,
                'tolerance': 15
            }
        }
    
    def validate_form(self, angles: Dict) -> Dict:
        """Validate shoulder stretch form"""
        feedback = {}
        
        # Check if arm is overhead
        if not angles.get('arm_overhead', False):
            feedback['position'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=0,
                message="Raise arm overhead"
            )
        else:
            feedback['position'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=0,
                message="Good arm position"
            )
        
        # Stretch depth (lower angle = deeper stretch)
        elbow = angles.get('stretching_elbow', 0)
        if elbow < 90:
            feedback['stretch'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=elbow,
                message="Good stretch depth"
            )
        elif elbow < 110:
            feedback['stretch'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=elbow,
                message="Reach lower"
            )
        else:
            feedback['stretch'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=elbow,
                message="Deepen stretch"
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
            if angles.get('arm_overhead', False):
                self.hold_start_time = now
                side = angles.get('stretching_side', 'right').upper()
                self.voice.speak(f"Hold {side} arm stretch", priority=True)
        
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
                    angles={'stretching_elbow': angles.get('stretching_elbow', 80)},
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
                if self.hold_count % 2 == 1:  # After first side
                    self.current_side = 'left' if self.current_side == 'right' else 'right'
                    self.voice.speak(f"Switch to {self.current_side} arm", priority=True)
        else:
            warnings.append("Get into position")
        
        self.frame_counter += 1
        return hold_complete, warnings
    
    def is_complete(self) -> bool:
        """Check if target holds reached"""
        return self.hold_count >= (self.target_holds_per_side * 2)  # Both sides
    
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
    print("Shoulder Stretch Overhead V2 initialized")
    print("Hold: 30 seconds per side")
    print("Ready to run!")
