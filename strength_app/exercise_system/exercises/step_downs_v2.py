"""
Step-Downs V2 - Eccentric control training

Reference Video: https://www.youtube.com/watch?v=vXxpXpAMjTQ
(Step-Down Exercise - Eccentric Control for Knee Rehabilitation)
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


class StepDownsV2:
    """
    Step-Downs - Eccentric control for knee rehabilitation
    
    Level: Intermediate
    Category: Strength
    Target: VMO, Quadriceps, Eccentric control
    
    Reference Video: https://www.youtube.com/watch?v=vXxpXpAMjTQ
    (Step-Down Exercise - Eccentric Control Technique)
    
    Biomechanics:
    - Primary angle: Stance knee (hip → knee → ankle)
    - Standing: 175° (straight on step)
    - Bottom: 120° (lowering foot touches ground)
    - CRITICAL: 3-second eccentric lowering phase
    - Focus: Controlled descent, no knee valgus, hips level
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=vXxpXpAMjTQ"
    
    def __init__(self, target_reps=10):
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Unilateral tracking
        self.unilateral = UnilateralExerciseHandler(
            total_reps=target_reps,
            exercise_name="Step-Downs"
        )
        
        # Phase tracking
        self.phase = "standing"  # standing → lowering → bottom → raising → standing
        self.last_phase = "standing"
        self.phase_start = time.time()
        self.rep_start_time = 0
        self.in_rep = False
        
        # Practice mode
        self.probation_mode = True
        self.practice_reps_needed = 3
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
        """Calculate angles for BOTH legs"""
        # Get ALL joint coordinates
        lh = analyzer.get_coords(results, 23, frame_shape)
        rh = analyzer.get_coords(results, 24, frame_shape)
        lk = analyzer.get_coords(results, 25, frame_shape)
        rk = analyzer.get_coords(results, 26, frame_shape)
        la = analyzer.get_coords(results, 27, frame_shape)
        ra = analyzer.get_coords(results, 28, frame_shape)
        ls = analyzer.get_coords(results, 11, frame_shape)
        rs = analyzer.get_coords(results, 12, frame_shape)
        
        # Calculate BOTH sides
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right')
        
        # Stance leg = higher foot (on step)
        if ra[1] < la[1]:  # Right foot on step
            stance_knee = right_knee
            lowering_knee = left_knee
            stance_side = 'right'
        else:
            stance_knee = left_knee
            lowering_knee = right_knee
            stance_side = 'left'
        
        # Hip level check
        hip_level_diff = abs(lh[1] - rh[1])
        
        # Back posture
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        back_angle = 180 - abs(analyzer.calculate_angle(
            (hip_mid[0], hip_mid[1] + 100), hip_mid, shoulder_mid
        ))
        
        # Knee valgus check
        knee_valgus = hip_level_diff > 40 and stance_knee < 140
        
        # Update stability
        self.stability_detector.update(hip_mid[0], hip_mid[1])
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'stance_knee': stance_knee,
            'lowering_knee': lowering_knee,
            'stance_side': stance_side,
            'hip_level_diff': hip_level_diff,
            'back': back_angle,
            'knee_valgus': knee_valgus,
            'joints_coords': {
                'lh': lh, 'rh': rh, 'lk': lk, 'rk': rk,
                'la': la, 'ra': ra, 'ls': ls, 'rs': rs
            }
        }
    
    def get_target_poses(self) -> Dict:
        """Target angles for AR overlay"""
        return {
            'standing': {
                'stance_knee': 175,
                'lowering_knee': 175,
                'back': 165,
                'hip_level': 0,
                'tolerance': 8
            },
            'lowering': {
                'stance_knee': 135,
                'lowering_knee': 165,
                'back': 165,
                'hip_level': 0,
                'tolerance': 12
            },
            'bottom': {
                'stance_knee': 120,
                'lowering_knee': 160,
                'back': 165,
                'hip_level': 10,
                'tolerance': 10
            },
            'raising': {
                'stance_knee': 155,
                'lowering_knee': 170,
                'back': 165,
                'hip_level': 5,
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles: Dict, phase: str) -> Dict:
        """Validate step-down form"""
        feedback = {}
        stance = angles.get('stance_knee', 0)
        hip_level = angles.get('hip_level_diff', 0)
        back = angles.get('back', 0)
        
        # CRITICAL: Knee valgus
        if angles.get('knee_valgus', False):
            feedback['valgus'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=0,
                message="Knee collapse"
            )
        
        # Hip level
        if hip_level < 30:
            feedback['hips'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=hip_level,
                message="Hips level"
            )
        elif hip_level < 50:
            feedback['hips'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=hip_level,
                message="Level hips"
            )
        else:
            feedback['hips'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=hip_level,
                message="Hips uneven"
            )
        
        # Back posture
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
        else:
            feedback['posture'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=back,
                message="Too much lean"
            )
        
        # Depth check
        if phase == 'bottom':
            if 110 <= stance <= 130:
                feedback['depth'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=stance,
                    message="Good control"
                )
            elif stance > 145:
                feedback['depth'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=stance,
                    message="Lower more"
                )
        
        return feedback
    
    def update_rep_counter(self, angles: Dict, feedback: Dict) -> Tuple[bool, str, List[str]]:
        """Update rep counter with eccentric emphasis"""
        rep_done = False
        warnings = []
        now = time.time()
        duration = now - self.phase_start
        self.frame_counter += 1
        
        stance_knee = angles.get('stance_knee', 0)
        
        # Show current side
        current_side = self.unilateral.get_current_side_name()
        current_reps = self.unilateral.get_reps_completed_current_side()
        warnings.append(f"{current_side}: {current_reps}/{self.target_reps}")
        
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
            if stance_knee >= 165 and duration > 0.5:
                self.phase = "lowering"
                self.phase_start = now
                self.rep_start_time = now
                self.in_rep = True
                self.critical_errors_this_rep = 0
                self.tempo_detector.start_phase('lowering')
                self.voice.give_atomic_command('start_descent_slow', priority=False)
        
        elif self.phase == "lowering":
            rep_duration = now - self.rep_start_time
            
            # Must take 2.5+ seconds (eccentric emphasis)
            if rep_duration < 2.0 and stance_knee < 130:
                warnings.append("Too fast - slow down")
                if self.frame_counter % 40 == 0:
                    self.voice.speak("Slower", priority=True)
            
            if stance_knee <= 130 and duration > 2.5:
                self.phase = "bottom"
                self.phase_start = now
                self.tempo_detector.start_phase('bottom')
                self.voice.give_atomic_command('tap_ground', priority=False)
        
        elif self.phase == "bottom":
            if duration > 0.3:
                self.phase = "raising"
                self.phase_start = now
                self.tempo_detector.start_phase('raising')
                self.voice.give_atomic_command('push_up', priority=False)
        
        elif self.phase == "raising":
            if stance_knee >= 165 and duration > 1.0:
                total_time = now - self.rep_start_time
                
                # Calculate form score
                targets = self.get_target_poses()['bottom']
                form_score = FormCalculator.calculate_form_score(
                    angles={'stance_knee': stance_knee, 'back': angles.get('back', 165)},
                    target_angles=targets,
                    stability=self.stability_detector.get_stability_data(),
                    tempo=self.tempo_detector.check_tempo()
                )
                
                # Penalty for fast eccentric
                if total_time < 3.5:
                    warnings.append(f"Eccentric too fast ({total_time:.1f}s)")
                    form_score = max(70, form_score - 10)
                
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
                        self.unilateral.increment_rep(form_score)
                        self.form_scores.append(form_score)
                        rep_done = True
                        
                        current_reps = self.unilateral.get_reps_completed_current_side()
                        self.voice.announce_rep(current_reps, self.target_reps, form_score)
                
                self.in_rep = False
                self.phase = "standing"
                self.phase_start = now
                self.critical_errors_this_rep = 0
        
        return rep_done, self.phase, warnings
    
    def check_side_switch_needed(self) -> bool:
        """Check if user needs to switch sides"""
        return self.unilateral.needs_side_switch
    
    def handle_side_switch(self):
        """Switch from left to right side"""
        self.unilateral.switch_to_right_side()
        self.phase = "standing"
        self.phase_start = time.time()
        self.voice.speak(f"Switch to {self.unilateral.get_current_side_name()} side", priority=True)
    
    def is_complete(self) -> bool:
        """Check if both sides complete"""
        return self.unilateral.is_complete()
    
    def get_stats(self) -> Dict:
        """Get exercise statistics"""
        stats = self.unilateral.get_stats()
        stats['rejected_reps'] = self.rejected_count
        return stats


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("Step-Downs V2 initialized")
    print("Eccentric emphasis - 3+ second lowering phase")
    print("Ready to run!")

    