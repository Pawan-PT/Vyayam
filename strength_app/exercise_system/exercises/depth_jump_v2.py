"""
DepthJump V2 - Step-off box, land, and immediately jump — reactive power

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class DepthJumpV2:
    """DepthJump — Step-off box, land, and immediately jump — reactive power

    Level: L5 elite
    Category: power
    Movement Pattern: squat-power
    Target: Quads, glutes, calves, reactive neuromuscular system

    Biomechanics:
    - Step (not jump) off box; on landing immediately explode upward
    - Ground contact time should be minimal — reactive, not deliberate
    - Landing mechanics: soft knees, hip-width stance, no valgus

    Key Landmarks (MediaPipe):
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    - LEFT_ANKLE (27), RIGHT_ANKLE (28)
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "ready"
        self.last_phase = "ready"
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
        right_knee_land = analyzer.calculate_angle(rh, rk, ra)
        valgus_l = abs(lk[0] - la[0]) / (abs(lk[1] - la[1]) + 1) if lk and la else 0
        valgus_r = abs(rk[0] - ra[0]) / (abs(rk[1] - ra[1]) + 1) if rk and ra else 0
        hip_height_ratio = ((lh[1] + rh[1]) / 2) / shape[0] if lh and rh else 0.5
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'left_knee_land': left_knee_land,
            'right_knee_land': right_knee_land,
            'valgus_l': valgus_l,
            'valgus_r': valgus_r,
            'hip_height_ratio': hip_height_ratio,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        """Define target angles for each phase."""
        return {
            'ready': {'avg_knee': 175, 'tolerance': 10},
            'landing': {'avg_knee': 130, 'tolerance': 20},
            'loaded': {'avg_knee': 100, 'tolerance': 20},
            'jumping': {'avg_knee': 170, 'tolerance': 10},
        }

    def validate_form(self, angles, phase):
        """Check form against exercise-specific standards."""
        feedback = {}
        vl = angles.get('valgus_l', 0)
        vr = angles.get('valgus_r', 0)
        if max(vl, vr) > 0.4:
            feedback['valgus'] = {'status': 'error', 'message': 'Knee caving — push knees out on landing'}
        lk_land = angles.get('left_knee_land', 175)
        if lk_land < 70 and phase == 'loaded':
            feedback['depth'] = {'status': 'warning', 'message': 'React quickly — minimize time on ground'}
        return feedback

    def update_rep_counter(self, angles, feedback, voice):
        """Detect rep completion through phase transitions."""
        rep_done = False
        warnings = []
        knee = angles.get('avg_knee', 175)
        hip_h = angles.get('hip_height_ratio', 0.3)

        if self.phase == "ready" and knee < 155:
            self.phase = "landing"
        elif self.phase == "landing" and knee < 120:
            self.phase = "loaded"
            self.tempo_detector.start_phase('loaded')
        elif self.phase == "loaded" and knee > 155:
            self.phase = "jumping"
        elif self.phase == "jumping" and knee > 170 and hip_h < 0.4:
            rep_done = True
            self.phase = "ready"
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
