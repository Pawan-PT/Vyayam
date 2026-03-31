"""
PigeonStretch V2 - Pigeon pose hold — deep hip external rotation and flexor stretch

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class PigeonStretchV2:
    """PigeonStretch — Pigeon pose hold — deep hip external rotation and flexor stretch

    Level: mobility
    Category: mobility
    Movement Pattern: hip-mobility
    Target: Piriformis, obturators, hip flexors, gluteus maximus

    Biomechanics:
    - Front leg knee at ~90° of ER; back leg extended straight behind
    - Hinge forward over front shin to increase hip ER stretch
    - Pelvis should eventually square to the floor — the target position

    Key Landmarks (MediaPipe):
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    - LEFT_ANKLE (27), RIGHT_ANKLE (28)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_duration=45):
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
        self.current_side = 'left'
        self.left_time = 0.0
        self.right_time = 0.0

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
        front_hip_flex = analyzer.calculate_angle(ls, lh, lk)
        back_hip_ext = analyzer.calculate_angle(ls, rh, rk)
        pelvis_square = abs(lh[1] - rh[1]) if lh and rh else 0
        torso_fold = analyzer.calculate_angle(ls, lh, la)
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'front_hip_flex': front_hip_flex,
            'back_hip_ext': back_hip_ext,
            'pelvis_square': pelvis_square,
            'torso_fold': torso_fold,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def validate_form(self, angles, phase):
        """Check form quality during the hold."""
        feedback = {}
        pelvis = angles.get('pelvis_square', 0)
        if pelvis > 40:
            feedback['pelvis'] = {'status': 'warning', 'message': 'Work toward squaring hips to floor'}
        back_hip = angles.get('back_hip_ext', 90)
        if back_hip < 160:
            feedback['back_leg'] = {'status': 'warning', 'message': 'Extend back leg fully — no bend at knee'}
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
            'left_time_completed': round(self.left_time, 1),
            'right_time_completed': round(self.right_time, 1),
        }
