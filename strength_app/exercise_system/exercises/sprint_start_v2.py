"""
SprintStart V2 - Explosive 3-point stance start for 5 metres — athletic acceleration

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class SprintStartV2:
    """SprintStart — Explosive 3-point stance start for 5 metres — athletic acceleration

    Level: L5 elite
    Category: power
    Movement Pattern: sprint-power
    Target: Glutes, hamstrings, quads, calves, hip flexors

    Biomechanics:
    - Start in 3-point stance: lead leg at ~90°, trail leg extended, one hand on ground
    - Explosive drive off both legs; lean forward 45° for first 3 steps
    - Drive knees high, arms pump vigorously — evaluate push-off angle

    Key Landmarks (MediaPipe):
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    - LEFT_ANKLE (27), RIGHT_ANKLE (28)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "set"
        self.last_phase = "set"
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
        
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left_knee')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right_knee')
        avg_knee = (left_knee + right_knee) / 2
        lead_knee = analyzer.calculate_angle(lh, lk, la)
        trail_hip_ext = analyzer.calculate_angle(ls, rh, rk)
        trunk_lean = analyzer.calculate_angle(ls, lh, la)
        pushoff_angle = analyzer.calculate_angle(lh, la, rh)
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'lead_knee': lead_knee,
            'trail_hip_ext': trail_hip_ext,
            'trunk_lean': trunk_lean,
            'pushoff_angle': pushoff_angle,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        """Define target angles for each phase."""
        return {
            'set': {'lead_knee': 90, 'tolerance': 20},
            'exploding': {'trunk_lean': 130, 'tolerance': 20},
            'sprinting': {'avg_knee': 145, 'tolerance': 20},
        }

    def validate_form(self, angles, phase):
        """Check form against exercise-specific standards."""
        feedback = {}
        trunk = angles.get('trunk_lean', 140)
        if trunk > 165 and phase == 'exploding':
            feedback['lean'] = {'status': 'error', 'message': 'Lean forward aggressively on start — push, not stand'}
        push_off = angles.get('pushoff_angle', 120)
        if push_off < 100:
            feedback['pushoff'] = {'status': 'warning', 'message': 'More aggressive hip drive on push-off'}
        return feedback

    def update_rep_counter(self, angles, feedback, voice):
        """Detect rep completion through phase transitions."""
        rep_done = False
        warnings = []
        trunk = angles.get('trunk_lean', 160)
        knee = angles.get('avg_knee', 90)

        if self.phase == "set" and trunk < 150:
            self.phase = "exploding"
            self.tempo_detector.start_phase('exploding')
        elif self.phase == "exploding" and knee > 130:
            self.phase = "sprinting"
        elif self.phase == "sprinting" and knee > 155:
            rep_done = True
            self.phase = "set"
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
