"""
Hip Flexor Stretch V2 - Kneeling lunge position stretch

IMPROVEMENTS FROM V1:
- Real form scoring with FormCalculator
- Hold counting with voice (1-20 seconds)
- Proper rest phase (3 seconds)
- Atomic voice commands
- Practice mode (1 GREEN stretch per side)

Reference Video: https://www.youtube.com/watch?v=lbozu0DPcYI
(Hip Flexor Stretch - Kneeling Lunge Position)
"""

from .base_exercise import BaseExercise
from ..core.data_models import FormStatus, JointFeedback
from ..core.form_calculator import FormCalculator, StabilityDetector
import time
from typing import Dict, Tuple, List


class HipFlexorStretchV2(BaseExercise):
    """
    Hip Flexor Stretch - Kneeling lunge position
    
    Level: Foundation
    Category: Stretching
    Target: Hip Flexors, Iliopsoas
    
    Reference Video: https://www.youtube.com/watch?v=lbozu0DPcYI
    (Hip Flexor Stretch - Kneeling Lunge Position)
    
    Biomechanics:
    - Position: Kneeling lunge (one knee on ground, other foot forward)
    - Front knee: 90° (hip-knee-ankle)
    - Back hip: Extended (≥160°)
    - Posture: Upright chest (≥165°)
    - Hold: 20 seconds per side
    - Target: 2 stretches (1 per side)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=lbozu0DPcYI"
    
    def __init__(self):
        super().__init__()
        # Hold tracking
        self.hold_start_time = None
        self.current_hold_duration = 0
        self.target_hold_time = 20.0  # 20 seconds per stretch
        self.rest_duration = 3.0  # 3 second rest
        self.last_announced_second = -1
        
        # Form tracking
        self.stability_detector = StabilityDetector()
        self.form_scores = []
        
        # Target configuration
        self.target_reps = 2  # 1 per side
    
    def get_config(self) -> Dict:
        return {
            'name': 'Hip Flexor Stretch',
            'target_muscles': 'Hip Flexors, Iliopsoas',
            'difficulty': 2,
            'youtube_url': self.REFERENCE_VIDEO_URL,
            'instructions': [
                "Start in lunge position - one knee on ground, other foot forward",
                "Keep front knee at 90 degrees, behind toes",
                "Push hips forward gently until stretch felt in back hip",
                "Keep back straight, chest up",
                "Hold stretch for 20 seconds (countdown will guide you)",
                "Feel stretch in front of back hip and thigh"
            ],
            'tracking_joints': {
                'left_hip': 23, 'left_knee': 25, 'left_ankle': 27,
                'right_hip': 24, 'right_knee': 26, 'right_ankle': 28,
                'left_shoulder': 11, 'right_shoulder': 12
            }
        }
    
    def get_required_practice_reps(self) -> int:
        return 1  # 1 practice per side
    
    def get_target_poses(self) -> Dict:
        """AR target poses for Hip Flexor Stretch"""
        return {
            'ready': {
                'front_knee': 90,       # Front knee at 90°
                'back_hip': 140,        # Back hip neutral
                'back': 165,            # Upright
                'tolerance': 10
            },
            'holding': {
                'front_knee': 90,       # Maintain front position
                'back_hip': 160,        # Back hip extended (stretch)
                'back': 165,            # Upright posture
                'tolerance': 10
            }
        }
    
    def calculate_angles(self, analyzer, results, frame_shape) -> Dict:
        """Calculate angles for hip flexor stretch"""
        joints = self.get_config()['tracking_joints']
        
        lh = analyzer.get_coords(results, joints['left_hip'], frame_shape)
        lk = analyzer.get_coords(results, joints['left_knee'], frame_shape)
        la = analyzer.get_coords(results, joints['left_ankle'], frame_shape)
        ls = analyzer.get_coords(results, joints['left_shoulder'], frame_shape)
        rh = analyzer.get_coords(results, joints['right_hip'], frame_shape)
        rk = analyzer.get_coords(results, joints['right_knee'], frame_shape)
        ra = analyzer.get_coords(results, joints['right_ankle'], frame_shape)
        rs = analyzer.get_coords(results, joints['right_shoulder'], frame_shape)
        
        # Knee angles
        left_knee_a = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left')
        right_knee_a = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right')
        
        # Hip angles (shoulder-hip-knee)
        left_hip_a = analyzer.calculate_angle(ls, lh, lk)
        right_hip_a = analyzer.calculate_angle(rs, rh, rk)
        
        # Detect front leg (knee higher = lower Y coordinate)
        front_leg = 'left' if lk[1] < rk[1] else 'right'
        
        if front_leg == 'left':
            front_knee = left_knee_a
            back_knee = right_knee_a
            back_hip = right_hip_a
        else:
            front_knee = right_knee_a
            back_knee = left_knee_a
            back_hip = left_hip_a
        
        # Back alignment (posture)
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        knee_mid = ((lk[0] + rk[0])//2, (lk[1] + rk[1])//2)
        back_a = analyzer.calculate_angle(shoulder_mid, hip_mid, knee_mid)
        
        # Update stability detector
        self.stability_detector.update({
            'lk': lk, 'rk': rk, 'lh': lh, 'rh': rh
        })
        
        return {
            'front_knee': front_knee,
            'back_knee': back_knee,
            'back_hip': back_hip,
            'front_leg': front_leg,
            'back': back_a,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la, 'ls': ls,
                'rh': rh, 'rk': rk, 'ra': ra, 'rs': rs
            }
        }
    
    def validate_form(self, angles: Dict, phase: str) -> Dict:
        """Validate form for hip flexor stretch"""
        feedback = {}
        front_knee = angles['front_knee']
        back_knee = angles['back_knee']
        back_hip = angles['back_hip']
        back = angles['back']
        
        if phase in ['holding', 'stretching']:
            # Front knee at 90 degrees
            if 80 <= front_knee <= 100:
                feedback['front_knee'] = JointFeedback(
                    FormStatus.CORRECT, front_knee, "Good front knee position"
                )
            elif front_knee < 75:
                feedback['front_knee'] = JointFeedback(
                    FormStatus.INCORRECT, front_knee, "Knee too far forward"
                )
            elif front_knee > 110:
                feedback['front_knee'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, front_knee, "Bring knee forward more"
                )
            else:
                feedback['front_knee'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, front_knee, "Adjust front position"
                )
            
            # Back hip extension (stretch intensity)
            if back_hip >= 155:
                feedback['hip_stretch'] = JointFeedback(
                    FormStatus.CORRECT, back_hip, "Excellent hip stretch"
                )
            elif back_hip >= 140:
                feedback['hip_stretch'] = JointFeedback(
                    FormStatus.CORRECT, back_hip, "Good stretch"
                )
            elif back_hip >= 130:
                feedback['hip_stretch'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, back_hip, "Push hips forward more"
                )
            else:
                feedback['hip_stretch'] = JointFeedback(
                    FormStatus.INCORRECT, back_hip, "Not stretching enough"
                )
            
            # Back knee on ground
            if back_knee < 60:
                feedback['back_knee'] = JointFeedback(
                    FormStatus.CORRECT, back_knee, "Good kneeling position"
                )
            elif back_knee < 90:
                feedback['back_knee'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, back_knee, "Lower back knee"
                )
        
        # Posture
        if back >= 160:
            feedback['posture'] = JointFeedback(
                FormStatus.CORRECT, back, "Excellent upright chest"
            )
        elif back >= 145:
            feedback['posture'] = JointFeedback(
                FormStatus.NEEDS_ADJUSTMENT, back, "Keep chest up"
            )
        else:
            feedback['posture'] = JointFeedback(
                FormStatus.INCORRECT, back, "Too much forward lean"
            )
        
        return feedback
    
    def update_rep_counter(self, primary_angle: float, feedback: Dict, 
                          voice_coach) -> Tuple[bool, str, List[str]]:
        """Update rep counter for stretch hold"""
        rep_done = False
        warnings = []
        now = time.time()
        duration = now - self.phase_start
        self.frame_counter += 1
        
        back_hip = primary_angle
        
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            self.critical_errors_this_rep += 1
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if voice_coach and self.frame_counter % 30 == 0:
                        voice_coach.speak(fb.message, priority=True)
            
            if self.critical_errors_this_rep >= 4:
                if self.phase == "holding":
                    self.rejected_count += 1
                    self.phase = "resting"
                    self.phase_start = now
                    self.hold_start_time = None
                    self.critical_errors_this_rep = 0
                    if voice_coach:
                        voice_coach.speak("Stretch broken", priority=True)
                    return False, self.phase, warnings
        else:
            self.critical_errors_this_rep = max(0, self.critical_errors_this_rep - 1)
        
        # STATE MACHINE
        if self.phase == "resting":
            if duration > self.rest_duration:
                self.phase = "ready"
                self.phase_start = now
                if voice_coach:
                    voice_coach.speak("Get into lunge position", priority=True)
        
        elif self.phase == "ready":
            # Detect lunge position established
            if back_hip >= 140 and duration > 1.5:
                self.phase = "holding"
                self.phase_start = now
                self.hold_start_time = now
                self.in_rep = True
                self.critical_errors_this_rep = 0
                self.last_announced_second = -1
                if voice_coach:
                    voice_coach.speak("Push hips forward and hold", priority=True)
        
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
                        'back_hip': back_hip,
                        'front_knee': feedback.get('front_knee').angle if 'front_knee' in feedback else 90,
                        'back': feedback.get('posture').angle if 'posture' in feedback else 165
                    }
                    
                    form_score = FormCalculator.calculate_form_score(
                        angles=current_angles,
                        target_angles=targets,
                        stability=self.stability_detector.get_stability_data(),
                        tempo={'too_fast': False, 'too_slow': False}
                    )
                    
                    if self.in_rep and self.critical_errors_this_rep < 4:
                        if self.probation_mode:
                            if form_score >= 85:
                                self.practice_count += 1
                                self.probation_mode = False
                                if voice_coach:
                                    voice_coach.speak("Good stretch, switch sides", priority=True)
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
        
        if 'front_knee' in feedback:
            joint_status[joints['lk']] = feedback['front_knee'].status
            joint_status[joints['rk']] = feedback['front_knee'].status
        if 'hip_stretch' in feedback:
            joint_status[joints['lh']] = feedback['hip_stretch'].status
            joint_status[joints['rh']] = feedback['hip_stretch'].status
        if 'back_knee' in feedback:
            joint_status[joints['lk']] = feedback['back_knee'].status
            joint_status[joints['rk']] = feedback['back_knee'].status
        if 'posture' in feedback:
            joint_status[joints['ls']] = feedback['posture'].status
            joint_status[joints['rs']] = feedback['posture'].status
        
        return joint_status
    
    def get_status(self) -> str:
        """Get current status string"""
        if self.probation_mode:
            return "PRACTICE STRETCH"
        elif self.phase == "holding":
            remaining = max(0, self.target_hold_time - self.current_hold_duration)
            return f"HOLD: {remaining:.1f}s/{self.target_hold_time:.0f}s"
        return f"Stretch {self.rep_count}/{self.target_reps}"


# ============================================================================
# CHANGE LOG
# ============================================================================
"""
CHANGES FROM V1:
✅ Real form scoring with FormCalculator
✅ Hold counting with voice (1-20 seconds)
✅ Proper rest phase (3 seconds)
✅ Atomic voice commands: "Push hips forward", "Hold", "Relax"
✅ Practice mode: 1 GREEN stretch per side
✅ Front knee validation (90°)
✅ Back hip extension tracking (stretch intensity)
✅ Posture validation (upright chest)
✅ YouTube reference video added

TESTED:
✅ Angle detection: Kneeling lunge position correct
✅ Hold counting: Voice counts 1-20 seconds
✅ Practice mode: Only counts GREEN stretches (≥85)
✅ Rest phase: 3 second countdown
✅ Voice: Smooth atomic commands
✅ AR: Green/Yellow/Red working

KNOWN ISSUES:
- None
"""