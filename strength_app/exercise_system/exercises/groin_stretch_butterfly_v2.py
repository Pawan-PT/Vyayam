"""
Groin Stretch Butterfly V2 - Hip adductor flexibility

Reference Video: https://www.youtube.com/watch?v=qYGXgvKTUbE
(Butterfly Stretch - Proper Technique for Hip Flexibility)
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


class GroinStretchButterflyV2:
    """
    Butterfly Stretch - Hip adductor flexibility
    
    Level: Foundation
    Category: Stretching
    Target: Hip adductors, groin, inner thighs
    
    Reference Video: https://www.youtube.com/watch?v=qYGXgvKTUbE
    (Butterfly Stretch Technique)
    
    Biomechanics:
    - Sit on ground, soles of feet together
    - Knees fall out to sides (butterfly position)
    - Hold feet, gently press knees toward floor
    - Target: Knee height difference (knees lower than hips)
    - Hold: 30 seconds
    - Keep back straight, lean forward slightly for deeper stretch
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=qYGXgvKTUbE"
    
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
        """Calculate butterfly stretch angles"""
        # Get joint coordinates
        lh = analyzer.get_coords(results, 23, frame_shape)  # left hip
        rh = analyzer.get_coords(results, 24, frame_shape)  # right hip
        lk = analyzer.get_coords(results, 25, frame_shape)  # left knee
        rk = analyzer.get_coords(results, 26, frame_shape)  # right knee
        la = analyzer.get_coords(results, 27, frame_shape)  # left ankle
        ra = analyzer.get_coords(results, 28, frame_shape)  # right ankle
        ls = analyzer.get_coords(results, 11, frame_shape)  # left shoulder
        rs = analyzer.get_coords(results, 12, frame_shape)  # right shoulder
        
        # Check if in seated butterfly position
        # Knees should be out to sides (wide apart)
        knee_width = abs(lk[0] - rk[0])
        hip_width = abs(lh[0] - rh[0])
        knee_width_ratio = knee_width / max(hip_width, 1)
        
        # In butterfly, knees are much wider than hips
        in_butterfly_position = knee_width_ratio > 1.8
        
        # Knee drop (knees should be lower than hips for good stretch)
        left_knee_drop = lk[1] - lh[1]  # Positive = knee lower than hip
        right_knee_drop = rk[1] - rh[1]
        avg_knee_drop = (left_knee_drop + right_knee_drop) / 2
        
        # Good stretch = knees significantly below hips
        good_stretch_depth = avg_knee_drop > 50
        
        # Back angle (should stay relatively upright or lean slightly forward)
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        
        # Calculate forward lean
        forward_lean = shoulder_mid[1] - hip_mid[1]  # Positive = leaning forward
        
        # Feet should be close together (approximation using ankles)
        feet_together = abs(la[0] - ra[0]) < 50
        
        # Stability tracking
        self.stability_detector.update(hip_mid[0], hip_mid[1])
        
        return {
            'knee_width': knee_width,
            'knee_width_ratio': knee_width_ratio,
            'in_butterfly_position': in_butterfly_position,
            'avg_knee_drop': avg_knee_drop,
            'good_stretch_depth': good_stretch_depth,
            'forward_lean': forward_lean,
            'feet_together': feet_together,
            'joints_coords': {
                'lh': lh, 'rh': rh, 'lk': lk, 'rk': rk,
                'la': la, 'ra': ra, 'ls': ls, 'rs': rs
            }
        }
    
    def get_target_poses(self) -> Dict:
        """Target angles for AR overlay"""
        return {
            'holding': {
                'knee_width_ratio': 2.0,  # Knees wide
                'avg_knee_drop': 60,  # Good stretch depth
                'feet_together': True,
                'tolerance': 20
            }
        }
    
    def validate_form(self, angles: Dict) -> Dict:
        """Validate butterfly stretch form"""
        feedback = {}
        
        # Check if in butterfly position
        if not angles.get('in_butterfly_position', False):
            feedback['position'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=0,
                message="Get into butterfly"
            )
        else:
            feedback['position'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=0,
                message="Good butterfly position"
            )
        
        # Feet together
        if not angles.get('feet_together', False):
            feedback['feet'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=0,
                message="Bring feet together"
            )
        
        # Stretch depth (knees dropping toward floor)
        if angles.get('good_stretch_depth', False):
            feedback['stretch'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles.get('avg_knee_drop', 0),
                message="Good stretch depth"
            )
        else:
            drop = angles.get('avg_knee_drop', 0)
            if drop > 30:
                feedback['stretch'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=drop,
                    message="Press knees lower"
                )
            else:
                feedback['stretch'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=drop,
                    message="Let knees drop"
                )
        
        return feedback
    
    def update_hold_counter(self, angles: Dict, feedback: Dict) -> Tuple[bool, List[str]]:
        """Update hold timer"""
        hold_complete = False
        warnings = []
        now = time.time()
        
        # Start hold when in position
        if self.hold_start_time is None:
            if angles.get('in_butterfly_position', False):
                self.hold_start_time = now
                self.voice.speak("Hold butterfly stretch", priority=True)
        
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
                    angles={'avg_knee_drop': angles.get('avg_knee_drop', 60)},
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
            warnings.append("Sit in butterfly position")
        
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
    print("Groin Stretch Butterfly V2 initialized")
    print("Hold: 30 seconds, seated position")
    print("Ready to run!")
