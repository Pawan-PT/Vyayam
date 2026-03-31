"""
Plyometric Lunge V2 - Jump lunge with mid-air leg switch

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class PlyometricLungeV2:
    """Plyometric Lunge - Explosive jump from lunge position; switch legs in mid-air.

    Level: advanced
    Category: strength (power)
    Movement Pattern: lunge
    Target: quadriceps, glutes, hamstrings, reactive neuromuscular system

    Biomechanics:
    - Start in lunge position; explode upward with both legs driving off the floor
    - Switch leg positions in mid-air; land softly in the opposite lunge
    - Landing mechanics are critical: soft knee, no valgus, controlled deceleration
    - Each successful jump-switch-land counts as one rep

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
        self.phase = "lunge_down"   # lunge_down → airborne → landing → lunge_down
        self.last_phase = "lunge_down"
        self.probation_mode = True
        self.practice_reps_needed = 4
        self.practice_reps_completed = 0
        self.form_scores = []
        self.current_rep_form_scores = []
        self.stability_detector = StabilityDetector()
        self.tempo_detector = TempoDetector()
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()

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
        avg_knee = (left_knee + right_knee) / 2
        min_knee = min(left_knee, right_knee)

        # Hip height tracks jump: high hips = airborne
        hip_mid_y = (lh[1] + rh[1]) / 2
        ankle_mid_y = (la[1] + ra[1]) / 2
        # Relative hip height: lower value = higher off ground (y is inverted in image coords)
        hip_height_ratio = hip_mid_y / max(1, ankle_mid_y)

        # Knee valgus proxy: left knee x vs left hip x, right knee x vs right hip x
        left_valgus = lk[0] - lh[0]   # negative = valgus
        right_valgus = rh[0] - rk[0]  # negative = valgus

        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'min_knee': min_knee,
            'hip_height_ratio': hip_height_ratio,
            'left_valgus': left_valgus,
            'right_valgus': right_valgus,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        return {
            'lunge_down': {'min_knee': 90,  'tolerance': 15},
            'airborne':   {'avg_knee': 140, 'tolerance': 25},
            'landing':    {'min_knee': 100, 'tolerance': 20},
        }

    def validate_form(self, angles, phase):
        """Prioritise landing valgus detection."""
        feedback = {}
        left_valgus = angles.get('left_valgus', 10)
        right_valgus = angles.get('right_valgus', 10)

        if phase == 'landing':
            if left_valgus < -15 or right_valgus < -15:
                feedback['valgus'] = JointFeedback(
                    joint='knee', status=FormStatus.WARNING,
                    message="Knee caving on landing — land with knees over toes"
                )
            min_knee = angles.get('min_knee', 100)
            if min_knee > 145:
                feedback['soft_landing'] = JointFeedback(
                    joint='knee', status=FormStatus.WARNING,
                    message="Bend knees on landing — absorb the impact"
                )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        angles_dict = angle if isinstance(angle, dict) else {}
        min_knee = angles_dict.get('min_knee', 170)
        hip_ratio = angles_dict.get('hip_height_ratio', 0.6)

        if self.phase == "lunge_down" and min_knee < 105:
            # Well into the lunge — ready to detect jump
            pass
        if self.phase == "lunge_down" and hip_ratio < 0.45:
            # Hips rose quickly = jump initiated
            self.phase = "airborne"
            self.tempo_detector.start_phase('airborne')
        elif self.phase == "airborne" and hip_ratio > 0.5 and min_knee < 130:
            # Hips dropped back = landing
            self.phase = "landing"
            self.tempo_detector.start_phase('landing')
        elif self.phase == "landing" and min_knee < 110:
            # Absorbed landing — rep complete
            rep_done = True
            self.phase = "lunge_down"
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
            if form_score >= 82:
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
