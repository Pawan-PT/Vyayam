"""
Step-Ups V2 - Functional VMO strengthening

Reference Video: https://www.youtube.com/watch?v=dQqApCGd5Ss
(Step-Up Exercise - Proper Technique for Knee Rehabilitation)
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


class StepUpsV2:
    """
    Step-Ups - Functional knee strengthening
    
    Level: Intermediate
    Category: Strength
    Target: VMO, Quadriceps, Gluteus Medius, Core stability
    
    Reference Video: https://www.youtube.com/watch?v=dQqApCGd5Ss
    (Step-Up Exercise - Proper Technique for Knee Rehabilitation)
    
    Biomechanics:
    - Primary angle: Lead knee (hip → knee → ankle)
    - Ground position: 90° (lead foot on step, bent knee)
    - Top position: 175° (full extension on step)
    - Critical: No knee valgus, hips level, controlled tempo
    - Eccentric emphasis on descent (2-3 seconds)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=dQqApCGd5Ss"
    
    def __init__(self, target_reps=10):
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Unilateral tracking (one leg at a time)
        self.unilateral = UnilateralExerciseHandler(
            total_reps=target_reps,
            exercise_name="Step-Ups"
        )
        
        # Phase tracking
        self.phase = "ground"  # ground → pushing → top → descending → ground
        self.last_phase = "ground"
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
        """Calculate angles for BOTH legs (handler will filter to current side)"""
        # Get ALL joint coordinates
        lh = analyzer.get_coords(results, 23, frame_shape)  # left hip
        rh = analyzer.get_coords(results, 24, frame_shape)  # right hip
        lk = analyzer.get_coords(results, 25, frame_shape)  # left knee
        rk = analyzer.get_coords(results, 26, frame_shape)  # right knee
        la = analyzer.get_coords(results, 27, frame_shape)  # left ankle
        ra = analyzer.get_coords(results, 28, frame_shape)  # right ankle
        ls = analyzer.get_coords(results, 11, frame_shape)  # left shoulder
        rs = analyzer.get_coords(results, 12, frame_shape)  # right shoulder
        
        # Calculate BOTH sides
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right')
        
        # Determine lead leg (higher foot = on step)
        if ra[1] < la[1]:  # Right foot higher
            lead_knee = right_knee
            trail_knee = left_knee
            lead_side = 'right'
        else:
            lead_knee = left_knee
            trail_knee = right_knee
            lead_side = 'left'
        
        # Hip level check
        hip_level_diff = abs(lh[1] - rh[1])
        
        # Back posture
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        back_angle = 180 - abs(analyzer.calculate_angle(
            (hip_mid[0], hip_mid[1] + 100), hip_mid, shoulder_mid
        ))
        
        # Knee valgus detection
        knee_valgus = hip_level_diff > 35 and lead_knee < 120
        
        # Update stability detector
        self.stability_detector.update(hip_mid[0], hip_mid[1])
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'lead_knee': lead_knee,
            'trail_knee': trail_knee,
            'lead_side': lead_side,
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
            'ground': {
                'lead_knee': 90,
                'trail_knee': 175,
                'back': 165,
                'hip_level': 0,
                'tolerance': 10
            },
            'pushing': {
                'lead_knee': 140,
                'trail_knee': 165,
                'back': 165,
                'hip_level': 0,
                'tolerance': 12
            },
            'top': {
                'lead_knee': 175,
                'trail_knee': 175,
                'back': 165,
                'hip_level': 0,
                'tolerance': 8
            },
            'descending': {
                'lead_knee': 150,
                'trail_knee': 170,
                'back': 165,
                'hip_level': 5,
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles: Dict, phase: str) -> Dict:
        """Validate step-up form"""
        feedback = {}
        lead_knee = angles.get('lead_knee', 0)
        hip_level = angles.get('hip_level_diff', 0)
        back = angles.get('back', 0)
        
        # CRITICAL: Knee valgus (dangerous)
        if angles.get('knee_valgus', False):
            feedback['valgus'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=0,
                message="Knee collapse"
            )
        
        # Hip level (prevent hip hike)
        if hip_level < 20:
            feedback['hips'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=hip_level,
                message="Hips level"
            )
        elif hip_level < 35:
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
                message="Stand upright"
            )
        else:
            feedback['posture'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=back,
                message="Too much lean"
            )
        
        # Phase-specific
        if phase == 'top':
            if lead_knee >= 170:
                feedback['extension'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=lead_knee,
                    message="Full extension"
                )
            elif lead_knee >= 160:
                feedback['extension'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=lead_knee,
                    message="Straighten more"
                )
            else:
                feedback['extension'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=lead_knee,
                    message="Stand fully"
                )
        
        return feedback
    
    def update_rep_counter(self, angles: Dict, feedback: Dict) -> Tuple[bool, str, List[str]]:
        """Update rep counter with form scoring"""
        rep_done = False
        warnings = []
        now = time.time()
        duration = now - self.phase_start
        self.frame_counter += 1
        
        lead_knee = angles.get('lead_knee', 0)
        
        # Show which side is working
        current_side = self.unilateral.get_current_side_name()
        current_reps = self.unilateral.get_reps_completed_current_side()
        warnings.append(f"{current_side}: {current_reps}/{self.target_reps}")
        
        # Error tracking
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        has_warning = any(f.status == FormStatus.NEEDS_ADJUSTMENT for f in feedback.values())
        
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
                self.phase = "ground"
                self.phase_start = now
                self.critical_errors_this_rep = 0
                self.voice.speak("Rep rejected", priority=True)
                return False, self.phase, warnings
        else:
            self.critical_errors_this_rep = max(0, self.critical_errors_this_rep - 1)
        
        # State machine
        if self.phase == "ground":
            if 80 <= lead_knee <= 110 and duration > 0.5:
                self.phase = "pushing"
                self.phase_start = now
                self.rep_start_time = now
                self.in_rep = True
                self.critical_errors_this_rep = 0
                self.tempo_detector.start_phase('pushing')
                self.voice.give_atomic_command('start_ascent', priority=False)
        
        elif self.phase == "pushing":
            rep_duration = now - self.rep_start_time
            
            if rep_duration < 0.8 and lead_knee > 160:
                warnings.append("Too fast")
            
            if lead_knee >= 165 and duration > 1.0:
                self.phase = "top"
                self.phase_start = now
                self.tempo_detector.start_phase('top')
                self.voice.give_atomic_command('stand_tall', priority=False)
        
        elif self.phase == "top":
            if lead_knee >= 170 and duration > 0.5:
                self.phase = "descending"
                self.phase_start = now
                self.tempo_detector.start_phase('descending')
                self.voice.give_atomic_command('start_descent', priority=False)
        
        elif self.phase == "descending":
            rep_duration = now - self.rep_start_time
            
            if lead_knee <= 110 and duration > 1.5:
                total_time = now - self.rep_start_time
                
                # Calculate form score
                targets = self.get_target_poses()['top']
                form_score = FormCalculator.calculate_form_score(
                    angles={'lead_knee': lead_knee, 'back': angles.get('back', 165)},
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
                        # Counted mode: rep always counts
                        self.unilateral.increment_rep(form_score)
                        self.form_scores.append(form_score)
                        rep_done = True
                        
                        current_reps = self.unilateral.get_reps_completed_current_side()
                        self.voice.announce_rep(current_reps, self.target_reps, form_score)
                
                self.in_rep = False
                self.phase = "ground"
                self.phase_start = now
                self.critical_errors_this_rep = 0
        
        return rep_done, self.phase, warnings
    
    def check_side_switch_needed(self) -> bool:
        """Check if user needs to switch sides"""
        return self.unilateral.needs_side_switch
    
    def handle_side_switch(self):
        """Switch from left to right side"""
        self.unilateral.switch_to_right_side()
        self.phase = "ground"
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
    print("Step-Ups V2 initialized")
    print("Unilateral exercise - tracks one leg at a time")
    print("Ready to run!")