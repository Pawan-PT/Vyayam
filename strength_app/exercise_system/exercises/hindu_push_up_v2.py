"""
Hindu Push Up V2 - Flowing arc movement from pike through dive to cobra

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class HinduPushUpV2:
    """Hindu Push-Up - Flowing movement: downward dog → dive → upward dog → return.

    Level: intermediate (L3)
    Category: strength
    Movement Pattern: push
    Target: anterior deltoid, pectorals, triceps, spine extensors

    Biomechanics:
    - Start in pike/downward dog (hips high, arms and legs straight)
    - Dive chest forward and down in a sweeping arc
    - Finish in upward dog (hips low, chest high, arms extended)
    - Reverse the arc or push back to pike to complete one rep
    - Four distinct phases tracked via hip height ratio

    Key Landmarks (MediaPipe):
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    - LEFT_ELBOW (13), RIGHT_ELBOW (14)
    - LEFT_WRIST (15), RIGHT_WRIST (16)
    - LEFT_HIP (23), RIGHT_HIP (24)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=8):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "pike"       # pike → diving → cobra → returning
        self.last_phase = "pike"
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
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        le = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ELBOW, shape)
        re = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ELBOW, shape)
        lw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_WRIST, shape)
        rw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_WRIST, shape)
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)

        left_elbow = analyzer.smooth_angle(analyzer.calculate_angle(ls, le, lw), 'left')
        right_elbow = analyzer.smooth_angle(analyzer.calculate_angle(rs, re, rw), 'right')
        avg_elbow = (left_elbow + right_elbow) / 2

        # Hip height relative to wrist height — pike = hips high (low y), cobra = hips low (high y)
        hip_mid_y = (lh[1] + rh[1]) / 2
        wrist_mid_y = (lw[1] + rw[1]) / 2
        # Negative = hips above wrists (pike), positive = hips below wrists (cobra)
        hip_wrist_diff = hip_mid_y - wrist_mid_y

        # Spine extension angle (shoulder-hip-knee)
        spine_angle = analyzer.calculate_angle(ls, lh, lk)

        return {
            'avg_elbow': avg_elbow, 'hip_wrist_diff': hip_wrist_diff, 'spine_angle': spine_angle,
            'joints_coords': {'ls': ls, 'rs': rs, 'le': le, 're': re,
                               'lw': lw, 'rw': rw, 'lh': lh, 'rh': rh}
        }

    def get_target_poses(self):
        return {
            'pike':      {'avg_elbow': 165, 'tolerance': 15},
            'diving':    {'avg_elbow': 100, 'tolerance': 20},
            'cobra':     {'avg_elbow': 160, 'tolerance': 15},
            'returning': {'avg_elbow': 130, 'tolerance': 20},
        }

    def validate_form(self, angles, phase):
        feedback = {}
        elbow = angles.get('avg_elbow', 165)
        if phase == 'cobra' and elbow < 130:
            feedback['extension'] = JointFeedback(
                joint='elbow', status=FormStatus.WARNING,
                message="Extend arms fully in cobra position"
            )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        angles_dict = angle if isinstance(angle, dict) else {}
        hip_diff = angles_dict.get('hip_wrist_diff', -30)
        avg_elbow = angles_dict.get('avg_elbow', 165)

        if self.phase == "pike" and hip_diff > -10:
            self.phase = "diving"
            self.tempo_detector.start_phase('diving')
        elif self.phase == "diving" and hip_diff > 15:
            self.phase = "cobra"
        elif self.phase == "cobra" and hip_diff < 5:
            self.phase = "returning"
            self.tempo_detector.start_phase('returning')
        elif self.phase == "returning" and hip_diff < -20:
            rep_done = True
            self.phase = "pike"
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
            stability=stability_data, tempo=tempo_data)
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
        return {'rep_count': self.rep_count, 'rejected_count': self.rejected_count,
                'avg_form_score': round(avg_form, 1), 'form_scores': self.form_scores,
                'target_reps': self.target_reps}
