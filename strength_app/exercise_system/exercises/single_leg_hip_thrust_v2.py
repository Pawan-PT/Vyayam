"""
Single Leg Hip Thrust V2 - Unilateral hip extension with one leg extended

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class SingleLegHipThrustV2:
    """Single Leg Hip Thrust - Hip thrust on one leg; other leg extended.

    Level: advanced
    Category: strength
    Movement Pattern: hinge (unilateral)
    Target: gluteus maximus (unilateral), hip stabilizers, core

    Biomechanics:
    - Identical setup to bilateral hip thrust but one leg extended out
    - Extended leg must stay level — no hip drop on unsupported side
    - Full hip extension of planted side; 2-second hold at top
    - Alternates sides each set

    Key Landmarks (MediaPipe):
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    - LEFT_ANKLE (27), RIGHT_ANKLE (28)
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    """

    REFERENCE_VIDEO_URL = ""
    HOLD_DURATION = 2.0

    def __init__(self, target_reps=10):
        self.target_reps = target_reps  # per side
        self.rep_count_left = 0
        self.rep_count_right = 0
        self.rejected_count = 0
        self.active_side = 'left'  # planted leg
        self.phase = "lowered"
        self.last_phase = "lowered"
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        self.form_scores = []
        self.current_rep_form_scores = []
        self.hold_start_time = None
        self.hold_elapsed = 0.0
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

        left_hip_ext = analyzer.calculate_angle(ls, lh, lk)
        right_hip_ext = analyzer.calculate_angle(rs, rh, rk)

        # Track pelvis level using hip y-coordinates
        hip_level_diff = abs(lh[1] - rh[1])

        active_hip_ext = left_hip_ext if self.active_side == 'left' else right_hip_ext

        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'left_hip_ext': left_hip_ext,
            'right_hip_ext': right_hip_ext,
            'active_hip_ext': active_hip_ext,
            'hip_level_diff': hip_level_diff,
            'hold_elapsed': self.hold_elapsed,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        return {
            'lowered':  {'active_hip_ext': 70,  'tolerance': 15},
            'rising':   {'active_hip_ext': 120, 'tolerance': 15},
            'holding':  {'active_hip_ext': 175, 'tolerance': 12},
            'lowering': {'active_hip_ext': 120, 'tolerance': 15},
        }

    def validate_form(self, angles, phase):
        feedback = {}
        hip_diff = angles.get('hip_level_diff', 0)
        active_hip = angles.get('active_hip_ext', 90)

        if phase == 'holding':
            if hip_diff > 20:
                feedback['pelvic_drop'] = JointFeedback(
                    joint='hip', status=FormStatus.WARNING,
                    message="Level your hips — don't let the unsupported side drop"
                )
            if active_hip < 160:
                feedback['extension'] = JointFeedback(
                    joint='hip', status=FormStatus.WARNING,
                    message="Drive hips higher — full glute extension"
                )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        angles_dict = angle if isinstance(angle, dict) else {}
        active_hip = angles_dict.get('active_hip_ext', 70)

        if self.phase == "lowered" and active_hip > 100:
            self.phase = "rising"
            self.tempo_detector.start_phase('rising')
        elif self.phase == "rising" and active_hip > 165:
            self.phase = "holding"
            self.hold_start_time = time.time()
            self.hold_elapsed = 0.0
            voice.say("Squeeze and hold")
        elif self.phase == "holding":
            if self.hold_start_time:
                self.hold_elapsed = time.time() - self.hold_start_time
            if self.hold_elapsed >= self.HOLD_DURATION:
                self.phase = "lowering"
                self.tempo_detector.start_phase('lowering')
        elif self.phase == "lowering" and active_hip <= 80:
            rep_done = True
            self.phase = "lowered"
            self.hold_start_time = None
            self.hold_elapsed = 0.0
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
            else:
                self.rep_count_right += 1
            self.form_scores.append(form_score)
            side_count = self.rep_count_left if self.active_side == 'left' else self.rep_count_right
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
