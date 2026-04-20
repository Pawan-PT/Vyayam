"""
Muscle-Up Progression - Pull-up transitioning through bar to dip position

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class MuscleUpProgressionV2:
    """Muscle-Up Progression.

    Level: advanced (L5)
    Category: strength
    Movement Pattern: pull
    Target: latissimus dorsi, pectorals, triceps, transition strength

    Three phases: pull, transition (false grip), press-out. Track bar transition.
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=4):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "hanging"
        self.last_phase = "hanging"
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

        left_elbow = analyzer.smooth_angle(analyzer.calculate_angle(ls, le, lw), 'left')
        right_elbow = analyzer.smooth_angle(analyzer.calculate_angle(rs, re, rw), 'right')
        avg_elbow = (left_elbow + right_elbow) / 2

        return {
            'avg_elbow': avg_elbow,
            'joints_coords': {'ls': ls, 'rs': rs, 'le': le, 're': re,
                               'lw': lw, 'rw': rw, 'lh': lh, 'rh': rh}
        }

    def get_target_poses(self):
        return {
            'hanging': {'avg_elbow': 170, 'tolerance': 15},
            'pulling': {'avg_elbow': 100, 'tolerance': 20},
            'top':     {'avg_elbow': 20,  'tolerance': 15},
            'lowering':{'avg_elbow': 100, 'tolerance': 20},
        }

    def validate_form(self, angles, phase):
        feedback = {}
        targets = self.get_target_poses().get(phase, {})
        tolerance = targets.get('tolerance', 20)
        for angle_key in ('avg_knee', 'avg_hip', 'avg_elbow'):
            target_val = targets.get(angle_key)
            if target_val is None or angle_key not in angles:
                continue
            diff = abs(angles[angle_key] - target_val)
            if diff <= tolerance:
                status, msg = FormStatus.CORRECT, 'Good position'
            elif diff <= tolerance * 1.5:
                status, msg = FormStatus.NEEDS_ADJUSTMENT, 'Adjust position'
            else:
                status, msg = FormStatus.INCORRECT, 'Check alignment'
            feedback[angle_key] = JointFeedback(
                status=status,
                angle=angles[angle_key],
                message=msg,
            )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        avg_elbow = angle if isinstance(angle, (int, float)) else angle.get('avg_elbow', 170)

        if self.phase == "hanging" and avg_elbow < 140:
            self.phase = "pulling"
            self.tempo_detector.start_phase('pulling')
        elif self.phase == "pulling" and avg_elbow < 35:
            self.phase = "top"
        elif self.phase == "top" and avg_elbow > 40:
            self.phase = "lowering"
            self.tempo_detector.start_phase('lowering')
        elif self.phase == "lowering" and avg_elbow >= 158:
            rep_done = True
            self.phase = "hanging"
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
