"""
Goblet Squat V2 - Counterbalance squat with weight at chest

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class GobletSquatV2:
    """Goblet Squat - Upright squat with weight held at chest as counterbalance.

    Level: building
    Category: strength
    Movement Pattern: squat
    Target: quadriceps, glutes, core, upper back

    Biomechanics:
    - Weight at chest encourages upright torso (shoulder over hip)
    - Elbows drive inside knees at bottom to open hips
    - Heels stay flat, neutral spine throughout
    - Deeper depth expected compared to bodyweight squat

    Key Landmarks (MediaPipe):
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    - LEFT_ANKLE (27), RIGHT_ANKLE (28)
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "standing"
        self.last_phase = "standing"
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        self.form_scores = []
        self.current_rep_form_scores = []
        self.stability_detector = StabilityDetector()
        self.tempo_detector = TempoDetector()
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()

    def calculate_angles(self, analyzer, results, shape):
        """Extract joint positions; calculate knee and torso upright angles."""
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

        # Torso upright: shoulder-hip-knee angle; higher = more upright
        left_torso = analyzer.calculate_angle(ls, lh, lk)
        right_torso = analyzer.calculate_angle(rs, rh, rk)
        avg_torso = (left_torso + right_torso) / 2

        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'avg_torso': avg_torso,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        """Deeper bottom position (85°) expected due to counterbalance."""
        return {
            'standing':   {'avg_knee': 175, 'tolerance': 10},
            'descending': {'avg_knee': 130, 'tolerance': 15},
            'bottom':     {'avg_knee': 85,  'tolerance': 12},
            'ascending':  {'avg_knee': 130, 'tolerance': 15},
        }

    def validate_form(self, angles, phase):
        """Check depth and upright torso."""
        feedback = {}
        knee = angles.get('avg_knee', 175)
        torso = angles.get('avg_torso', 90)

        if phase == 'bottom':
            if knee > 100:
                feedback['depth'] = JointFeedback(
                    joint='knee', status=FormStatus.WARNING,
                    message="Go deeper — aim for thighs parallel or below"
                )
            if torso < 65:
                feedback['torso'] = JointFeedback(
                    joint='torso', status=FormStatus.WARNING,
                    message="Stay upright — chest up, weight at sternum"
                )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        avg_knee = angle if isinstance(angle, (int, float)) else angle.get('avg_knee', 180)

        if self.phase == "standing" and avg_knee < 150:
            self.phase = "descending"
            self.tempo_detector.start_phase('descending')
        elif self.phase == "descending" and avg_knee < 100:
            self.phase = "bottom"
        elif self.phase == "bottom" and avg_knee > 105:
            self.phase = "ascending"
            self.tempo_detector.start_phase('ascending')
        elif self.phase == "ascending" and avg_knee >= 165:
            rep_done = True
            self.phase = "standing"
            form_score = self._calculate_rep_form_score()
            self._handle_rep_completion(form_score, voice)

        if self.phase != self.last_phase:
            self.last_phase = self.phase

        return rep_done, self.phase, warnings

    def _calculate_rep_form_score(self):
        if self.current_rep_form_scores:
            avg = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg
        return 85.0

    def _handle_rep_completion(self, form_score, voice):
        if self.probation_mode:
            if form_score >= 85:
                self.practice_reps_completed += 1
                voice.announce_practice_rep(self.practice_reps_completed,
                                            self.practice_reps_needed, form_score)
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
            angles=angles, target_angles=target_angles,
            stability=stability_data, tempo=tempo_data
        )
        self.current_rep_form_scores.append(form_score)
        return form_score

    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        if self.probation_mode:
            frame, _ = self.ar.draw_practice_mode(frame, joints_coords, angles,
                                                   self.get_target_poses()[self.phase], form_score)
        else:
            frame = self.ar.draw_counted_mode(frame, joints_coords, form_score)
        return frame

    def get_summary(self):
        avg_form = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        return {
            'rep_count': self.rep_count,
            'rejected_count': self.rejected_count,
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps,
        }
