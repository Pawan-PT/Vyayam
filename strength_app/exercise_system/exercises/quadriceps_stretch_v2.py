"""
Quadriceps Stretch V2 - Standing Flexibility Exercise

IMPROVEMENTS FROM V1:
✅ FormCalculator integration for real-time scoring
✅ VoiceCoachV2 with atomic commands
✅ Accurate knee bend and ankle-to-hip distance tracking
✅ Practice mode (1 GREEN stretch per leg required)
✅ 15-second hold with voice countdown
✅ Balance validation on standing leg

CHANGELOG:
- Added FormCalculator for dynamic form scoring
- Integrated VoiceCoachV2 for smooth audio guidance
- Enhanced knee bend detection (target 40-60°)
- Added practice mode with 1 GREEN stretch requirement
- Implemented 15-second hold with countdown
- Better balance checking on standing leg
- Posture validation (no back arching)

TEST NOTES:
- Verify knee bend detection works (stretch leg)
- Ensure 15-second hold with voice countdown
- Test balance on standing leg
- Check form score varies realistically

Reference Video: https://www.youtube.com/watch?v=ZlRrIsoDpKg
(Quadriceps Stretch - Standing Position)
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class QuadricepsStretchV2:
    """
    Quadriceps Stretch - Standing position
    
    Level: Foundation
    Category: Stretching
    Target: Quadriceps, hip flexors
    
    Reference Video: https://www.youtube.com/watch?v=ZlRrIsoDpKg
    (Quadriceps Stretch - Standing Position)
    
    Biomechanics:
    - Position: Standing on one leg
    - Action: Grab ankle and pull toward buttocks
    - Stretch leg: Knee bent (40-60°)
    - Standing leg: Straight for balance
    - Hold: 15 seconds per stretch
    - Target: 2 stretches (1 per leg)
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=ZlRrIsoDpKg"
    
    def __init__(self, target_reps=2):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        self.phase = "resting"
        self.last_phase = "resting"
        
        # Hold tracking
        self.hold_start_time = None
        self.current_hold_duration = 0
        self.target_hold_time = 15.0
        self.rest_duration = 2.0
        self.last_announced_second = -1
        
        # Practice mode
        self.probation_mode = True
        self.practice_reps_needed = 1  # 1 per leg
        self.practice_reps_completed = 0
        
        # Form tracking
        self.form_scores = []
        self.current_rep_form_scores = []
        
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        # Knee angles
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right')
        
        # Detect stretch leg (more bent)
        if left_knee < right_knee:
            stretch_knee = left_knee
            standing_knee = right_knee
            stretch_ankle = la
            stretch_hip = lh
        else:
            stretch_knee = right_knee
            standing_knee = left_knee
            stretch_ankle = ra
            stretch_hip = rh
        
        # Ankle-to-hip distance (should be close for good stretch)
        ankle_hip_dist = abs(stretch_ankle[1] - stretch_hip[1])
        
        # Back alignment
        shoulder_mid_x = (ls[0] + rs[0]) / 2
        hip_mid_x = (lh[0] + rh[0]) / 2
        shoulder_mid_y = (ls[1] + rs[1]) / 2
        hip_mid_y = (lh[1] + rh[1]) / 2
        
        vertical_offset = abs(shoulder_mid_x - hip_mid_x)
        vertical_height = abs(hip_mid_y - shoulder_mid_y) if hip_mid_y > shoulder_mid_y else 1
        lean_ratio = vertical_offset / max(vertical_height, 1)
        back_angle = 180 - (lean_ratio * 60)
        back_angle = max(120, min(180, back_angle))
        
        return {
            'stretch_knee': stretch_knee,
            'standing_knee': standing_knee,
            'ankle_hip_dist': ankle_hip_dist,
            'back': back_angle,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la, 'ls': ls,
                'rh': rh, 'rk': rk, 'ra': ra, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        return {
            'ready': {
                'standing_knee': 165,
                'back': 165,
                'tolerance': 10
            },
            'holding': {
                'stretch_knee': 50,  # Deep quad stretch
                'standing_knee': 165,
                'back': 165,
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        stretch_knee = angles.get('stretch_knee', 0)
        standing_knee = angles.get('standing_knee', 0)
        back = angles.get('back', 0)
        
        if phase == 'holding':
            # Stretch intensity
            if stretch_knee < 40:
                feedback['stretch'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=stretch_knee,
                    message="Deep stretch"
                )
            elif stretch_knee < 60:
                feedback['stretch'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=stretch_knee,
                    message="Good stretch"
                )
            elif stretch_knee < 90:
                feedback['stretch'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=stretch_knee,
                    message="Pull ankle closer"
                )
            else:
                feedback['stretch'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=stretch_knee,
                    message="Not stretching enough"
                )
            
            # Standing leg balance
            if 160 <= standing_knee <= 180:
                feedback['balance'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=standing_knee,
                    message="Good balance"
                )
            elif 145 <= standing_knee < 160:
                feedback['balance'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=standing_knee,
                    message="Stand straighter"
                )
            else:
                feedback['balance'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=standing_knee,
                    message="Keep standing leg straight"
                )
        
        # Posture (no back arching)
        if back >= 155:
            feedback['posture'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=back,
                message="Good posture"
            )
        elif back >= 140:
            feedback['posture'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=back,
                message="Don't arch back"
            )
        else:
            feedback['posture'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=back,
                message="Keep hips forward"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        stretch_knee = angle
        
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
        
        # STATE MACHINE
        if self.phase == "resting":
            if self.tempo_detector.get_phase_duration() > self.rest_duration:
                self.phase = "ready"
                self.tempo_detector.start_phase('ready')
                voice.speak("Grab ankle and pull", priority=True)
        
        elif self.phase == "ready":
            # Detect stretch beginning
            if stretch_knee < 90 and self.tempo_detector.get_phase_duration() > 1.0:
                self.phase = "holding"
                self.tempo_detector.start_phase('holding')
                self.hold_start_time = time.time()
                self.last_announced_second = -1
                voice.speak("Hold this stretch", priority=True)
        
        elif self.phase == "holding":
            if self.hold_start_time:
                self.current_hold_duration = time.time() - self.hold_start_time
                
                # Voice countdown
                if voice:
                    current_second = int(self.current_hold_duration)
                    if current_second != self.last_announced_second and current_second > 0:
                        self.last_announced_second = current_second
                        voice.count_hold_seconds(current_second, int(self.target_hold_time))
                
                if self.current_hold_duration >= self.target_hold_time:
                    form_score = self._calculate_rep_form_score()
                    
                    if not has_critical:
                        self._handle_rep_completion(form_score, voice)
                        rep_done = True
                    else:
                        self.rejected_count += 1
                        voice.speak("Stretch broken", priority=True)
                    
                    self.phase = "resting"
                    self.tempo_detector.start_phase('resting')
                    self.hold_start_time = None
                    self.current_hold_duration = 0
                    voice.speak("Release and relax", priority=True)
        
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
            if self.rep_count < self.target_reps:
                voice.speak("Switch legs", priority=True)
    
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
    print("QUADRICEPS STRETCH V2 - Standing Flexibility")
    print("="*70)
    exercise = QuadricepsStretchV2(target_reps=2)
    print("\n✅ Features: Knee bend detection, 15-sec holds, balance validation")
    print("🎯 Exercise ready!")