"""
HollowBodyRock V2 - Hollow hold with rhythmic rocking — dynamic core compression

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class HollowBodyRockV2:
    """HollowBodyRock — Hollow hold with rhythmic rocking — dynamic core compression

    Level: L5 elite
    Category: core
    Movement Pattern: anti-extension
    Target: Rectus abdominis, TVA, hip flexors, serratus anterior

    Biomechanics:
    - Establish hollow hold position first, then add gentle fore-aft rocking
    - Rocking amplitude is small — 5-10 cm; body shape must not change
    - Lower back stays in contact with floor throughout

    Key Landmarks (MediaPipe):
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_WRIST (15), RIGHT_WRIST (16)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "hold"
        self.last_phase = "hold"
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
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left_knee')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right_knee')
        avg_knee = (left_knee + right_knee) / 2
        lumbar_contact = analyzer.calculate_angle(ls, lh, lk)
        arm_overhead = analyzer.calculate_angle(lh, ls, lw)
        shoulder_position = ls[1] / shape[0] if ls else 0.5
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'lumbar_contact': lumbar_contact,
            'arm_overhead': arm_overhead,
            'shoulder_position': shoulder_position,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        """Define target angles for each phase."""
        return {
            'hold': {'lumbar_contact': 160, 'tolerance': 15},
            'rocking_f': {'shoulder_position': 0.45, 'tolerance': 0.05},
            'rocking_b': {'shoulder_position': 0.55, 'tolerance': 0.05},
        }

    def validate_form(self, angles, phase):
        """Check form against exercise-specific standards."""
        feedback = {}
        lumbar = angles.get('lumbar_contact', 160)
        if lumbar < 150:
            feedback['lumbar'] = {'status': 'error', 'message': 'Lower back arching — reduce leg height or stop rocking'}
        arm = angles.get('arm_overhead', 90)
        if arm < 140:
            feedback['arms'] = {'status': 'warning', 'message': 'Keep arms reaching overhead while rocking'}
        return feedback

    def update_rep_counter(self, angles, feedback, voice):
        """Detect rep completion through phase transitions."""
        rep_done = False
        warnings = []
        sp = angles.get('shoulder_position', 0.5)

        if self.phase == "hold" and sp < 0.46:
            self.phase = "rocking_f"
        elif self.phase == "rocking_f" and sp > 0.54:
            self.phase = "rocking_b"
        elif self.phase == "rocking_b" and sp < 0.48:
            rep_done = True
            self.phase = "rocking_f"
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
        target_angles = self.get_target_poses().get(self.phase, {})
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
            frame, _ = self.ar.draw_practice_mode(
                frame, joints_coords, angles,
                self.get_target_poses().get(self.phase, {}), form_score
            )
        else:
            frame = self.ar.draw_counted_mode(frame, joints_coords, form_score)
        return frame

    def get_stats(self):
        avg_form = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        return {
            'reps_completed': self.rep_count,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps,
        }
