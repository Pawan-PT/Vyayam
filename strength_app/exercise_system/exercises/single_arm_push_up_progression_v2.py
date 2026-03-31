"""
Single Arm Push Up Progression V2 - Progressive one-arm push-up development

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class SingleArmPushUpProgressionV2:
    """Single Arm Push-Up Progression - Build toward full one-arm push-up.

    Level: advanced (L5)
    Category: strength
    Movement Pattern: push
    Target: pectorals, anterior deltoid, triceps, anti-rotation core

    Biomechanics:
    - Working arm at shoulder width; off-hand on hip or back
    - Key fault: torso rotation (shoulder twist) away from floor
    - Body should stay square throughout — minimal hip rotation
    - Progression: wide-stance feet → narrow feet → elevated hand → floor
    - Alternate sides each set

    Key Landmarks (MediaPipe):
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    - LEFT_ELBOW (13), RIGHT_ELBOW (14)
    - LEFT_WRIST (15), RIGHT_WRIST (16)
    - LEFT_HIP (23), RIGHT_HIP (24)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=5):
        self.target_reps = target_reps  # per side
        self.rep_count_left = 0
        self.rep_count_right = 0
        self.rejected_count = 0
        self.active_side = 'left'
        self.phase = "up"
        self.last_phase = "up"
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

        # Active side elbow angle
        active_e = le if self.active_side == 'left' else re
        active_s = ls if self.active_side == 'left' else rs
        active_w = lw if self.active_side == 'left' else rw
        active_elbow = analyzer.smooth_angle(analyzer.calculate_angle(active_s, active_e, active_w), self.active_side)

        # Torso rotation: shoulder y-level difference
        shoulder_rot = abs(ls[1] - rs[1])
        # Hip rotation: hip y-level difference
        hip_rot = abs(lh[1] - rh[1])

        return {
            'active_elbow': active_elbow, 'shoulder_rot': shoulder_rot, 'hip_rot': hip_rot,
            'joints_coords': {'ls': ls, 'rs': rs, 'le': le, 're': re,
                               'lw': lw, 'rw': rw, 'lh': lh, 'rh': rh}
        }

    def get_target_poses(self):
        return {
            'up':   {'active_elbow': 168, 'tolerance': 12},
            'down': {'active_elbow': 90,  'tolerance': 18},
        }

    def validate_form(self, angles, phase):
        feedback = {}
        shoulder_rot = angles.get('shoulder_rot', 0)
        if shoulder_rot > 25:
            feedback['rotation'] = JointFeedback(
                joint='shoulder', status=FormStatus.WARNING,
                message="Keep shoulders square — resist the rotation"
            )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        angles_dict = angle if isinstance(angle, dict) else {}
        active_elbow = angles_dict.get('active_elbow', 168)

        if self.phase == "up" and active_elbow < 130:
            self.phase = "down"
            self.tempo_detector.start_phase('down')
        elif self.phase == "down" and active_elbow >= 155:
            rep_done = True
            self.phase = "up"
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
        return {'rep_count_left': self.rep_count_left, 'rep_count_right': self.rep_count_right,
                'rejected_count': self.rejected_count, 'avg_form_score': round(avg_form, 1),
                'target_reps_per_side': self.target_reps}
