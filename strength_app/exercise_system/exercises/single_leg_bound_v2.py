"""
SingleLegBound V2 - Single-leg forward bound — unilateral power and landing stability

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class SingleLegBoundV2:
    """SingleLegBound — Single-leg forward bound — unilateral power and landing stability

    Level: L5 elite
    Category: power
    Movement Pattern: lunge-power
    Target: Quads, glutes, calves, single-leg stabilizers

    Biomechanics:
    - Push off one leg, fly forward, land on same leg and stick
    - Landing hip: absorb with a single-leg squat of 90° or less
    - Track distance and landing stability separately

    Key Landmarks (MediaPipe):
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    - LEFT_ANKLE (27), RIGHT_ANKLE (28)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "loaded"
        self.last_phase = "loaded"
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
        left_knee_land = analyzer.calculate_angle(lh, lk, la)
        valgus_l = abs(lk[0] - la[0]) / (abs(lk[1] - la[1]) + 1) if lk and la else 0
        hip_height_ratio = lh[1] / shape[0] if lh else 0.5
        trunk_forward = analyzer.calculate_angle(ls, lh, la)
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'left_knee_land': left_knee_land,
            'valgus_l': valgus_l,
            'hip_height_ratio': hip_height_ratio,
            'trunk_forward': trunk_forward,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        """Define target angles for each phase."""
        return {
            'loaded': {'left_knee_land': 130, 'tolerance': 20},
            'airborne': {'hip_height_ratio': 0.3, 'tolerance': 0.1},
            'landing': {'left_knee_land': 110, 'tolerance': 20},
            'stick': {'left_knee_land': 90, 'tolerance': 15},
        }

    def validate_form(self, angles, phase):
        """Check form against exercise-specific standards."""
        feedback = {}
        valgus = angles.get('valgus_l', 0)
        if valgus > 0.4:
            feedback['valgus'] = {'status': 'error', 'message': 'Knee caving on landing — push knee out'}
        knee = angles.get('left_knee_land', 175)
        if knee > 150 and phase == 'landing':
            feedback['absorption'] = {'status': 'warning', 'message': 'Bend knee to absorb — soft landing'}
        return feedback

    def update_rep_counter(self, angles, feedback, voice):
        """Detect rep completion through phase transitions."""
        rep_done = False
        warnings = []
        knee = angles.get('left_knee_land', 175)
        hip_h = angles.get('hip_height_ratio', 0.5)

        if self.phase == "loaded" and hip_h < 0.35:
            self.phase = "airborne"
        elif self.phase == "airborne" and hip_h > 0.45:
            self.phase = "landing"
        elif self.phase == "landing" and knee < 105:
            self.phase = "stick"
        elif self.phase == "stick" and knee > 155:
            rep_done = True
            self.phase = "loaded"
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
