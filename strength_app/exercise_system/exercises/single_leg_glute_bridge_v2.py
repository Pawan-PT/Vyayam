"""
Single-Leg Glute Bridge V2 - Unilateral posterior chain

Reference Video: https://www.youtube.com/watch?v=AVAXhy6pl7o
(Single-Leg Glute Bridge - Proper Technique)
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


class SingleLegGluteBridgeV2:
    """
    Single-Leg Glute Bridge - Unilateral posterior chain
    
    Level: Intermediate
    Category: Strength
    Target: Gluteus maximus, hamstrings, core stability
    
    Reference Video: https://www.youtube.com/watch?v=AVAXhy6pl7o
    (Single-Leg Glute Bridge Technique)
    
    Biomechanics:
    - Lying on back, one foot planted
    - Other leg extended straight (or knee bent up)
    - Primary angle: Hip extension (shoulder → hip → knee)
    - Lying: ~0° hip extension
    - Top: 170° (full hip extension)
    - CRITICAL: Hips stay level (no rotation)
    - Hold at top for 2 seconds
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=AVAXhy6pl7o"
    
    def __init__(self, target_reps=10):
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Unilateral tracking
        self.unilateral = UnilateralExerciseHandler(
            total_reps=target_reps,
            exercise_name="Single-Leg Glute Bridge"
        )
        self.current_working_leg = 'right'  # Which leg is working
        
        # Phase tracking
        self.phase = "lying"
        self.last_phase = "lying"
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
        """Calculate angles for glute bridge"""
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
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        # Determine working leg (foot on ground, more bent)
        if ra[1] > la[1]:  # Right foot on ground
            working_knee = right_knee
            extended_knee = left_knee
            working_hip = rh
            working_knee_pos = rk
            working_side = 'right'
        else:
            working_knee = left_knee
            extended_knee = right_knee
            working_hip = lh
            working_knee_pos = lk
            working_side = 'left'
        
        # Hip lift angle (shoulder-hip-knee alignment)
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        
        hip_lift = analyzer.calculate_angle(shoulder_mid, hip_mid, working_knee_pos)
        
        # Hip rotation check (hips should stay level)
        hip_rotation = abs(lh[1] - rh[1])
        hips_rotated = hip_rotation > 30
        
        # Update stability
        self.stability_detector.update(hip_mid[0], hip_mid[1])
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'working_knee': working_knee,
            'extended_knee': extended_knee,
            'working_side': working_side,
            'hip_lift': hip_lift,
            'hip_rotation': hip_rotation,
            'hips_rotated': hips_rotated,
            'joints_coords': {
                'lh': lh, 'rh': rh, 'lk': lk, 'rk': rk,
                'la': la, 'ra': ra, 'ls': ls, 'rs': rs
            }
        }
    
    def get_target_poses(self) -> Dict:
        """Target angles for AR overlay"""
        return {
            'lying': {
                'working_knee': 90,
                'extended_knee': 175,
                'hip_lift': 0,
                'tolerance': 10
            },
            'lifting': {
                'working_knee': 95,
                'extended_knee': 175,
                'hip_lift': 140,
                'tolerance': 12
            },
            'top': {
                'working_knee': 100,
                'extended_knee': 175,
                'hip_lift': 170,
                'body_alignment': 170,
                'tolerance': 8
            },
            'lowering': {
                'working_knee': 95,
                'extended_knee': 175,
                'hip_lift': 120,
                'tolerance': 12
            }
        }
    
    def validate_form(self, angles: Dict, phase: str) -> Dict:
        """Validate glute bridge form"""
        feedback = {}
        
        # CRITICAL: Hips must stay level
        if angles.get('hips_rotated', False):
            feedback['rotation'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=angles.get('hip_rotation', 0),
                message="Hips rotating"
            )
        else:
            feedback['rotation'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles.get('hip_rotation', 0),
                message="Good hip control"
            )
        
        # Extended leg should stay straight
        extended = angles.get('extended_knee', 0)
        if extended >= 165:
            feedback['extended'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=extended,
                message="Good leg extension"
            )
        elif extended >= 155:
            feedback['extended'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=extended,
                message="Straighten leg"
            )
        
        # Hip extension at top
        if phase == 'top':
            hip_lift = angles.get('hip_lift', 0)
            if hip_lift >= 165:
                feedback['extension'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=hip_lift,
                    message="Perfect extension"
                )
            elif hip_lift >= 150:
                feedback['extension'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=hip_lift,
                    message="Lift hips higher"
                )
            else:
                feedback['extension'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=hip_lift,
                    message="Much higher"
                )
        
        return feedback
    
    def update_rep_counter(self, angles: Dict, feedback: Dict) -> Tuple[bool, str, List[str]]:
        """Update rep counter"""
        rep_done = False
        warnings = []
        now = time.time()
        duration = now - self.phase_start
        self.frame_counter += 1
        
        hip_lift = angles.get('hip_lift', 0)
        
        # Show working leg
        working_side = angles.get('working_side', 'right').upper()
        current_reps = self.unilateral.get_reps_completed_current_side()
        warnings.append(f"{working_side}: {current_reps}/{self.target_reps}")
        
        # Error tracking
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            self.critical_errors_this_rep += 1
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if self.frame_counter % 30 == 0:
                        self.voice.give_atomic_command('level_hips', priority=True)
            
            if self.critical_errors_this_rep >= 2 and self.in_rep:
                self.rejected_count += 1
                self.in_rep = False
                self.phase = "lying"
                self.phase_start = now
                self.critical_errors_this_rep = 0
                self.voice.speak("Rep rejected", priority=True)
                return False, self.phase, warnings
        else:
            self.critical_errors_this_rep = max(0, self.critical_errors_this_rep - 1)
        
        # State machine
        if self.phase == "lying":
            if hip_lift <= 100 and duration > 0.5:
                self.phase = "lifting"
                self.phase_start = now
                self.rep_start_time = now
                self.in_rep = True
                self.critical_errors_this_rep = 0
                self.tempo_detector.start_phase('lifting')
                self.voice.give_atomic_command('lift_hips', priority=False)
        
        elif self.phase == "lifting":
            if hip_lift >= 160 and duration > 0.8:
                self.phase = "top"
                self.phase_start = now
                self.tempo_detector.start_phase('top')
                self.voice.give_atomic_command('squeeze_glutes', priority=False)
        
        elif self.phase == "top":
            # Hold for 2 seconds
            if duration >= 2.0:
                self.phase = "lowering"
                self.phase_start = now
                self.tempo_detector.start_phase('lowering')
                self.voice.give_atomic_command('lower_control', priority=False)
        
        elif self.phase == "lowering":
            if hip_lift <= 100 and duration > 0.5:
                # Calculate form score
                targets = self.get_target_poses()['top']
                form_score = FormCalculator.calculate_form_score(
                    angles={'hip_lift': hip_lift, 'extended_knee': angles.get('extended_knee', 175)},
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
                        self.unilateral.increment_rep(form_score)
                        self.form_scores.append(form_score)
                        rep_done = True
                        
                        current_reps = self.unilateral.get_reps_completed_current_side()
                        self.voice.announce_rep(current_reps, self.target_reps, form_score)
                        
                        # Switch legs every 5 reps
                        if current_reps % 5 == 0 and current_reps > 0:
                            self.voice.speak(f"Switch to other leg", priority=True)
                
                self.in_rep = False
                self.phase = "lying"
                self.phase_start = now
                self.critical_errors_this_rep = 0
        
        return rep_done, self.phase, warnings
    
    def check_side_switch_needed(self) -> bool:
        """Check if user needs to switch sides"""
        return self.unilateral.needs_side_switch
    
    def handle_side_switch(self):
        """Switch working leg"""
        self.unilateral.switch_to_right_side()
        self.phase = "lying"
        self.phase_start = time.time()
        self.voice.speak(f"Switch to {self.unilateral.get_current_side_name()} leg", priority=True)
    
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
    print("Single-Leg Glute Bridge V2 initialized")
    print("Unilateral posterior chain - keep hips level")
    print("Ready to run!")