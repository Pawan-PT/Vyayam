"""
Decline Squats V2 - Patellar tendon loading exercise

Reference Video: https://www.youtube.com/watch?v=sfa9vYi8i68
(Decline Squat - Gold Standard for Patellar Tendinopathy)
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


class DeclineSquatsV2:
    """
    Decline Squats - Patellar tendon rehabilitation
    
    Level: Intermediate
    Category: Strength
    Target: Patellar tendon loading, quadriceps, VMO
    
    Reference Video: https://www.youtube.com/watch?v=sfa9vYi8i68
    (Decline Squat Technique - Patellar Tendinopathy Treatment)
    
    Biomechanics:
    - Performed on 25° decline board (heels elevated)
    - Primary angle: Knee flexion (hip → knee → ankle)
    - Standing: 175° (nearly straight)
    - Target depth: 85-100° (90° full squat on decline)
    - Knees travel OVER toes (expected and therapeutic on decline)
    - Eccentric phase: 3+ seconds (therapeutic loading)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=sfa9vYi8i68"
    
    def __init__(self, target_reps=10):
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "standing"
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
        """Calculate angles for decline squats"""
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
        
        # Back posture
        shoulder_mid_y = (ls[1] + rs[1]) / 2
        hip_mid_y = (lh[1] + rh[1]) / 2
        shoulder_mid_x = (ls[0] + rs[0]) / 2
        hip_mid_x = (lh[0] + rh[0]) / 2
        
        vertical_offset = abs(shoulder_mid_x - hip_mid_x)
        vertical_height = abs(hip_mid_y - shoulder_mid_y) if hip_mid_y > shoulder_mid_y else 1
        lean_ratio = vertical_offset / max(vertical_height, 1)
        back_angle = 180 - (lean_ratio * 60)
        back_angle = max(120, min(180, back_angle))
        
        # Symmetry check
        knee_diff = abs(left_knee - right_knee)
        
        # Update stability
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        self.stability_detector.update(hip_mid[0], hip_mid[1])
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'back': back_angle,
            'knee_diff': knee_diff,
            'joints_coords': {
                'lh': lh, 'rh': rh, 'lk': lk, 'rk': rk,
                'la': la, 'ra': ra, 'ls': ls, 'rs': rs
            }
        }
    
    def get_target_poses(self) -> Dict:
        """Target angles for AR overlay"""
        return {
            'standing': {
                'avg_knee': 175,
                'left_knee': 175,
                'right_knee': 175,
                'back': 165,
                'tolerance': 8
            },
            'descending': {
                'avg_knee': 135,
                'left_knee': 135,
                'right_knee': 135,
                'back': 160,
                'tolerance': 12
            },
            'bottom': {
                'avg_knee': 90,
                'left_knee': 90,
                'right_knee': 90,
                'back': 160,
                'tolerance': 10
            },
            'ascending': {
                'avg_knee': 135,
                'left_knee': 135,
                'right_knee': 135,
                'back': 160,
                'tolerance': 12
            }
        }
    
    def validate_form(self, angles: Dict, phase: str) -> Dict:
        """Validate decline squat form"""
        feedback = {}
        avg_knee = angles.get('avg_knee', 0)
        back = angles.get('back', 0)
        knee_diff = angles.get('knee_diff', 0)
        
        # Symmetry check
        if knee_diff < 12:
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=knee_diff,
                message="Legs even"
            )
        elif knee_diff < 20:
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=knee_diff,
                message="Keep legs even"
            )
        else:
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=knee_diff,
                message="Uneven knees"
            )
        
        # Back posture
        if back >= 155:
            feedback['back'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=back,
                message="Good posture"
            )
        elif back >= 145:
            feedback['back'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=back,
                message="Chest up"
            )
        else:
            feedback['back'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=back,
                message="Too much lean"
            )
        
        # Depth check
        if phase == 'bottom':
            if 85 <= avg_knee <= 100:
                feedback['depth'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=avg_knee,
                    message="Perfect 90° depth"
                )
            elif 100 < avg_knee <= 120:
                feedback['depth'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=avg_knee,
                    message="Good depth"
                )
            elif avg_knee > 130:
                feedback['depth'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=avg_knee,
                    message="Squat deeper"
                )
        
        return feedback
    
    def update_rep_counter(self, angles: Dict, feedback: Dict) -> Tuple[bool, str, List[str]]:
        """Update rep counter with eccentric emphasis"""
        rep_done = False
        warnings = []
        now = time.time()
        duration = now - self.phase_start
        self.frame_counter += 1
        
        avg_knee = angles.get('avg_knee', 0)
        
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
            if avg_knee >= 165 and duration > 0.6:
                self.phase = "descending"
                self.phase_start = now
                self.rep_start_time = now
                self.in_rep = True
                self.critical_errors_this_rep = 0
                self.tempo_detector.start_phase('descending')
                self.voice.give_atomic_command('lower_slow', priority=False)
        
        elif self.phase == "descending":
            rep_duration = now - self.rep_start_time
            
            # Must take 3+ seconds (eccentric emphasis)
            if rep_duration < 2.0 and avg_knee < 110:
                warnings.append("Too fast - slow down")
                if self.frame_counter % 40 == 0:
                    self.voice.speak("Slower", priority=True)
            
            if avg_knee <= 110 and duration > 2.5:
                self.phase = "bottom"
                self.phase_start = now
                self.tempo_detector.start_phase('bottom')
                self.voice.give_atomic_command('reached_bottom', priority=False)
        
        elif self.phase == "bottom":
            if duration > 0.3:
                self.phase = "ascending"
                self.phase_start = now
                self.tempo_detector.start_phase('ascending')
                self.voice.give_atomic_command('push_up', priority=False)
        
        elif self.phase == "ascending":
            if avg_knee >= 165 and duration > 1.5:
                total_time = now - self.rep_start_time
                
                # Calculate form score
                targets = self.get_target_poses()['bottom']
                form_score = FormCalculator.calculate_form_score(
                    angles={'avg_knee': avg_knee, 'back': angles.get('back', 165)},
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
                        self.rep_count += 1
                        self.form_scores.append(form_score)
                        rep_done = True
                        self.voice.announce_rep(self.rep_count, self.target_reps, form_score)
                
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
    print("Decline Squats V2 initialized")
    print("Gold standard for patellar tendinopathy")
    print("Ready to run!")