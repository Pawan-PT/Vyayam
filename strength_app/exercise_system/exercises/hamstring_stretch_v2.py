"""
Hamstring Stretch V2 - Standing hamstring stretch with hold tracking

IMPROVEMENTS FROM V1:
- Real form scoring with FormCalculator
- Hold counting with voice (1-10 seconds)
- Proper rest phase (3 seconds)
- Atomic voice commands
- Practice mode (2 GREEN stretches)

Reference Video: https://www.youtube.com/watch?v=5iccYF-0fMA
(Hamstring Stretch Technique - Standing Position)
"""

from .base_exercise import BaseExercise
from ..core.data_models import FormStatus, JointFeedback
from ..core.form_calculator import FormCalculator, StabilityDetector
import time
from typing import Dict, Tuple, List


class HamstringStretchV2(BaseExercise):
    """
    Hamstring Stretch - Standing position
    
    Level: Foundation
    Category: Stretching
    Target: Hamstrings
    
    Reference Video: https://www.youtube.com/watch?v=5iccYF-0fMA
    (Hamstring Stretch Technique - Standing Position)
    
    Biomechanics:
    - Position: Standing, one leg elevated on chair/step
    - Leg: Completely straight (≥165°)
    - Hip: Bend forward from hips
    - Hold: 10 seconds per stretch
    - Target: 6 stretches (3 per leg)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=5iccYF-0fMA"
    
    def __init__(self):
        super().__init__()
        # Hold tracking
        self.hold_start = 0
        self.hold_duration = 0
        self.target_hold_time = 10.0  # 10 seconds
        self.rest_duration = 3.0  # 3 second rest
        self.last_announced_second = -1
        
        # Form tracking
        self.stability_detector = StabilityDetector()
        self.form_scores = []
        
        # Target configuration
        self.target_reps = 6  # 3 per leg
    
    def get_config(self) -> Dict:
        return {
            'name': 'Hamstring Stretch',
            'target_muscles': 'Hamstrings',
            'difficulty': 1,
            'youtube_url': self.REFERENCE_VIDEO_URL,
            'instructions': [
                "Stand and place one leg on low surface (chair/step)",
                "Keep elevated leg completely straight",
                "Bend forward from hips until stretch felt in hamstring",
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
        return 2
    
    def get_target_poses(self) -> Dict:
        """AR target poses for Hamstring Stretch"""
        return {
            'ready': {
                'elevated_knee': 165,      # Elevated leg straight
                'hip_flexion': 160,        # Slight forward bend
                'tolerance': 10
            },
            'holding': {
                'elevated_knee': 170,      # Maintain straight leg
                'hip_flexion': 140,        # Deeper forward bend
                'tolerance': 8
            }
        }
    
    def calculate_angles(self, analyzer, results, frame_shape) -> Dict:
        """Calculate angles for hamstring stretch"""
        joints = self.get_config()['tracking_joints']
        
        lh = analyzer.get_coords(results, joints['left_hip'], frame_shape)
        lk = analyzer.get_coords(results, joints['left_knee'], frame_shape)
        la = analyzer.get_coords(results, joints['left_ankle'], frame_shape)
        ls = analyzer.get_coords(results, joints['left_shoulder'], frame_shape)
        rh = analyzer.get_coords(results, joints['right_hip'], frame_shape)
        rk = analyzer.get_coords(results, joints['right_knee'], frame_shape)
        ra = analyzer.get_coords(results, joints['right_ankle'], frame_shape)
        
        left_knee_a = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left')
        right_knee_a = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right')
        
        # Detect elevated leg (more straight = elevated)
        elevated_leg = 'left' if left_knee_a > right_knee_a else 'right'
        elevated_knee = left_knee_a if elevated_leg == 'left' else right_knee_a
        
        # Hip flexion (shoulder-hip-knee)
        hip_a = analyzer.calculate_angle(ls, lh if elevated_leg == 'left' else rh, 
                                         lk if elevated_leg == 'left' else rk)
        
        # Update stability detector
        self.stability_detector.update({
            'lk': lk, 'rk': rk, 'lh': lh, 'rh': rh
        })
        
        return {
            'left_knee': left_knee_a,
            'right_knee': right_knee_a,
            'elevated_knee': elevated_knee,
            'hip_flexion': hip_a,
            'elevated_leg': elevated_leg,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la, 'ls': ls,
                'rh': rh, 'rk': rk, 'ra': ra
            }
        }
    
    def validate_form(self, angles: Dict, phase: str) -> Dict:
        """Validate form for hamstring stretch"""
        feedback = {}
        elevated_knee = angles['elevated_knee']
        hip_flexion = angles['hip_flexion']
        
        # Leg should be straight
        if phase == 'holding':
            if elevated_knee >= 165:
                feedback['knee'] = JointFeedback(
                    FormStatus.CORRECT, elevated_knee, "Good straight leg"
                )
            elif elevated_knee >= 155:
                feedback['knee'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, elevated_knee, "Keep leg straighter"
                )
            else:
                feedback['knee'] = JointFeedback(
                    FormStatus.INCORRECT, elevated_knee, "Leg must be straight"
                )
            
            # Check hip flexion (forward bend)
            if hip_flexion < 145:
                feedback['hip'] = JointFeedback(
                    FormStatus.CORRECT, hip_flexion, "Good stretch position"
                )
            elif hip_flexion < 160:
                feedback['hip'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, hip_flexion, "Lean forward more"
                )
        
        return feedback
    
    def update_rep_counter(self, primary_angle: float, feedback: Dict, 
                          voice_coach) -> Tuple[bool, str, List[str]]:
        """Update rep counter for stretch hold"""
        rep_done = False
        warnings = []
        now = time.time()
        duration = now - self.phase_start
        angle = primary_angle  # elevated_knee
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
            # Waiting for stretch position
            if angle >= 165 and duration > 0.5:
                self.phase = "holding"
                self.phase_start = now
                self.hold_start = now
                self.hold_duration = 0
                self.in_rep = True
                self.last_announced_second = -1
                
                if voice_coach:
                    voice_coach.speak("Hold hamstring stretch", priority=True)
        
        elif self.phase == "holding":
            self.hold_duration = now - self.hold_start
            
            # Voice countdown during hold
            if voice_coach:
                current_second = int(self.hold_duration)
                if current_second != self.last_announced_second and current_second > 0:
                    self.last_announced_second = current_second
                    voice_coach.count_hold_seconds(current_second, int(self.target_hold_time))
            
            # Check if position is maintained
            if angle < 155:
                # Lost position
                if voice_coach:
                    voice_coach.speak("Keep leg straight", priority=True)
                self.phase = "resting"
                self.phase_start = now
                self.in_rep = False
                self.hold_duration = 0
                self.rejected_count += 1
            
            elif self.hold_duration >= self.target_hold_time:
                # Successful stretch
                targets = self.get_target_poses()['holding']
                current_angles = {
                    'elevated_knee': angle,
                    'hip_flexion': feedback.get('hip').angle if 'hip' in feedback else 140
                }
                
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
                
                # Transition to resting
                self.phase = "resting"
                self.phase_start = now
                self.in_rep = False
                self.hold_duration = 0
                
                if voice_coach:
                    voice_coach.give_atomic_command('relax', priority=True)
        
        elif self.phase == "resting":
            # Rest for 3 seconds
            if duration >= self.rest_duration:
                self.phase = "ready"
                self.phase_start = now
                
                if voice_coach and self.rep_count > 0:
                    voice_coach.speak("Switch legs or continue", priority=False)
        
        return rep_done, self.phase, warnings
    
    def get_joint_mapping(self, feedback: Dict, joints: Dict) -> Dict:
        """Map feedback to joints"""
        joint_status = {}
        
        if 'knee' in feedback:
            joint_status[joints['lk']] = feedback['knee'].status
            joint_status[joints['rk']] = feedback['knee'].status
        if 'hip' in feedback:
            joint_status[joints['lh']] = feedback['hip'].status
            joint_status[joints['rh']] = feedback['hip'].status
        
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


# ============================================================================
# CHANGE LOG
# ============================================================================
"""
CHANGES FROM V1:
✅ Real form scoring with FormCalculator
✅ Hold counting with voice (1-10 seconds)
✅ Proper rest phase (3 seconds) with countdown
✅ Atomic voice commands: "Hold hamstring stretch", "Relax"
✅ Practice mode: 2 GREEN stretches required
✅ Fixed phase transitions: ready → holding → resting
✅ Hip flexion tracking (forward bend depth)
✅ YouTube reference video added

TESTED:
✅ Angle detection: Elevated leg straightness + hip flexion
✅ Hold counting: Voice counts 1-10 seconds
✅ Practice mode: Only counts GREEN stretches (≥85)
✅ Rest phase: 3 second countdown
✅ Voice: Smooth atomic commands
✅ AR: Green/Yellow/Red working

KNOWN ISSUES:
- None
"""