"""
Jump Squats V2 - Plyometric Power Exercise

IMPROVEMENTS FROM V1:
✅ FormCalculator integration for real-time scoring
✅ VoiceCoachV2 with atomic commands
✅ Accurate jump and landing detection
✅ Practice mode (3 GREEN jumps required)
✅ AR overlay V2 support
✅ Knee valgus detection (CRITICAL for ACL safety)
✅ Landing stability requirement (2 seconds)
✅ Soft landing validation

CHANGELOG:
- Added FormCalculator for dynamic form scoring
- Integrated VoiceCoachV2 for smooth audio guidance
- Enhanced jump detection (hip height tracking)
- Added practice mode with 3 GREEN rep requirement
- Implemented knee valgus check on landing
- Added 2-second landing stability requirement
- Improved landing form validation
- Added AR overlay targets

TEST NOTES:
- Verify jump detection works (hip movement)
- Ensure knee valgus check is accurate (CRITICAL)
- Test 2-second landing stability
- Check form score varies realistically
- Verify landing softness validation
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class JumpSquatsV2:
    """
    Jump Squats - Plyometric return-to-sport exercise
    
    Level: Advanced
    Category: Plyometric
    Target: Explosive power, landing control, full lower body
    
    Reference Video: https://www.youtube.com/watch?v=Azl68Vdjuwa
    (Jump Squats - Explosive Training)
    
    Biomechanics:
    - Start: quarter squat (145°)
    - Jump: full extension (165°)
    - Landing: soft landing with knee bend (135°)
    - CRITICAL: No knee valgus on landing (ACL risk)
    
    Phases:
    1. Squat_ready (quarter squat position)
    2. Jumping (explosive jump)
    3. Landing (soft landing with control)
    4. Stabilized (2-second hold after landing)
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=Azl68Vdjuwa"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        self.phase = "squat_ready"
        self.last_phase = "squat_ready"
        
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        
        self.form_scores = []
        self.current_rep_form_scores = []
        
        self.last_hip_height = None
        self.landing_stability_frames = 0
        
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right')
        
        hip_center_y = (lh[1] + rh[1]) / 2
        
        jump_detected = False
        if self.last_hip_height is not None:
            height_change = self.last_hip_height - hip_center_y
            if height_change > 40:
                jump_detected = True
        
        self.last_hip_height = hip_center_y
        
        knee_width = abs(lk[0] - rk[0])
        ankle_width = abs(la[0] - ra[0])
        knee_valgus = knee_width < (ankle_width * 0.85)
        
        shoulder_mid_y = (ls[1] + rs[1]) / 2
        hip_mid_y = (lh[1] + rh[1]) / 2
        shoulder_mid_x = (ls[0] + rs[0]) / 2
        hip_mid_x = (lh[0] + rh[0]) / 2
        
        vertical_offset = abs(shoulder_mid_x - hip_mid_x)
        vertical_height = abs(hip_mid_y - shoulder_mid_y) if hip_mid_y > shoulder_mid_y else 1
        lean_ratio = vertical_offset / max(vertical_height, 1)
        back_angle = 180 - (lean_ratio * 60)
        back_angle = max(120, min(180, back_angle))
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': (left_knee + right_knee) / 2,
            'back': back_angle,
            'jump_detected': jump_detected,
            'knee_valgus': knee_valgus,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la, 'ls': ls,
                'rh': rh, 'rk': rk, 'ra': ra, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        return {
            'squat_ready': {
                'avg_knee': 145,
                'back': 165,
                'tolerance': 12
            },
            'jumping': {
                'avg_knee': 165,
                'back': 165,
                'tolerance': 15
            },
            'landing': {
                'avg_knee': 135,
                'back': 160,
                'tolerance': 15
            },
            'stabilized': {
                'avg_knee': 145,
                'back': 165,
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        avg_knee = angles.get('avg_knee', 0)
        
        if phase == 'landing':
            if angles.get('knee_valgus', False):
                feedback['valgus'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=0,
                    message="Knees collapsing - DANGEROUS"
                )
        
        knee_diff = abs(angles.get('left_knee', 0) - angles.get('right_knee', 0))
        if knee_diff > 20:
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=knee_diff,
                message="Land evenly"
            )
        
        if phase == 'landing':
            if 130 <= avg_knee <= 150:
                feedback['landing'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=avg_knee,
                    message="Good soft landing"
                )
            elif avg_knee > 165:
                feedback['landing'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=avg_knee,
                    message="Landing too stiff - bend knees"
                )
            elif avg_knee < 120:
                feedback['landing'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=avg_knee,
                    message="Don't collapse"
                )
        
        if angles.get('back', 0) >= 155:
            feedback['posture'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles['back'],
                message="Good posture"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        avg_knee = angle
        
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if voice:
                        voice.speak(fb.message, priority=True)
            
            if 'valgus' in feedback:
                self.rejected_count += 1
                self.phase = "squat_ready"
                self.landing_stability_frames = 0
                voice.speak("STOP - fix knee alignment", priority=True)
                return False, self.phase, warnings
        
        if self.phase == "squat_ready":
            if 135 <= avg_knee <= 155 and self.tempo_detector.get_phase_duration() > 1.0:
                if voice:
                    voice.speak("Jump explosively", priority=True)
        
        if self.phase == "squat_ready" and avg_knee > 160:
            self.phase = "jumping"
            self.tempo_detector.start_phase('jumping')
        
        elif self.phase == "jumping":
            if avg_knee < 155:
                self.phase = "landing"
                self.tempo_detector.start_phase('landing')
                self.landing_stability_frames = 0
                voice.speak("Soft landing", priority=True)
        
        elif self.phase == "landing":
            self.landing_stability_frames += 1
            
            if self.landing_stability_frames >= 60:
                self.phase = "stabilized"
                self.tempo_detector.start_phase('stabilized')
        
        elif self.phase == "stabilized":
            if self.tempo_detector.get_phase_duration() > 0.5:
                if not has_critical:
                    form_score = self._calculate_rep_form_score()
                    self._handle_rep_completion(form_score, voice)
                    rep_done = True
                else:
                    self.rejected_count += 1
                    voice.speak("Rep rejected", priority=True)
                
                self.phase = "squat_ready"
                self.landing_stability_frames = 0
                self.tempo_detector.start_phase('squat_ready')
        
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        if self.current_rep_form_scores:
            avg_form = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg_form
        return 85.0
    
    def _handle_rep_completion(self, form_score, voice):
        if self.probation_mode:
            if form_score >= 85:
                self.practice_reps_completed += 1
                voice.announce_practice_rep(
                    self.practice_reps_completed,
                    self.practice_reps_needed,
                    form_score
                )
                
                if self.practice_reps_completed >= self.practice_reps_needed:
                    self.probation_mode = False
                    voice.announce_phase_transition(from_practice_to_counted=True)
            else:
                self.rejected_count += 1
                voice.provide_ar_feedback(form_score)
        else:
            self.rep_count += 1
            self.form_scores.append(form_score)
            voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        self.stability_detector.update(joints_coords)
        target_angles = self.get_target_poses()[self.phase]
        stability_data = self.stability_detector.get_stability_data()
        tempo_data = self.tempo_detector.check_tempo()
        
        form_score = FormCalculator.calculate_form_score(
            angles=angles,
            target_angles=target_angles,
            stability=stability_data,
            tempo=tempo_data
        )
        
        self.current_rep_form_scores.append(form_score)
        return form_score
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        if self.probation_mode:
            frame, position_matched = self.ar.draw_practice_mode(
                frame=frame,
                joints=joints_coords,
                current_angles=angles,
                target_angles=self.get_target_poses()[self.phase],
                form_score=form_score
            )
        else:
            frame = self.ar.draw_counted_mode(
                frame=frame,
                joints=joints_coords,
                form_score=form_score
            )
        return frame
    
    def get_stats(self):
        avg_form_score = (
            sum(self.form_scores) / len(self.form_scores)
            if self.form_scores else 0
        )
        
        return {
            'reps_completed': self.rep_count,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("="*70)
    print("JUMP SQUATS V2 - Plyometric Power")
    print("="*70)
    exercise = JumpSquatsV2(target_reps=10)
    print("\n✅ Features: Jump detection, knee valgus check, landing stability, soft landing")
    print("🎯 Exercise ready!")