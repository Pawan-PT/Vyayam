"""
Reverse Lunges V2 - ACL-safe unilateral strength

Reference Video: https://www.youtube.com/watch?v=xXx1b2XK8E4
(Reverse Lunge - Proper Form for Knee Protection)
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


class ReverseLungesV2:
    """
    Reverse Lunges - ACL-safe unilateral training
    
    Level: Intermediate
    Category: Strength
    Target: Quadriceps, glutes, unilateral strength
    
    Reference Video: https://www.youtube.com/watch?v=xXx1b2XK8E4
    (Reverse Lunge Technique - Safe for Knees)
    
    Biomechanics:
    - Step BACKWARD (safer than forward for ACL)
    - Front knee: 90° at bottom
    - Back knee: 90° at bottom (nearly touches ground)
    - CRITICAL: Front knee stays behind toes (ACL protection)
    - Torso upright throughout
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=xXx1b2XK8E4"
    
    def __init__(self, target_reps=10):
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Unilateral tracking (alternating legs each rep)
        self.unilateral = UnilateralExerciseHandler(
            total_reps=target_reps,
            exercise_name="Reverse Lunges"
        )
        
        # Phase tracking
        self.phase = "standing"
        self.last_phase = "standing"
        self.phase_start = time.time()
        self.rep_start_time = 0
        self.in_rep = False
        
        # Practice mode
        self.probation_mode = True
        self.practice_reps_needed = 4  # 2 per leg
        self.practice_reps_completed = 0
        
        # Form tracking
        self.form_scores = []
        self.stability_detector = StabilityDetector()
        self.tempo_detector = TempoDetector()
        self.critical_errors_this_rep = 0
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        self.frame_counter = 0
    
    def calculate_angles(self, analyzer: PoseAnalyzer, results, frame_shape) -> Dict:
        """Calculate angles for lunge position"""
        # Get joint coordinates
        lh = analyzer.get_coords(results, 23, frame_shape)
        rh = analyzer.get_coords(results, 24, frame_shape)
        lk = analyzer.get_coords(results, 25, frame_shape)
        rk = analyzer.get_coords(results, 26, frame_shape)
        la = analyzer.get_coords(results, 27, frame_shape)
        ra = analyzer.get_coords(results, 28, frame_shape)
        ls = analyzer.get_coords(results, 11, frame_shape)
        rs = analyzer.get_coords(results, 12, frame_shape)
        
        # Calculate both knees
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right')
        
        # Determine front/back leg (front = more forward, lower ankle Y)
        if la[1] > ra[1]:  # Left foot more on ground = front leg
            front_knee = left_knee
            back_knee = right_knee
            front_ankle = la
            front_knee_pos = lk
            front_side = 'left'
        else:
            front_knee = right_knee
            back_knee = left_knee
            front_ankle = ra
            front_knee_pos = rk
            front_side = 'right'
        
        # Back posture
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        back_angle = 180 - abs(analyzer.calculate_angle(
            (hip_mid[0], hip_mid[1] + 100), hip_mid, shoulder_mid
        ))
        
        # Front knee over toe check (should NOT pass in reverse lunge)
        knee_over_toe = False
        if front_knee < 120:  # Only check when lunging
            knee_to_ankle_x = abs(front_knee_pos[0] - front_ankle[0])
            knee_over_toe = knee_to_ankle_x > 80
        
        # Update stability
        self.stability_detector.update(hip_mid[0], hip_mid[1])
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'front_knee': front_knee,
            'back_knee': back_knee,
            'front_side': front_side,
            'back': back_angle,
            'knee_over_toe': knee_over_toe,
            'joints_coords': {
                'lh': lh, 'rh': rh, 'lk': lk, 'rk': rk,
                'la': la, 'ra': ra, 'ls': ls, 'rs': rs
            }
        }
    
    def get_target_poses(self) -> Dict:
        """Target angles for AR overlay"""
        return {
            'standing': {
                'left_knee': 175,
                'right_knee': 175,
                'back': 165,
                'tolerance': 10
            },
            'stepping_back': {
                'front_knee': 160,
                'back_knee': 155,
                'back': 165,
                'tolerance': 12
            },
            'bottom': {
                'front_knee': 90,
                'back_knee': 90,
                'back': 165,
                'tolerance': 10
            },
            'returning': {
                'front_knee': 130,
                'back_knee': 120,
                'back': 165,
                'tolerance': 12
            }
        }
    
    def validate_form(self, angles: Dict, phase: str) -> Dict:
        """Validate reverse lunge form"""
        feedback = {}
        front = angles.get('front_knee', 0)
        back_knee = angles.get('back_knee', 0)
        back_angle = angles.get('back', 0)
        
        # CRITICAL: Front knee should NOT go over toe
        if angles.get('knee_over_toe', False):
            feedback['knee_forward'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=0,
                message="Knee past toe"
            )
        
        # Torso upright
        if back_angle >= 155:
            feedback['posture'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=back_angle,
                message="Good posture"
            )
        elif back_angle >= 145:
            feedback['posture'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=back_angle,
                message="Chest up"
            )
        else:
            feedback['posture'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=back_angle,
                message="Too much lean"
            )
        
        # Phase-specific
        if phase == 'bottom':
            # Front knee at 90 degrees
            if 85 <= front <= 100:
                feedback['front_depth'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=front,
                    message="Perfect angle"
                )
            elif 100 < front <= 120:
                feedback['front_depth'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=front,
                    message="Good depth"
                )
            elif front > 130:
                feedback['front_depth'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=front,
                    message="Lower more"
                )
            
            # Back knee should nearly touch ground
            if 80 <= back_knee <= 100:
                feedback['back_depth'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=back_knee,
                    message="Good back knee"
                )
            elif back_knee > 120:
                feedback['back_depth'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=back_knee,
                    message="Drop back knee"
                )
        
        return feedback
    
    def update_rep_counter(self, angles: Dict, feedback: Dict) -> Tuple[bool, str, List[str]]:
        """Update rep counter"""
        rep_done = False
        warnings = []
        now = time.time()
        duration = now - self.phase_start
        self.frame_counter += 1
        
        front_knee = angles.get('front_knee', 0)
        
        # Show progress
        current_side = angles.get('front_side', 'left')
        warnings.append(f"Working: {current_side.upper()} leg")
        
        # Error tracking
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            self.critical_errors_this_rep += 1
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if self.frame_counter % 30 == 0:
                        self.voice.give_atomic_command('form_error', priority=True)
            
            if self.critical_errors_this_rep >= 2 and self.in_rep:
                self.rejected_count += 1
                self.in_rep = False
                self.phase = "standing"
                self.phase_start = now
                self.critical_errors_this_rep = 0
                self.voice.speak("Rep rejected", priority=True)
                return False, self.phase, warnings
        else:
            self.critical_errors_this_rep = max(0, self.critical_errors_this_rep - 1)
        
        # State machine
        if self.phase == "standing":
            if front_knee >= 165 and duration > 0.5:
                # Ready state - waiting for lunge
                pass
        
        # Detect stepping back
        if self.phase == "standing" and front_knee < 155:
            self.phase = "stepping_back"
            self.phase_start = now
            self.rep_start_time = now
            self.in_rep = True
            self.critical_errors_this_rep = 0
            self.tempo_detector.start_phase('stepping_back')
            self.voice.give_atomic_command('step_back', priority=False)
        
        elif self.phase == "stepping_back":
            if front_knee <= 120 and duration > 0.8:
                self.phase = "bottom"
                self.phase_start = now
                self.tempo_detector.start_phase('bottom')
                self.voice.give_atomic_command('hold_position', priority=False)
        
        elif self.phase == "bottom":
            if duration > 0.5:
                self.phase = "returning"
                self.phase_start = now
                self.tempo_detector.start_phase('returning')
                self.voice.give_atomic_command('step_forward', priority=False)
        
        elif self.phase == "returning":
            if front_knee >= 165 and duration > 1.0:
                # Calculate form score
                targets = self.get_target_poses()['bottom']
                form_score = FormCalculator.calculate_form_score(
                    angles={'front_knee': front_knee, 'back': angles.get('back', 165)},
                    target_angles=targets,
                    stability=self.stability_detector.get_stability_data(),
                    tempo=self.tempo_detector.check_tempo()
                )
                
                if self.in_rep and self.critical_errors_this_rep < 2:
                    if self.probation_mode:
                        if form_score >= 85:
                            self.practice_reps_completed += 1
                            self.voice.announce_practice_rep(
                                self.practice_reps_completed,
                                self.practice_reps_needed,
                                form_score
                            )
                            
                            if self.practice_reps_completed >= self.practice_reps_needed:
                                self.probation_mode = False
                                warnings.append("✅ Practice complete")
                                self.voice.announce_phase_transition(True)
                        else:
                            self.voice.provide_ar_feedback(form_score)
                            self.rejected_count += 1
                    else:
                        self.rep_count += 1
                        self.form_scores.append(form_score)
                        rep_done = True
                        self.voice.announce_rep(self.rep_count, self.target_reps, form_score)
                        
                        # Alternate legs reminder
                        if self.rep_count % 2 == 0:
                            self.voice.speak("Switch legs", priority=True)
                
                self.in_rep = False
                self.phase = "standing"
                self.phase_start = now
                self.critical_errors_this_rep = 0
        
        return rep_done, self.phase, warnings
    
    def is_complete(self) -> bool:
        """Check if target reps reached"""
        return self.rep_count >= self.target_reps
    
    def get_stats(self) -> Dict:
        """Get exercise statistics"""
        avg_form = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        return {
            'reps': self.rep_count,
            'target_reps': self.target_reps,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("Reverse Lunges V2 initialized")
    print("ACL-safe - knee stays behind toes")
    print("Ready to run!")