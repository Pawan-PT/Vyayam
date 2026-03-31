"""
Single-Leg Balance V2 - Proprioception and stability training

Reference Video: https://www.youtube.com/watch?v=TBt0MJBfKH4
(Single Leg Balance Exercise - Proper Technique)
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
from ..core.unilateral_handler import UnilateralExerciseHandler, Side


class SingleLegBalanceV2:
    """
    Single-Leg Balance - Proprioception training
    
    Level: Intermediate
    Category: Balance
    Target: Proprioception, ankle/knee stabilizers, core
    
    Reference Video: https://www.youtube.com/watch?v=TBt0MJBfKH4
    (Single Leg Balance - Stability Training)
    
    Biomechanics:
    - Primary: Stance knee angle (hip → knee → ankle)
    - Stance knee: 170-180° (slightly bent, not locked)
    - Lifted knee: 90° (knee raised to hip level)
    - Hold duration: 20 seconds per leg
    - Success metric: Minimal sway (stability score)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=TBt0MJBfKH4"
    
    def __init__(self, target_holds=3):
        # Exercise parameters
        self.target_holds_per_side = target_holds
        self.hold_count = 0
        self.rejected_count = 0
        
        # Unilateral tracking
        self.unilateral = UnilateralExerciseHandler(
            total_reps=target_holds,
            exercise_name="Single-Leg Balance"
        )
        
        # Hold tracking
        self.target_hold_duration = 20  # 20 seconds
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
    
    def calculate_angles(self, analyzer: PoseAnalyzer, results, frame_shape) -> Dict:
        """Calculate angles for balance position"""
        # Get joint coordinates
        lh = analyzer.get_coords(results, 23, frame_shape)
        rh = analyzer.get_coords(results, 24, frame_shape)
        lk = analyzer.get_coords(results, 25, frame_shape)
        rk = analyzer.get_coords(results, 26, frame_shape)
        la = analyzer.get_coords(results, 27, frame_shape)
        ra = analyzer.get_coords(results, 28, frame_shape)
        
        # Calculate knee angles
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        # Determine stance leg (foot on ground = higher ankle Y value)
        if ra[1] > la[1]:  # Right foot on ground
            stance_knee = right_knee
            lifted_knee = left_knee
            stance_ankle_y = ra[1]
            lifted_ankle_y = la[1]
            stance_side = 'right'
        else:
            stance_knee = left_knee
            lifted_knee = right_knee
            stance_ankle_y = la[1]
            lifted_ankle_y = ra[1]
            stance_side = 'left'
        
        # Check if leg is actually lifted
        leg_lifted = abs(stance_ankle_y - lifted_ankle_y) > 50
        
        # Stability tracking
        hip_center_x = (lh[0] + rh[0]) / 2
        hip_center_y = (lh[1] + rh[1]) / 2
        self.stability_detector.update(hip_center_x, hip_center_y)
        
        # Get stability metrics
        stability_data = self.stability_detector.get_stability_data()
        sway_score = stability_data['sway']
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'stance_knee': stance_knee,
            'lifted_knee': lifted_knee,
            'leg_lifted': leg_lifted,
            'stance_side': stance_side,
            'sway_score': sway_score,
            'stability_data': stability_data,
            'joints_coords': {
                'lh': lh, 'rh': rh, 'lk': lk, 'rk': rk,
                'la': la, 'ra': ra
            }
        }
    
    def get_target_poses(self) -> Dict:
        """Target angles for AR overlay"""
        return {
            'holding': {
                'stance_knee': 175,
                'lifted_knee': 90,
                'sway': 0,
                'tolerance': 12
            }
        }
    
    def validate_form(self, angles: Dict) -> Dict:
        """Validate balance form"""
        feedback = {}
        
        # Check if leg is lifted
        if not angles.get('leg_lifted', False):
            feedback['lifted'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=0,
                message="Lift leg higher"
            )
        else:
            lifted_knee = angles.get('lifted_knee', 0)
            if 80 <= lifted_knee <= 110:
                feedback['lifted'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=lifted_knee,
                    message="Good knee lift"
                )
            else:
                feedback['lifted'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=lifted_knee,
                    message="Knee to hip level"
                )
        
        # Stance knee position
        stance_knee = angles.get('stance_knee', 0)
        if 170 <= stance_knee <= 180:
            feedback['stance'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=stance_knee,
                message="Good stance"
            )
        elif stance_knee < 160:
            feedback['stance'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=stance_knee,
                message="Stand more upright"
            )
        
        # Stability check
        sway = angles.get('sway_score', 0)
        if sway < 4:
            feedback['stability'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=sway,
                message="Excellent stability"
            )
        elif sway < 8:
            feedback['stability'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=sway,
                message="Good stability"
            )
        elif sway < 12:
            feedback['stability'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=sway,
                message="Reduce sway"
            )
        else:
            feedback['stability'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=sway,
                message="Too much movement"
            )
        
        return feedback
    
    def update_hold_counter(self, angles: Dict, feedback: Dict) -> Tuple[bool, List[str]]:
        """Update hold timer with stability tracking"""
        hold_complete = False
        warnings = []
        now = time.time()
        
        # Start hold timer if not started
        if self.hold_start_time is None:
            self.hold_start_time = now
            current_side = self.unilateral.get_current_side_name()
            self.voice.speak(f"Balance on {current_side} leg", priority=True)
        
        # Calculate hold duration
        self.current_hold_duration = now - self.hold_start_time
        seconds_held = int(self.current_hold_duration)
        seconds_remaining = max(0, self.target_hold_duration - seconds_held)
        
        # Show progress
        current_side = self.unilateral.get_current_side_name()
        current_holds = self.unilateral.get_reps_completed_current_side()
        warnings.append(f"{current_side}: {current_holds}/{self.target_holds_per_side}")
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
                        self.voice.give_atomic_command('maintain_balance', priority=True)
            
            # Reset if too many errors
            if self.critical_errors_this_hold >= 8:
                self.rejected_count += 1
                self.hold_start_time = None
                self.current_hold_duration = 0
                self.critical_errors_this_hold = 0
                self.stability_detector = StabilityDetector()  # Reset
                self.voice.speak("Hold failed", priority=True)
                return False, warnings
        
        # Check if hold complete
        if self.current_hold_duration >= self.target_hold_duration:
            # Calculate form score based on stability
            targets = self.get_target_poses()['holding']
            stability_data = self.stability_detector.get_stability_data()
            
            form_score = FormCalculator.calculate_form_score(
                angles={'stance_knee': angles.get('stance_knee', 175)},
                target_angles=targets,
                stability=stability_data,
                tempo=None  # No tempo for static holds
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
                self.unilateral.increment_rep(form_score)
                self.form_scores.append(form_score)
                hold_complete = True
                
                current_holds = self.unilateral.get_reps_completed_current_side()
                self.voice.announce_rep(current_holds, self.target_holds_per_side, form_score)
            
            # Reset for next hold
            self.hold_start_time = None
            self.current_hold_duration = 0
            self.critical_errors_this_hold = 0
            self.stability_detector = StabilityDetector()  # Reset stability
            
            # Switch legs if this side complete
            if current_holds >= self.target_holds_per_side:
                self.voice.speak(f"Switch to other leg", priority=True)
        
        self.frame_counter += 1
        return hold_complete, warnings
    
    def check_side_switch_needed(self) -> bool:
        """Check if user needs to switch sides"""
        return self.unilateral.needs_side_switch
    
    def handle_side_switch(self):
        """Switch from left to right side"""
        self.unilateral.switch_to_right_side()
        self.hold_start_time = None
        self.current_hold_duration = 0
        self.stability_detector = StabilityDetector()
        self.voice.speak(f"Balance on {self.unilateral.get_current_side_name()} leg", priority=True)
    
    def is_complete(self) -> bool:
        """Check if both sides complete"""
        return self.unilateral.is_complete()
    
    def get_stats(self) -> Dict:
        """Get exercise statistics"""
        stats = self.unilateral.get_stats()
        stats['rejected_holds'] = self.rejected_count
        return stats


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("Single-Leg Balance V2 initialized")
    print("Hold: 20 seconds per leg")
    print("Ready to run!")