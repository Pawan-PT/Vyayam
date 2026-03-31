"""
HollowBodyHold V2 - Supine hollow position hold — full-body core compression

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class HollowBodyHoldV2:
    """HollowBodyHold — Supine hollow position hold — full-body core compression

    Level: L4 elite
    Category: core
    Movement Pattern: anti-extension
    Target: Rectus abdominis, TVA, hip flexors, serratus anterior

    Biomechanics:
    - Lower back must remain in contact with floor — no arch
    - Arms overhead and legs extended at ~30-45° — the lower the harder
    - Body forms a banana or dish shape; squeeze abs, not just hip flexors

    Key Landmarks (MediaPipe):
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    - LEFT_WRIST (15), RIGHT_WRIST (16)
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_duration=30):
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
        lw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_WRIST, shape)
        rw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_WRIST, shape)
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left_knee')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right_knee')
        avg_knee = (left_knee + right_knee) / 2
        leg_height_ratio = (shape[0] - la[1]) / shape[0] if la else 0.3
        arm_overhead = analyzer.calculate_angle(lh, ls, lw)
        lumbar_contact = analyzer.calculate_angle(ls, lh, lk)
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'leg_height_ratio': leg_height_ratio,
            'arm_overhead': arm_overhead,
            'lumbar_contact': lumbar_contact,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def validate_form(self, angles, phase):
        """Check form quality during the hold."""
        feedback = {}
        lumbar = angles.get('lumbar_contact', 180)
        if lumbar < 155:
            feedback['lumbar'] = {'status': 'error', 'message': 'Press lower back to floor — reduce leg height if needed'}
        arm = angles.get('arm_overhead', 90)
        if arm < 150:
            feedback['arms'] = {'status': 'warning', 'message': 'Reach arms fully overhead'}
        leg_h = angles.get('leg_height_ratio', 0.3)
        if leg_h > 0.5:
            feedback['legs'] = {'status': 'warning', 'message': 'Lower legs to increase difficulty if back stays flat'}
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
