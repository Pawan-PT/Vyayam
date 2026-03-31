"""
CopenhagenWithMovement V2 - Copenhagen plank with dynamic hip adduction movement

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class CopenhagenWithMovementV2:
    """CopenhagenWithMovement — Copenhagen plank with dynamic hip adduction movement

    Level: L4 elite
    Category: core
    Movement Pattern: lateral-flexion
    Target: Hip adductors, obliques, hip abductors, core stabilizers

    Biomechanics:
    - From Copenhagen position, perform controlled hip adduction and abduction
    - Body line stays straight while top leg presses into and away from surface
    - Each rep is a full press-away and return cycle

    Key Landmarks (MediaPipe):
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "neutral"
        self.last_phase = "neutral"
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
        body_line = analyzer.calculate_angle(ls, lh, la)
        hip_ab_angle = analyzer.calculate_angle(ls, lh, rh)
        top_hip_flex = analyzer.calculate_angle(ls, lh, lk)
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'body_line': body_line,
            'hip_ab_angle': hip_ab_angle,
            'top_hip_flex': top_hip_flex,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        """Define target angles for each phase."""
        return {
            'neutral': {'body_line': 175, 'tolerance': 15},
            'adducting': {'hip_ab_angle': 150, 'tolerance': 20},
            'abducting': {'hip_ab_angle': 170, 'tolerance': 15},
        }

    def validate_form(self, angles, phase):
        """Check form against exercise-specific standards."""
        feedback = {}
        body = angles.get('body_line', 175)
        if body < 150:
            feedback['hip_sag'] = {'status': 'error', 'message': 'Maintain hip height during movement'}
        hip_ab = angles.get('hip_ab_angle', 160)
        if hip_ab < 120 and phase == 'adducting':
            feedback['range'] = {'status': 'warning', 'message': 'Full adduction — press into surface more'}
        return feedback

    def update_rep_counter(self, angles, feedback, voice):
        """Detect rep completion through phase transitions."""
        rep_done = False
        warnings = []
        hip_ab = angles.get('hip_ab_angle', 165)

        if self.phase == "neutral" and hip_ab < 155:
            self.phase = "adducting"
            self.tempo_detector.start_phase('adducting')
        elif self.phase == "adducting" and hip_ab < 135:
            self.phase = "abducting"
            self.tempo_detector.start_phase('abducting')
        elif self.phase == "abducting" and hip_ab > 168:
            rep_done = True
            self.phase = "neutral"
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
