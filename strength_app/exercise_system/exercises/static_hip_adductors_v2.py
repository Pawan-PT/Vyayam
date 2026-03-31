"""
Static Hip Adductors V2 - Isometric inner thigh exercise

IMPROVEMENTS FROM V1:
- Knee separation detection (squeeze tracking)
- Real form scoring with FormCalculator
- Hold counting with voice (1-5 seconds)
- Atomic voice commands
- Practice mode (2 GREEN holds)

Reference Video: https://www.youtube.com/watch?v=XaVLZT3LYPI
(Static Hip Adductors - Inner Thigh Isometric Exercise)
"""

from .base_exercise import BaseExercise
from ..core.data_models import FormStatus, JointFeedback
from ..core.form_calculator import FormCalculator, StabilityDetector
import time
from typing import Dict, Tuple, List


class StaticHipAdductorsV2(BaseExercise):
    """
    Static Hip Adductors - Isometric inner thigh contraction
    
    Level: Foundation
    Category: Strength (Isometric)
    Target: Hip Adductors, Inner Thigh
    
    Reference Video: https://www.youtube.com/watch?v=XaVLZT3LYPI
    (Static Hip Adductors - Inner Thigh Isometric Exercise)
    
    Biomechanics:
    - Position: Sitting with knees bent, feet flat
    - Equipment: Ball or pillow between knees
    - Action: Squeeze knees together tightly
    - Hold: 5 seconds per rep
    - Target: 10 reps
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=XaVLZT3LYPI"
    
    def __init__(self):
        super().__init__()
        # Hold tracking
        self.hold_start_time = None
        self.current_hold_duration = 0
        self.target_hold_time = 5.0
        self.rest_duration = 2.0
        self.last_announced_second = -1
        
        # Form tracking
        self.stability_detector = StabilityDetector()
        self.form_scores = []
        
        # Target configuration
        self.target_reps = 10
    
    def get_config(self) -> Dict:
        return {
            'name': 'Static Hip Adductors',
            'target_muscles': 'Hip Adductors, Inner Thigh',
            'difficulty': 1,
            'youtube_url': self.REFERENCE_VIDEO_URL,
            'instructions': [
                "Sit on ground with knees bent, feet flat",
                "Place a ball or pillow between knees",
                "Squeeze knees together tightly",
                "Hold contraction for 5 seconds",
                "Release and relax for 2 seconds",
                "Keep back straight throughout"
            ],
            'tracking_joints': {
                'left_hip': 23, 'left_knee': 25, 'left_ankle': 27,
                'right_hip': 24, 'right_knee': 26, 'right_ankle': 28,
                'left_shoulder': 11, 'right_shoulder': 12
            }
        }
    
    def get_required_practice_reps(self) -> int:
        return 2
    
    def get_target_poses(self) -> Dict:
        """AR target poses for Static Hip Adductors"""
        return {
            'ready': {
                'knee_separation': 60,  # Knees apart before squeeze
                'avg_knee': 95,         # Sitting with bent knees
                'tolerance': 10
            },
            'holding': {
                'knee_separation': 25,  # Knees squeezed together
                'avg_knee': 95,         # Maintain sitting position
                'tolerance': 8
            }
        }
    
    def calculate_angles(self, analyzer, results, frame_shape) -> Dict:
        """Calculate angles for static hip adductors"""
        joints = self.get_config()['tracking_joints']
        
        lh = analyzer.get_coords(results, joints['left_hip'], frame_shape)
        lk = analyzer.get_coords(results, joints['left_knee'], frame_shape)
        la = analyzer.get_coords(results, joints['left_ankle'], frame_shape)
        ls = analyzer.get_coords(results, joints['left_shoulder'], frame_shape)
        rh = analyzer.get_coords(results, joints['right_hip'], frame_shape)
        rk = analyzer.get_coords(results, joints['right_knee'], frame_shape)
        ra = analyzer.get_coords(results, joints['right_ankle'], frame_shape)
        rs = analyzer.get_coords(results, joints['right_shoulder'], frame_shape)
        
        # Knee separation (should be close during squeeze)
        knee_separation = abs(lk[0] - rk[0])
        
        # Knee angles
        left_knee_a = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left')
        right_knee_a = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right')
        
        # Back alignment
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        
        vertical_offset = abs(shoulder_mid[0] - hip_mid[0])
        vertical_height = abs(hip_mid[1] - shoulder_mid[1]) if hip_mid[1] > shoulder_mid[1] else 1
        lean_ratio = vertical_offset / max(vertical_height, 1)
        back_a = 180 - (lean_ratio * 60)
        back_a = max(120, min(180, back_a))
        
        # Update stability detector
        self.stability_detector.update({
            'lk': lk, 'rk': rk, 'lh': lh, 'rh': rh
        })
        
        return {
            'knee_separation': knee_separation,
            'left_knee': left_knee_a,
            'right_knee': right_knee_a,
            'avg_knee': (left_knee_a + right_knee_a) / 2,
            'back': back_a,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la, 'ls': ls,
                'rh': rh, 'rk': rk, 'ra': ra, 'rs': rs
            }
        }
    
    def validate_form(self, angles: Dict, phase: str) -> Dict:
        """Validate form for static hip adductors"""
        feedback = {}
        knee_sep = angles['knee_separation']
        avg_knee = angles['avg_knee']
        back = angles['back']
        
        # Knee squeeze validation
        if phase in ['holding', 'squeezing']:
            if knee_sep < 30:
                feedback['squeeze'] = JointFeedback(
                    FormStatus.CORRECT, knee_sep, "Strong squeeze"
                )
            elif knee_sep < 50:
                feedback['squeeze'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, knee_sep, "Squeeze harder"
                )
            else:
                feedback['squeeze'] = JointFeedback(
                    FormStatus.INCORRECT, knee_sep, "Knees too far apart"
                )
        
        # Knee bend position
        if 80 <= avg_knee <= 110:
            feedback['position'] = JointFeedback(
                FormStatus.CORRECT, avg_knee, "Good sitting position"
            )
        elif avg_knee < 70 or avg_knee > 130:
            feedback['position'] = JointFeedback(
                FormStatus.NEEDS_ADJUSTMENT, avg_knee, "Adjust knee angle"
            )
        
        # Posture check
        if back >= 155:
            feedback['posture'] = JointFeedback(
                FormStatus.CORRECT, back, "Good upright posture"
            )
        elif back >= 140:
            feedback['posture'] = JointFeedback(
                FormStatus.NEEDS_ADJUSTMENT, back, "Sit up straighter"
            )
        else:
            feedback['posture'] = JointFeedback(
                FormStatus.INCORRECT, back, "Back too rounded"
            )
        
        return feedback
    
    def update_rep_counter(self, primary_angle: float, feedback: Dict, 
                          voice_coach) -> Tuple[bool, str, List[str]]:
        """Update rep counter for static hold"""
        rep_done = False
        warnings = []
        now = time.time()
        duration = now - self.phase_start
        self.frame_counter += 1
        
        knee_sep = primary_angle  # knee_separation
        
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            self.critical_errors_this_rep += 1
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if voice_coach and self.frame_counter % 30 == 0:
                        voice_coach.speak(fb.message, priority=True)
            
            if self.critical_errors_this_rep >= 3:
                if self.phase == "holding":
                    self.rejected_count += 1
                    self.phase = "resting"
                    self.phase_start = now
                    self.hold_start_time = None
                    self.critical_errors_this_rep = 0
                    if voice_coach:
                        voice_coach.speak("Hold broken", priority=True)
                    return False, self.phase, warnings
        else:
            self.critical_errors_this_rep = max(0, self.critical_errors_this_rep - 1)
        
        # STATE MACHINE
        if self.phase == "resting":
            if duration > self.rest_duration:
                self.phase = "ready"
                self.phase_start = now
                if voice_coach and self.rep_count == 0 and self.practice_count == 0:
                    voice_coach.speak("Squeeze knees together", priority=True)
        
        elif self.phase == "ready":
            # Detect squeeze beginning
            if knee_sep < 40 and duration > 0.5 and not has_critical:
                self.phase = "holding"
                self.phase_start = now
                self.hold_start_time = now
                self.in_rep = True
                self.critical_errors_this_rep = 0
                self.last_announced_second = -1
                if voice_coach:
                    voice_coach.speak("Hold tight", priority=True)
        
        elif self.phase == "holding":
            if self.hold_start_time:
                self.current_hold_duration = now - self.hold_start_time
                
                # Voice countdown during hold
                if voice_coach:
                    current_second = int(self.current_hold_duration)
                    if current_second != self.last_announced_second and current_second > 0:
                        self.last_announced_second = current_second
                        voice_coach.count_hold_seconds(current_second, int(self.target_hold_time))
                
                if self.current_hold_duration >= self.target_hold_time:
                    # Calculate form score
                    targets = self.get_target_poses()['holding']
                    current_angles = {
                        'knee_separation': knee_sep,
                        'avg_knee': feedback.get('position').angle if 'position' in feedback else 95
                    }
                    
                    form_score = FormCalculator.calculate_form_score(
                        angles=current_angles,
                        target_angles=targets,
                        stability=self.stability_detector.get_stability_data(),
                        tempo={'too_fast': False, 'too_slow': False}
                    )
                    
                    if self.in_rep and self.critical_errors_this_rep < 3:
                        if self.probation_mode:
                            if form_score >= 85:
                                self.practice_count += 1
                                if voice_coach:
                                    voice_coach.announce_practice_rep(
                                        self.practice_count,
                                        self.get_required_practice_reps(),
                                        form_score
                                    )
                                
                                if self.practice_count >= self.get_required_practice_reps():
                                    self.probation_mode = False
                                    if voice_coach:
                                        voice_coach.announce_phase_transition(True)
                            else:
                                self.rejected_count += 1
                                if voice_coach:
                                    voice_coach.provide_ar_feedback(form_score)
                        else:
                            self.rep_count += 1
                            self.form_scores.append(form_score)
                            rep_done = True
                            if voice_coach:
                                voice_coach.announce_rep(self.rep_count, self.target_reps, form_score)
                    
                    self.phase = "resting"
                    self.phase_start = now
                    self.hold_start_time = None
                    self.in_rep = False
                    self.current_hold_duration = 0
                    self.critical_errors_this_rep = 0
                    
                    if voice_coach:
                        voice_coach.give_atomic_command('relax', priority=True)
        
        return rep_done, self.phase, warnings
    
    def get_joint_mapping(self, feedback: Dict, joints: Dict) -> Dict:
        """Map feedback to joints"""
        joint_status = {}
        
        if 'squeeze' in feedback:
            joint_status[joints['lk']] = feedback['squeeze'].status
            joint_status[joints['rk']] = feedback['squeeze'].status
        if 'position' in feedback:
            joint_status[joints['lh']] = feedback['position'].status
            joint_status[joints['rh']] = feedback['position'].status
        if 'posture' in feedback:
            joint_status[joints['ls']] = feedback['posture'].status
            joint_status[joints['rs']] = feedback['posture'].status
        
        return joint_status
    
    def get_status(self) -> str:
        """Get current status string"""
        if self.probation_mode:
            return f"PRACTICE: {self.practice_count}/{self.get_required_practice_reps()}"
        elif self.phase == "holding":
            remaining = max(0, self.target_hold_time - self.current_hold_duration)
            return f"HOLD: {remaining:.1f}s | REPS: {self.rep_count}/{self.target_reps}"
        elif self.phase == "resting":
            rest_elapsed = time.time() - self.phase_start
            rest_remaining = max(0, self.rest_duration - rest_elapsed)
            return f"REST: {rest_remaining:.1f}s | REPS: {self.rep_count}/{self.target_reps}"
        return f"REPS: {self.rep_count}/{self.target_reps}"


# ============================================================================
# CHANGE LOG
# ============================================================================
"""
CHANGES FROM V1:
✅ Knee separation detection (tracks squeeze distance)
✅ Real form scoring with FormCalculator
✅ Hold counting with voice (1-5 seconds)
✅ Atomic voice commands: "Squeeze knees", "Hold tight", "Relax"
✅ Practice mode: 2 GREEN holds required
✅ Fixed phase transitions: resting → ready → holding → resting
✅ Posture validation (upright sitting)
✅ YouTube reference video added

TESTED:
✅ Angle detection: Knee separation tracking works
✅ Hold counting: Voice counts 1-5 seconds
✅ Practice mode: Only counts GREEN holds (≥85)
✅ Voice: Smooth atomic commands
✅ AR: Green/Yellow/Red working

KNOWN ISSUES:
- None
"""