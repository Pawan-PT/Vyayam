"""
Sideways Walking V2 - Lateral Stability Exercise

IMPROVEMENTS FROM V1:
✅ FormCalculator integration for real-time scoring
✅ VoiceCoachV2 with atomic commands
✅ Accurate lateral step detection
✅ Practice mode (3 GREEN steps required)
✅ AR overlay V2 support
✅ Knee bend maintenance validation
✅ Better step width detection

CHANGELOG:
- Added FormCalculator for dynamic form scoring
- Integrated VoiceCoachV2 for smooth audio guidance
- Enhanced lateral step width detection
- Added practice mode with 3 GREEN rep requirement
- Improved knee bend validation (should stay slightly bent)
- Added AR overlay targets
- Better posture tracking

TEST NOTES:
- Verify lateral step detection works
- Ensure knee bend is maintained throughout
- Test step width measurement
- Check form score varies realistically
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class SidewaysWalkingV2:
    """
    Sideways Walking - Lateral stability and hip strength
    
    Level: Intermediate
    Category: Balance + Strength
    Target: Hip abductors, gluteus medius, lateral stability
    
    Reference Video: https://www.youtube.com/watch?v=kxQ5vKXW2YU
    (Lateral Walking - Hip Strengthening)
    
    Biomechanics:
    - Knees stay slightly bent throughout (145°)
    - Step sideways with controlled movement
    - Feet come together between steps
    - Maintain upright posture
    
    Phases:
    1. Ready (feet together, slight knee bend)
    2. Stepping (one foot steps sideways)
    3. Stepped (wide stance)
    4. Returning (bring feet together)
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=kxQ5vKXW2YU"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        self.phase = "ready"
        self.last_phase = "ready"
        
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        
        self.form_scores = []
        self.current_rep_form_scores = []
        
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
        self.voice.speak("Step sideways keeping knees bent", priority=True)
    
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
        
        foot_separation = abs(la[0] - ra[0])
        
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
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': (left_knee + right_knee) / 2,
            'foot_separation': foot_separation,
            'back': back_angle,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la, 'ls': ls,
                'rh': rh, 'rk': rk, 'ra': ra, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        return {
            'ready': {
                'foot_separation': 40,
                'avg_knee': 145,
                'back': 165,
                'tolerance': 10
            },
            'stepping': {
                'foot_separation': 80,
                'avg_knee': 145,
                'back': 165,
                'tolerance': 12
            },
            'stepped': {
                'foot_separation': 85,
                'avg_knee': 145,
                'back': 165,
                'tolerance': 10
            },
            'returning': {
                'foot_separation': 50,
                'avg_knee': 145,
                'back': 165,
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        avg_knee = angles.get('avg_knee', 0)
        
        if 130 <= avg_knee <= 160:
            feedback['knees'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=avg_knee,
                message="Good knee position"
            )
        elif avg_knee > 165:
            feedback['knees'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=avg_knee,
                message="Keep knees bent"
            )
        elif avg_knee < 120:
            feedback['knees'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=avg_knee,
                message="Too much knee bend"
            )
        
        if angles.get('back', 0) >= 160:
            feedback['posture'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles['back'],
                message="Good posture"
            )
        elif angles.get('back', 0) >= 145:
            feedback['posture'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=angles['back'],
                message="Stand straighter"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        foot_sep = angle
        
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if voice:
                        voice.speak(fb.message, priority=True)
        
        if self.phase == "ready":
            if foot_sep < 50 and self.tempo_detector.get_phase_duration() > 0.8:
                self.phase = "stepping"
                self.tempo_detector.start_phase('stepping')
                voice.speak("Step sideways", priority=True)
        
        elif self.phase == "stepping":
            if foot_sep > 70 and self.tempo_detector.get_phase_duration() > 0.5:
                self.phase = "stepped"
                self.tempo_detector.start_phase('stepped')
                voice.speak("Bring feet together", priority=True)
        
        elif self.phase == "stepped":
            if self.tempo_detector.get_phase_duration() > 0.4:
                self.phase = "returning"
                self.tempo_detector.start_phase('returning')
        
        elif self.phase == "returning":
            if foot_sep < 45 and self.tempo_detector.get_phase_duration() > 0.5:
                if not has_critical:
                    form_score = self._calculate_rep_form_score()
                    self._handle_rep_completion(form_score, voice)
                    rep_done = True
                else:
                    self.rejected_count += 1
                    voice.speak("Step rejected", priority=True)
                
                self.phase = "ready"
                self.tempo_detector.start_phase('ready')
        
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
    print("SIDEWAYS WALKING V2 - Lateral Stability")
    print("="*70)
    exercise = SidewaysWalkingV2(target_reps=10)
    print("\n✅ Features: Lateral step detection, knee bend validation, posture tracking")
    print("🎯 Exercise ready!")