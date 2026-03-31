"""
Spanish Squat V2 - VMO activation with band resistance

Reference Video: https://www.youtube.com/watch?v=VjvPjhBYKCU
(Spanish Squat - Wall Squat with Band Technique)
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


class SpanishSquatV2:
    """
    Spanish Squat - Isometric VMO loading
    
    Level: Intermediate
    Category: Strength
    Target: VMO (Vastus Medialis Oblique), Quadriceps
    
    Reference Video: https://www.youtube.com/watch?v=VjvPjhBYKCU
    (Spanish Squat - Proper Technique)
    
    Biomechanics:
    - Primary angle: Knee flexion (hip → knee → ankle)
    - Hold position: 110-135° (60-90° actual knee bend)
    - Band behind knees pulls backward → VMO activation
    - Back against wall throughout
    - Hold duration: 30 seconds
    - CRITICAL: No knee valgus, maintain band tension
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=VjvPjhBYKCU"
    
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
        self.practice_holds_needed = 2
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
        """Calculate angles with wall contact and knee width"""
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
        
        # Check wall contact (shoulders/hips aligned vertically)
        shoulder_mid_x = (ls[0] + rs[0]) / 2
        hip_mid_x = (lh[0] + rh[0]) / 2
        back_wall_contact = abs(shoulder_mid_x - hip_mid_x) < 40
        
        # Knee width (valgus check)
        knee_width = abs(lk[0] - rk[0])
        ankle_width = abs(la[0] - ra[0])
        knee_collapsed = knee_width < (ankle_width * 0.85)
        
        # Symmetry
        knee_diff = abs(left_knee - right_knee)
        
        # Update stability
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        self.stability_detector.update(hip_mid[0], hip_mid[1])
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'back_wall_contact': back_wall_contact,
            'knee_width': knee_width,
            'ankle_width': ankle_width,
            'knee_collapsed': knee_collapsed,
            'knee_diff': knee_diff,
            'joints_coords': {
                'lh': lh, 'rh': rh, 'lk': lk, 'rk': rk,
                'la': la, 'ra': ra, 'ls': ls, 'rs': rs
            }
        }
    
    def get_target_poses(self) -> Dict:
        """Target angles for AR overlay"""
        return {
            'holding': {
                'avg_knee': 120,  # 60-90 degree target
                'back_wall_contact': True,
                'knee_width': 'neutral',
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles: Dict) -> Dict:
        """Validate Spanish squat form"""
        feedback = {}
        avg_knee = angles.get('avg_knee', 0)
        
        # CRITICAL: Wall contact
        if not angles.get('back_wall_contact', False):
            feedback['wall'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=0,
                message="Back against wall"
            )
        else:
            feedback['wall'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=0,
                message="Good wall contact"
            )
        
        # CRITICAL: Knee collapse
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
                message="Good knee position"
            )
        
        # Symmetry
        knee_diff = angles.get('knee_diff', 0)
        if knee_diff < 15:
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=knee_diff,
                message="Knees even"
            )
        elif knee_diff < 25:
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=knee_diff,
                message="Level knees"
            )
        
        # Depth check (60-90 degree target = 110-135 in our measurement)
        if 110 <= avg_knee <= 135:
            feedback['depth'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=avg_knee,
                message="Perfect VMO depth"
            )
        elif 135 < avg_knee <= 150:
            feedback['depth'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=avg_knee,
                message="Good depth"
            )
        elif avg_knee > 160:
            feedback['depth'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=avg_knee,
                message="Slide down more"
            )
        elif avg_knee < 100:
            feedback['depth'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=avg_knee,
                message="Not too deep"
            )
        
        return feedback
    
    def update_hold_counter(self, angles: Dict, feedback: Dict) -> Tuple[bool, List[str]]:
        """Update hold timer"""
        hold_complete = False
        warnings = []
        now = time.time()
        
        avg_knee = angles.get('avg_knee', 0)
        
        # Start hold when in position
        if self.hold_start_time is None:
            # Check if in holding position
            if 100 <= avg_knee <= 150:
                self.hold_start_time = now
                self.voice.speak("Hold this position", priority=True)
        
        if self.hold_start_time is not None:
            # Calculate hold duration
            self.current_hold_duration = now - self.hold_start_time
            seconds_held = int(self.current_hold_duration)
            seconds_remaining = max(0, self.target_hold_duration - seconds_held)
            
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
                            self.voice.give_atomic_command('maintain_form', priority=True)
                
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
                    angles={'avg_knee': avg_knee},
                    target_angles=targets,
                    stability=stability_data,
                    tempo=None
                )
                
                if self.probation_mode:
                    if form_score >= 85:
                        self.practice_holds_completed += 1
                        self.voice.announce_practice_rep(
                            self.practice_holds_completed,
                            self.practice_holds_needed,
                            form_score
                        )
                        
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
            
            # If they stand up too early
            elif avg_knee > 160:
                warnings.append("Maintain position")
        else:
            # Not in position yet
            warnings.append("Get into position")
        
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
    print("Spanish Squat V2 initialized")
    print("Hold: 30 seconds, 3 sets")
    print("Ready to run!")