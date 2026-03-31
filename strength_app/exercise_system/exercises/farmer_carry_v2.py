"""
FarmerCarry V2 - Bilateral loaded carry — whole-body stability and grip strength

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class FarmerCarryV2:
    """FarmerCarry — Bilateral loaded carry — whole-body stability and grip strength

    Level: L1 foundation
    Category: carry
    Movement Pattern: loaded-locomotion
    Target: Trapezius, forearms, core, glutes, calves

    Biomechanics:
    - Walk with weights at sides; maintain tall, upright posture throughout
    - Shoulders should be level and retracted — no shrugging or side lean
    - Steps should be controlled; avoid waddling or trunk sway

    Key Landmarks (MediaPipe):
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_EAR (7), RIGHT_EAR (8)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_duration=60):
        self.target_duration = target_duration
        self.hold_start_time = None
        self.elapsed_time = 0.0
        self.hold_completed = False
        self.phase = "setup"
        self.form_scores = []
        self.current_hold_form_scores = []
        self.stability_detector = StabilityDetector()
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()

    def calculate_angles(self, analyzer, results, shape):
        """Extract joint positions and calculate relevant angles."""
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left_knee')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right_knee')
        avg_knee = (left_knee + right_knee) / 2
        shoulder_level_diff = abs(ls[1] - rs[1]) if ls and rs else 0
        trunk_lean = analyzer.calculate_angle(ls, lh, la)
        head_position = analyzer.calculate_angle(ls, lh, la)
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'shoulder_level_diff': shoulder_level_diff,
            'trunk_lean': trunk_lean,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def validate_form(self, angles, phase):
        """Check form quality during the hold."""
        feedback = {}
        sh_diff = angles.get('shoulder_level_diff', 0)
        if sh_diff > 25:
            feedback['shoulders'] = {'status': 'error', 'message': 'Keep shoulders level — weight too heavy'}
        trunk = angles.get('trunk_lean', 180)
        if trunk < 160:
            feedback['trunk'] = {'status': 'warning', 'message': 'Stand tall — no lateral lean'}
        return feedback

    def update_hold_timer(self, angles, feedback, voice):
        """Track hold duration and form quality."""
        now = time.time()
        form_ok = len([v for v in feedback.values() if v.get('status') == 'error']) == 0

        if self.phase == "setup":
            if self._entry_condition(angles):
                self.phase = "holding"
                self.hold_start_time = now
                voice.cue("Hold steady")
        elif self.phase == "holding":
            if form_ok:
                self.elapsed_time = now - self.hold_start_time
            else:
                # Pause timer on form break
                self.hold_start_time = now - self.elapsed_time
                voice.provide_form_cue(feedback)

            remaining = self.target_duration - self.elapsed_time
            if remaining <= 10 and int(remaining) % 5 == 0:
                voice.countdown(int(remaining))

            if self.elapsed_time >= self.target_duration:
                self.hold_completed = True
                self.phase = "complete"
                voice.announce_hold_complete(self.elapsed_time)

        return self.hold_completed, self.phase, self.elapsed_time

    def _entry_condition(self, angles):
        """Override per exercise — detect when hold position is achieved."""
        return True

    def calculate_real_time_form_score(self, angles, joints_coords):
        self.stability_detector.update(joints_coords)
        stability_data = self.stability_detector.get_stability_data()
        form_score = FormCalculator.calculate_form_score(
            angles=angles, target_angles={},
            stability=stability_data, tempo=None
        )
        self.current_hold_form_scores.append(form_score)
        return form_score

    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        frame = self.ar.draw_hold_mode(
            frame, joints_coords, self.elapsed_time, self.target_duration, form_score
        )
        return frame

    def get_stats(self):
        avg_form = (sum(self.current_hold_form_scores) /
                    len(self.current_hold_form_scores)) if self.current_hold_form_scores else 0
        return {
            'hold_completed': self.hold_completed,
            'elapsed_time': round(self.elapsed_time, 1),
            'target_duration': self.target_duration,
            'avg_form_score': round(avg_form, 1),
        }
