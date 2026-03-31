"""
Calf Stretch V2 - Standing calf stretch with hold tracking

IMPROVEMENTS FROM V1:
- Fixed hold counting with voice countdown
- Proper rest phase between holds
- Real form scoring
- Atomic voice commands
- Fixed phase transitions

Reference Video: https://www.youtube.com/watch?v=sKuN62fRVxo
(Calf Stretch Technique - Physiotherapy Demonstration)
"""

from .base_exercise import BaseExercise
from ..core.data_models import FormStatus, JointFeedback
from ..core.form_calculator import FormCalculator, StabilityDetector
import time
from typing import Dict, Tuple, List


class CalfStretchV2(BaseExercise):
    """
    Calf Stretch - Standing position
    
    Level: Foundation
    Category: Stretching
    Target: Gastrocnemius, Soleus
    
    Reference Video: https://www.youtube.com/watch?v=sKuN62fRVxo
    (Calf Stretch Technique - Physiotherapy Demonstration)
    
    Biomechanics:
    - Position: Standing facing wall, one leg back
    - Back leg: Completely straight (170-180°)
    - Heel: Must stay on ground
    - Hold: 10 seconds per stretch
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=sKuN62fRVxo"
    
    def __init__(self):
        super().__init__()
        # Hold tracking
        self.hold_start = 0
        self.hold_duration = 0
        self.target_hold_time = 10.0  # 10 seconds per stretch
        self.last_announced_second = -1
        self.rest_duration = 3.0  # 3 second rest
        
        # Form tracking
        self.stability_detector = StabilityDetector()
        self.form_scores = []
        
        # Target configuration
        self.target_reps = 6  # 3 stretches per leg
    
    def get_config(self) -> Dict:
        return {
            'name': 'Calf Stretch',
            'target_muscles': 'Gastrocnemius, Soleus',
            'difficulty': 1,
            'youtube_url': self.REFERENCE_VIDEO_URL,
            'instructions': [
                "Stand facing wall, one leg back with heel on ground",
                "Keep back leg completely straight",
                "Front knee bent, lean forward until stretch felt in calf",
                "Hold stretch for 10 seconds (countdown will guide you)",
                "Relax and rest for 3 seconds between holds",
                "Repeat on both legs"
            ],
            'tracking_joints': {
                'left_hip': 23, 'left_knee': 25, 'left_ankle': 27,
                'right_hip': 24, 'right_knee': 26, 'right_ankle': 28,
                'left_shoulder': 11, 'right_shoulder': 12
            }
        }
    
    def get_required_practice_reps(self) -> int:
        return 2  # 2 practice stretches
    
    def get_target_poses(self) -> Dict:
        """AR target poses for Calf Stretch"""
        return {
            'ready': {
                'back_knee': 165,       # Back leg straight
                'tolerance': 10
            },
            'holding': {
                'back_knee': 170,       # Keep back leg straight during stretch
                'tolerance': 8
            }
        }
    
    def calculate_angles(self, analyzer, results, frame_shape) -> Dict:
        """Calculate angles for calf stretch"""
        joints = self.get_config()['tracking_joints']
        
        lh = analyzer.get_coords(results, joints['left_hip'], frame_shape)
        lk = analyzer.get_coords(results, joints['left_knee'], frame_shape)
        la = analyzer.get_coords(results, joints['left_ankle'], frame_shape)
        rh = analyzer.get_coords(results, joints['right_hip'], frame_shape)
        rk = analyzer.get_coords(results, joints['right_knee'], frame_shape)
        ra = analyzer.get_coords(results, joints['right_ankle'], frame_shape)
        
        left_knee_a = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left')
        right_knee_a = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right')
        
        # Detect back leg (more straight leg is back leg being stretched)
        back_knee = max(left_knee_a, right_knee_a)
        
        # Update stability detector
        self.stability_detector.update({
            'lk': lk, 'rk': rk, 'lh': lh, 'rh': rh
        })
        
        return {
            'left_knee': left_knee_a,
            'right_knee': right_knee_a,
            'back_knee': back_knee,
            'avg_knee': (left_knee_a + right_knee_a) / 2,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra
            }
        }
    
    def validate_form(self, angles: Dict, phase: str) -> Dict:
        """Validate form for calf stretch"""
        feedback = {}
        back_knee = angles['back_knee']
        
        # Back leg should be straight for calf stretch
        if phase == 'holding':
            if back_knee >= 165:
                feedback['knee'] = JointFeedback(
                    FormStatus.CORRECT, back_knee, "Good straight leg"
                )
            elif back_knee >= 155:
                feedback['knee'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, back_knee, "Straighten back leg more"
                )
            else:
                feedback['knee'] = JointFeedback(
                    FormStatus.INCORRECT, back_knee, "Back leg must be straight"
                )
        
        return feedback
    
    def update_rep_counter(self, primary_angle: float, feedback: Dict, 
                          voice_coach) -> Tuple[bool, str, List[str]]:
        """Update rep counter for stretch hold"""
        rep_done = False
        warnings = []
        now = time.time()
        duration = now - self.phase_start
        angle = primary_angle  # back_knee
        self.frame_counter += 1
        
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if voice_coach and self.frame_counter % 60 == 0:
                        voice_coach.speak(fb.message, priority=True)
        
        # STATE MACHINE
        if self.phase == "ready":
            # Waiting for stretch position (back leg straight)
            if angle >= 165 and duration > 0.5:
                self.phase = "holding"
                self.phase_start = now
                self.hold_start = now
                self.hold_duration = 0
                self.in_rep = True
                self.last_announced_second = -1
                
                if voice_coach:
                    voice_coach.speak("Hold this stretch", priority=True)
        
        elif self.phase == "holding":
            self.hold_duration = now - self.hold_start
            
            # Voice countdown during hold
            if voice_coach:
                current_second = int(self.hold_duration)
                if current_second != self.last_announced_second and current_second > 0:
                    self.last_announced_second = current_second
                    
                    # Count every second
                    voice_coach.count_hold_seconds(current_second, int(self.target_hold_time))
            
            # Check if position is maintained
            if angle < 155:
                # Lost position
                if voice_coach:
                    voice_coach.speak("Keep back leg straight", priority=True)
                self.phase = "resting"
                self.phase_start = now
                self.in_rep = False
                self.hold_duration = 0
                self.rejected_count += 1
            
            elif self.hold_duration >= self.target_hold_time:
                # Successful stretch - calculate form score
                targets = self.get_target_poses()['holding']
                current_angles = {'back_knee': angle}
                
                form_score = FormCalculator.calculate_form_score(
                    angles=current_angles,
                    target_angles=targets,
                    stability=self.stability_detector.get_stability_data(),
                    tempo={'too_fast': False, 'too_slow': False}
                )
                
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
                
                # Transition to resting phase
                self.phase = "resting"
                self.phase_start = now
                self.in_rep = False
                self.hold_duration = 0
                
                if voice_coach:
                    voice_coach.give_atomic_command('relax', priority=True)
        
        elif self.phase == "resting":
            # Rest phase with countdown
            rest_elapsed = now - self.phase_start
            
            # Rest complete
            if rest_elapsed >= self.rest_duration:
                self.phase = "ready"
                self.phase_start = now
                
                if voice_coach:
                    if self.rep_count > 0:
                        voice_coach.speak("Switch legs or continue", priority=False)
        
        return rep_done, self.phase, warnings
    
    def get_joint_mapping(self, feedback: Dict, joints: Dict) -> Dict:
        """Map feedback to joints"""
        joint_status = {}
        
        if 'knee' in feedback:
            joint_status[joints['lk']] = feedback['knee'].status
            joint_status[joints['rk']] = feedback['knee'].status
        
        return joint_status
    
    def get_status(self) -> str:
        """Get current status string"""
        if self.probation_mode:
            return f"PRACTICE: {self.practice_count}/{self.get_required_practice_reps()}"
        if self.phase == "holding":
            remaining = max(0, self.target_hold_time - self.hold_duration)
            return f"HOLD: {remaining:.1f}s | STRETCHES: {self.rep_count}/{self.target_reps}"
        elif self.phase == "resting":
            rest_elapsed = time.time() - self.phase_start
            rest_remaining = max(0, self.rest_duration - rest_elapsed)
            return f"REST: {rest_remaining:.1f}s | STRETCHES: {self.rep_count}/{self.target_reps}"
        return f"STRETCHES: {self.rep_count}/{self.target_reps}"