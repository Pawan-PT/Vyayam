"""
BirdDog V2 - Quadruped opposite arm-leg extension for spinal stability

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class BirdDogV2:
    """BirdDog — Quadruped opposite arm-leg extension for spinal stability

    Level: L1 foundation
    Category: core
    Movement Pattern: anti-rotation
    Target: Erector spinae, glutes, deltoid, TVA

    Biomechanics:
    - Spine neutral throughout — no sag or rotation at hip or shoulder
    - Extend arm and opposite leg to parallel with floor, not beyond
    - Pause 1-2 seconds at full extension before returning

    Key Landmarks (MediaPipe):
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    - LEFT_ELBOW (13), RIGHT_WRIST (16)
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "quadruped"
        self.last_phase = "quadruped"
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
        rw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_WRIST, shape)
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left_knee')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right_knee')
        avg_knee = (left_knee + right_knee) / 2
        spine_angle = analyzer.calculate_angle(ls, lh, la)
        left_arm_angle = analyzer.calculate_angle(lh, ls, lw)
        right_arm_angle = analyzer.calculate_angle(rh, rs, rw)
        left_hip_ext = analyzer.calculate_angle(ls, lh, lk)
        right_hip_ext = analyzer.calculate_angle(rs, rh, rk)
        shoulder_level_diff = abs(ls[1] - rs[1]) if ls and rs else 0
        hip_level_diff = abs(lh[1] - rh[1]) if lh and rh else 0
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'spine_angle': spine_angle,
            'left_arm_angle': left_arm_angle,
            'right_arm_angle': right_arm_angle,
            'left_hip_ext': left_hip_ext,
            'right_hip_ext': right_hip_ext,
            'shoulder_level_diff': shoulder_level_diff,
            'hip_level_diff': hip_level_diff,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        """Define target angles for each phase."""
        return {
            'quadruped': {'spine_angle': 180, 'tolerance': 15},
            'extending': {'left_hip_ext': 170, 'right_hip_ext': 170, 'tolerance': 15},
            'return': {'spine_angle': 180, 'tolerance': 15},
        }

    def validate_form(self, angles, phase):
        """Check form against exercise-specific standards."""
        feedback = {}
        hip_diff = angles.get('hip_level_diff', 0)
        if hip_diff > 20:
            feedback['hip_rotation'] = {'status': 'error', 'message': 'Keep hips level — no rotation'}
        shoulder_diff = angles.get('shoulder_level_diff', 0)
        if shoulder_diff > 20:
            feedback['shoulder_level'] = {'status': 'warning', 'message': 'Keep shoulders level'}
        spine = angles.get('spine_angle', 180)
        if spine < 160:
            feedback['spine'] = {'status': 'error', 'message': 'Maintain neutral spine — no sag'}
        return feedback

    def update_rep_counter(self, angles, feedback, voice):
        """Detect rep completion through phase transitions."""
        rep_done = False
        warnings = []
        lhe = angles.get('left_hip_ext', 90)
        rhe = angles.get('right_hip_ext', 90)
        avg_ext = (lhe + rhe) / 2

        if self.phase == "quadruped" and avg_ext > 140:
            self.phase = "extending"
            self.tempo_detector.start_phase('extending')
        elif self.phase == "extending" and avg_ext > 165:
            self.phase = "return"
        elif self.phase == "return" and avg_ext < 110:
            rep_done = True
            self.phase = "quadruped"
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
