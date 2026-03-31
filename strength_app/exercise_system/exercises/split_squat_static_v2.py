"""
Split Squat Static V2 - Fixed-foot lunge for unilateral leg strength

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class SplitSquatStaticV2:
    """Split Squat (Static) - Fixed lunge stance, lower and raise without moving feet.

    Level: foundation
    Category: strength
    Movement Pattern: lunge
    Target: quadriceps, glutes, hip flexors (rear leg)

    Biomechanics:
    - Feet remain stationary in split stance throughout the set
    - Front knee tracks over toes — no valgus
    - Back knee hovers ~2 inches from floor at the bottom
    - Torso upright — slight forward lean acceptable

    Key Landmarks (MediaPipe):
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    - LEFT_ANKLE (27), RIGHT_ANKLE (28)
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=10):
        self.target_reps = target_reps  # per side
        self.rep_count_left = 0
        self.rep_count_right = 0
        self.rejected_count = 0
        self.active_side = 'left'  # front leg
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

        # Front knee = active side; back knee tracked separately
        front_knee = left_knee if self.active_side == 'left' else right_knee
        back_knee = right_knee if self.active_side == 'left' else left_knee
        avg_knee = (left_knee + right_knee) / 2

        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'front_knee': front_knee,
            'back_knee': back_knee,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        return {
            'standing':   {'front_knee': 170, 'tolerance': 10},
            'descending': {'front_knee': 120, 'tolerance': 15},
            'bottom':     {'front_knee': 90,  'tolerance': 12},
            'ascending':  {'front_knee': 130, 'tolerance': 15},
        }

    def validate_form(self, angles, phase):
        feedback = {}
        front_knee = angles.get('front_knee', 170)
        back_knee = angles.get('back_knee', 170)

        if phase in ('descending', 'bottom'):
            if front_knee < 75:
                feedback['depth'] = JointFeedback(
                    joint='front_knee', status=FormStatus.WARNING,
                    message="Don't go too deep — front knee past 90° is enough"
                )
            if back_knee > 30:
                feedback['back_knee'] = JointFeedback(
                    joint='back_knee', status=FormStatus.INFO,
                    message="Lower back knee — hover close to the floor"
                )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        angles_dict = angle if isinstance(angle, dict) else {}
        front_knee = angles_dict.get('front_knee', 170)

        if self.phase == "standing" and front_knee < 145:
            self.phase = "descending"
            self.tempo_detector.start_phase('descending')
        elif self.phase == "descending" and front_knee < 100:
            self.phase = "bottom"
        elif self.phase == "bottom" and front_knee > 110:
            self.phase = "ascending"
            self.tempo_detector.start_phase('ascending')
        elif self.phase == "ascending" and front_knee >= 160:
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
            if self.active_side == 'left':
                self.rep_count_left += 1
                side_count = self.rep_count_left
            else:
                self.rep_count_right += 1
                side_count = self.rep_count_right
            self.form_scores.append(form_score)
            voice.announce_rep(side_count, self.target_reps, form_score)

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
            'rep_count_left': self.rep_count_left,
            'rep_count_right': self.rep_count_right,
            'rejected_count': self.rejected_count,
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores,
            'target_reps_per_side': self.target_reps,
        }
