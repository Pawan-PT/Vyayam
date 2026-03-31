"""
Lateral Bound V2 - Lateral plyometric hop between legs

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class LateralBoundV2:
    """Lateral Bound - Push off one leg sideways and land on the opposite leg.

    Level: advanced
    Category: strength (power / frontal plane)
    Movement Pattern: lunge
    Target: glutes (abductors), quadriceps, ankle stabilisers

    Biomechanics:
    - Stand on one leg; push off powerfully to the side
    - Land on the opposite leg with soft knee
    - Decelerate and stick the landing — each side counts as one rep
    - Tracks lateral distance indirectly via hip displacement between frames
    - Landing mechanics: knee over toes, no valgus, controlled trunk

    Key Landmarks (MediaPipe):
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    - LEFT_ANKLE (27), RIGHT_ANKLE (28)
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=10):
        self.target_reps = target_reps  # total bounds (alternating)
        self.rep_count = 0
        self.rejected_count = 0
        self.active_side = 'left'   # push-off leg
        self.phase = "loaded"       # loaded (single-leg) → airborne → landing → loaded
        self.last_phase = "loaded"
        self.probation_mode = True
        self.practice_reps_needed = 4
        self.practice_reps_completed = 0
        self.form_scores = []
        self.current_rep_form_scores = []
        self._last_hip_x = None
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

        # Landing leg
        landing_knee = right_knee if self.active_side == 'left' else left_knee

        # Valgus on landing leg
        if self.active_side == 'left':
            valgus_offset = rh[0] - rk[0]  # landing on right
        else:
            valgus_offset = lk[0] - lh[0]  # landing on left

        # Hip height ratio for jump detection
        hip_mid_y = (lh[1] + rh[1]) / 2
        ankle_mid_y = (la[1] + ra[1]) / 2
        hip_height_ratio = hip_mid_y / max(1, ankle_mid_y)

        # Hip lateral movement
        hip_mid_x = (lh[0] + rh[0]) / 2

        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'landing_knee': landing_knee,
            'valgus_offset': valgus_offset,
            'hip_height_ratio': hip_height_ratio,
            'hip_mid_x': hip_mid_x,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        return {
            'loaded':   {'avg_knee': 150, 'tolerance': 20},
            'airborne': {'avg_knee': 155, 'tolerance': 25},
            'landing':  {'landing_knee': 140, 'tolerance': 20},
        }

    def validate_form(self, angles, phase):
        feedback = {}
        valgus = angles.get('valgus_offset', 10)
        landing_knee = angles.get('landing_knee', 170)

        if phase == 'landing':
            if valgus < -15:
                feedback['valgus'] = JointFeedback(
                    joint='knee', status=FormStatus.WARNING,
                    message="Knee caving on landing — push knee out"
                )
            if landing_knee > 160:
                feedback['stiff'] = JointFeedback(
                    joint='knee', status=FormStatus.WARNING,
                    message="Bend the landing knee — absorb laterally"
                )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        angles_dict = angle if isinstance(angle, dict) else {}
        hip_ratio = angles_dict.get('hip_height_ratio', 0.6)
        landing_knee = angles_dict.get('landing_knee', 170)
        hip_x = angles_dict.get('hip_mid_x', 0)

        if self._last_hip_x is None:
            self._last_hip_x = hip_x

        hip_x_delta = abs(hip_x - self._last_hip_x)
        self._last_hip_x = hip_x

        if self.phase == "loaded" and hip_ratio < 0.44:
            self.phase = "airborne"
            self.tempo_detector.start_phase('airborne')

        elif self.phase == "airborne" and hip_ratio > 0.52 and landing_knee < 160:
            self.phase = "landing"
            self.tempo_detector.start_phase('landing')

        elif self.phase == "landing" and landing_knee < 150 and hip_x_delta < 5:
            # Stable — landed and stopped
            rep_done = True
            self.phase = "loaded"
            self.active_side = 'right' if self.active_side == 'left' else 'left'
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
