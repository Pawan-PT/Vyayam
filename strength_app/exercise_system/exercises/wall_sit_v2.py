"""
Wall Sit V2 - Isometric quad and glute endurance hold

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class WallSitV2:
    """Wall Sit - Isometric lower body hold with back against wall.

    Level: foundation
    Category: strength
    Movement Pattern: squat (isometric)
    Target: quadriceps, glutes, hamstrings, core

    Biomechanics:
    - Hips and knees at ~90° (thighs parallel to floor)
    - Back flat against wall — shoulder and hip in vertical alignment
    - Knees track directly over toes (no valgus)
    - Heels directly below knees, feet flat on floor

    Key Landmarks (MediaPipe):
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    - LEFT_ANKLE (27), RIGHT_ANKLE (28)
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_duration=30):
        self.target_duration = target_duration
        self.phase = "setup"          # setup → holding → complete
        self.last_phase = "setup"
        self.hold_start_time = None
        self.elapsed_hold = 0.0
        self.hold_completed = False
        self.form_scores = []
        self.current_rep_form_scores = []
        self.stability_detector = StabilityDetector()
        self.tempo_detector = TempoDetector()
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        self._last_milestone = 0

    def calculate_angles(self, analyzer, results, shape):
        """Extract joint positions and calculate knee and trunk angles."""
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
        avg_knee = (left_knee + right_knee) / 2

        # Trunk angle: shoulder over hip (vertical alignment with wall)
        left_trunk = analyzer.calculate_angle(ls, lh, lk)
        right_trunk = analyzer.calculate_angle(rs, rh, rk)
        avg_trunk = (left_trunk + right_trunk) / 2

        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'avg_trunk': avg_trunk,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        """Target: knees at 90°, trunk upright (hip stacked under shoulder)."""
        return {
            'setup':    {'avg_knee': 130, 'tolerance': 20},
            'holding':  {'avg_knee': 90,  'tolerance': 12},
            'complete': {'avg_knee': 90,  'tolerance': 12},
        }

    def validate_form(self, angles, phase):
        """Check knee angle and trunk alignment during hold."""
        feedback = {}
        knee = angles.get('avg_knee', 90)
        trunk = angles.get('avg_trunk', 90)

        if phase == 'holding':
            if knee > 110:
                feedback['knee'] = JointFeedback(
                    joint='knee', status=FormStatus.WARNING,
                    message="Slide down — thighs should be parallel to floor"
                )
            elif knee < 70:
                feedback['knee'] = JointFeedback(
                    joint='knee', status=FormStatus.WARNING,
                    message="Slide up slightly — knees past 90°"
                )
            if trunk < 70:
                feedback['trunk'] = JointFeedback(
                    joint='trunk', status=FormStatus.WARNING,
                    message="Press back flat against wall"
                )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        """Track hold duration, announce milestones, detect completion."""
        rep_done = False
        warnings = []
        avg_knee = angle if isinstance(angle, (int, float)) else angle.get('avg_knee', 180)

        if self.phase == "setup" and avg_knee < 110:
            self.phase = "holding"
            self.hold_start_time = time.time()
            voice.say("Hold position")

        elif self.phase == "holding":
            if self.hold_start_time:
                self.elapsed_hold = time.time() - self.hold_start_time

                # Announce every 5-second milestone
                milestone = int(self.elapsed_hold // 5) * 5
                if milestone > self._last_milestone and milestone > 0:
                    self._last_milestone = milestone
                    remaining = max(0, self.target_duration - self.elapsed_hold)
                    voice.say(f"{int(remaining)} seconds remaining")

                if self.elapsed_hold >= self.target_duration:
                    self.phase = "complete"
                    self.hold_completed = True
                    rep_done = True
                    voice.say("Hold complete. Well done!")

            # If patient stands up early
            if avg_knee > 150:
                self.phase = "setup"
                self.hold_start_time = None
                self.elapsed_hold = 0.0
                self._last_milestone = 0
                voice.say("Slide back down to hold position")

        if self.phase != self.last_phase:
            self.last_phase = self.phase

        return rep_done, self.phase, warnings

    def calculate_real_time_form_score(self, angles, joints_coords):
        self.stability_detector.update(joints_coords)
        target_angles = self.get_target_poses()[self.phase]
        stability_data = self.stability_detector.get_stability_data()
        tempo_data = self.tempo_detector.check_tempo()
        form_score = FormCalculator.calculate_form_score(
            angles=angles, target_angles=target_angles,
            stability=stability_data, tempo=tempo_data
        )
        self.current_rep_form_scores.append(form_score)
        return form_score

    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        elapsed = round(self.elapsed_hold, 1)
        remaining = max(0.0, self.target_duration - elapsed)
        frame = self.ar.draw_counted_mode(frame, joints_coords, form_score,
                                          timer_remaining=remaining)
        return frame

    def get_summary(self):
        avg_form = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        return {
            'hold_completed': self.hold_completed,
            'elapsed_hold': round(self.elapsed_hold, 1),
            'target_duration': self.target_duration,
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores,
        }
