"""
Planche Lean V2 - Isometric forward lean in push-up position past wrists

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class PlancheLeanV2:
    """Planche Lean - Isometric: lean forward until shoulders are past the wrists.

    Level: advanced (L5)
    Category: strength (isometric)
    Movement Pattern: push
    Target: anterior deltoid, serratus anterior, core, wrist flexors

    Biomechanics:
    - Start in push-up position; shift bodyweight forward
    - Shoulders pass over or beyond wrists
    - Body stays in one rigid plank line (no hip pike)
    - Hold position for target_duration seconds
    - Lean angle: shoulder x-position relative to wrist x-position

    Key Landmarks (MediaPipe):
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    - LEFT_WRIST (15), RIGHT_WRIST (16)
    - LEFT_HIP (23), RIGHT_HIP (24)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_duration=20):
        self.target_duration = target_duration
        self.phase = "setup"
        self.last_phase = "setup"
        self.hold_start_time = None
        self.elapsed_hold = 0.0
        self.hold_completed = False
        self.form_scores = []
        self.current_rep_form_scores = []
        self._last_milestone = 0
        self.stability_detector = StabilityDetector()
        self.tempo_detector = TempoDetector()
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()

    def calculate_angles(self, analyzer, results, shape):
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        lw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_WRIST, shape)
        rw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_WRIST, shape)
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        le = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ELBOW, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)

        # Lean: shoulder x vs wrist x (forward lean = shoulder x > wrist x in front-facing)
        shoulder_mid_x = (ls[0] + rs[0]) / 2
        wrist_mid_x = (lw[0] + rw[0]) / 2
        lean_offset = shoulder_mid_x - wrist_mid_x  # positive = shoulders past wrists

        # Body straight
        body_align = analyzer.calculate_angle(ls, lh, lk)

        # Elbow angle (should be locked)
        left_elbow = analyzer.calculate_angle(ls, le, lw)

        return {
            'lean_offset': lean_offset, 'body_align': body_align, 'left_elbow': left_elbow,
            'elapsed_hold': self.elapsed_hold,
            'joints_coords': {'ls': ls, 'rs': rs, 'lw': lw, 'rw': rw, 'lh': lh, 'rh': rh, 'le': le}
        }

    def get_target_poses(self):
        return {
            'setup':   {'lean_offset': 0,  'tolerance': 30},
            'holding': {'lean_offset': 15, 'tolerance': 20},
        }

    def validate_form(self, angles, phase):
        feedback = {}
        body = angles.get('body_align', 175)
        lean = angles.get('lean_offset', 0)
        if phase == 'holding':
            if body < 155:
                feedback['pike'] = JointFeedback(
                    joint='hip', status=FormStatus.WARNING,
                    message="Keep body straight — don't pike"
                )
            if lean < 5:
                feedback['lean'] = JointFeedback(
                    joint='shoulder', status=FormStatus.INFO,
                    message="Lean further — shoulders past wrists"
                )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        angles_dict = angle if isinstance(angle, dict) else {}
        lean = angles_dict.get('lean_offset', 0)

        if self.phase == "setup" and lean > 8:
            self.phase = "holding"
            self.hold_start_time = time.time()
            voice.say("Hold")
        elif self.phase == "holding":
            if self.hold_start_time:
                self.elapsed_hold = time.time() - self.hold_start_time
            milestone = int(self.elapsed_hold // 5) * 5
            if milestone > self._last_milestone and milestone > 0:
                self._last_milestone = milestone
                remaining = max(0, self.target_duration - self.elapsed_hold)
                voice.say(f"{int(remaining)} seconds remaining")
            if self.elapsed_hold >= self.target_duration:
                self.phase = "setup"
                self.hold_completed = True
                rep_done = True
                voice.say("Hold complete!")
            if lean < 2:
                self.phase = "setup"
                self.hold_start_time = None
                self.elapsed_hold = 0.0
                self._last_milestone = 0

        if self.phase != self.last_phase:
            self.last_phase = self.phase
        return rep_done, self.phase, warnings

    def _calculate_rep_form_score(self):
        if self.current_rep_form_scores:
            avg = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg
        return 85.0

    def calculate_real_time_form_score(self, angles, joints_coords):
        self.stability_detector.update(joints_coords)
        target_angles = self.get_target_poses()[self.phase]
        stability_data = self.stability_detector.get_stability_data()
        tempo_data = self.tempo_detector.check_tempo()
        form_score = FormCalculator.calculate_form_score(
            angles=angles, target_angles=target_angles,
            stability=stability_data, tempo=tempo_data)
        self.current_rep_form_scores.append(form_score)
        return form_score

    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        remaining = max(0.0, self.target_duration - self.elapsed_hold)
        frame = self.ar.draw_counted_mode(frame, joints_coords, form_score,
                                          timer_remaining=remaining)
        return frame

    def get_summary(self):
        avg_form = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        return {'hold_completed': self.hold_completed,
                'elapsed_hold': round(self.elapsed_hold, 1),
                'target_duration': self.target_duration,
                'avg_form_score': round(avg_form, 1)}
