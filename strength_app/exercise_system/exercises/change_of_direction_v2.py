"""
Change of Direction V2 - Sprint-decelerate-cut sport-specific drill

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class ChangeOfDirectionV2:
    """Change of Direction - Sprint short distance, decelerate, cut 45°/90°.

    Level: advanced
    Category: strength (power / sport-specific)
    Movement Pattern: lunge
    Target: quadriceps, glutes, hamstrings, lateral hip stabilisers, reactive control

    Biomechanics:
    - Sprint forward 3–5 steps, plant outside foot, cut 45° or 90°
    - Plant leg must accept full deceleration load — knee tracks over toes
    - Lower centre of gravity (hip drop) before the cut reduces knee stress
    - Trunk leans slightly toward direction of cut
    - Drive explosively off the plant foot after the cut

    Key Landmarks (MediaPipe):
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    - LEFT_ANKLE (27), RIGHT_ANKLE (28)
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    """

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=8):
        self.target_reps = target_reps  # total cuts (alternating sides)
        self.rep_count = 0
        self.rejected_count = 0
        self.active_side = 'left'    # plant/cut leg
        self.phase = "sprinting"     # sprinting → decelerating → cutting → driving
        self.last_phase = "sprinting"
        self.probation_mode = True
        self.practice_reps_needed = 4
        self.practice_reps_completed = 0
        self.form_scores = []
        self.current_rep_form_scores = []
        self._prev_hip_mid_x = None
        self._prev_hip_mid_y = None
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
        min_knee = min(left_knee, right_knee)

        # Plant leg knee
        plant_knee = left_knee if self.active_side == 'left' else right_knee

        # Valgus on plant leg
        if self.active_side == 'left':
            valgus_offset = lk[0] - lh[0]
        else:
            valgus_offset = rh[0] - rk[0]

        # Hip centre for motion tracking
        hip_mid_x = (lh[0] + rh[0]) / 2
        hip_mid_y = (lh[1] + rh[1]) / 2
        ankle_mid_y = (la[1] + ra[1]) / 2
        hip_height_ratio = hip_mid_y / max(1, ankle_mid_y)

        # Hip velocity (lateral + vertical)
        if self._prev_hip_mid_x is not None:
            hip_lateral_vel = abs(hip_mid_x - self._prev_hip_mid_x)
            hip_vertical_vel = abs(hip_mid_y - self._prev_hip_mid_y)
        else:
            hip_lateral_vel = 0.0
            hip_vertical_vel = 0.0

        self._prev_hip_mid_x = hip_mid_x
        self._prev_hip_mid_y = hip_mid_y

        # Hip drop: lower hips = better cut mechanics
        left_hip_angle = analyzer.calculate_angle(ls, lh, lk)
        right_hip_angle = analyzer.calculate_angle(rs, rh, rk)
        avg_hip = (left_hip_angle + right_hip_angle) / 2

        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'min_knee': min_knee,
            'plant_knee': plant_knee,
            'valgus_offset': valgus_offset,
            'hip_height_ratio': hip_height_ratio,
            'hip_lateral_vel': hip_lateral_vel,
            'hip_vertical_vel': hip_vertical_vel,
            'avg_hip': avg_hip,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        return {
            'sprinting':     {'avg_knee': 150, 'tolerance': 25},
            'decelerating':  {'plant_knee': 130, 'tolerance': 20},
            'cutting':       {'plant_knee': 110, 'tolerance': 20},
            'driving':       {'avg_knee': 145, 'tolerance': 20},
        }

    def validate_form(self, angles, phase):
        """Check knee valgus on plant foot and hip drop before the cut."""
        feedback = {}
        valgus = angles.get('valgus_offset', 10)
        hip_ratio = angles.get('hip_height_ratio', 0.6)
        plant_knee = angles.get('plant_knee', 170)

        if phase in ('decelerating', 'cutting'):
            if valgus < -15:
                feedback['valgus'] = JointFeedback(
                    joint='knee', status=FormStatus.WARNING,
                    message="Plant knee caving — drive it out over your toes"
                )
            if hip_ratio < 0.52 and phase == 'decelerating':
                feedback['hip_drop'] = JointFeedback(
                    joint='hip', status=FormStatus.INFO,
                    message="Good — drop hips before the cut"
                )
            if hip_ratio > 0.62 and phase == 'cutting':
                feedback['upright'] = JointFeedback(
                    joint='hip', status=FormStatus.WARNING,
                    message="Lower your hips — sit into the cut"
                )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        """Detect sprint → decel → cut → drive cycle via knee flexion and hip velocity."""
        rep_done = False
        warnings = []
        angles_dict = angle if isinstance(angle, dict) else {}
        plant_knee = angles_dict.get('plant_knee', 170)
        avg_knee = angles_dict.get('avg_knee', 170)
        hip_lat_vel = angles_dict.get('hip_lateral_vel', 0)

        if self.phase == "sprinting" and plant_knee < 145:
            self.phase = "decelerating"
            self.tempo_detector.start_phase('decelerating')

        elif self.phase == "decelerating" and plant_knee < 120:
            self.phase = "cutting"
            self.tempo_detector.start_phase('cutting')

        elif self.phase == "cutting" and hip_lat_vel > 8:
            # Lateral velocity spike = driving off the cut
            self.phase = "driving"
            self.tempo_detector.start_phase('driving')

        elif self.phase == "driving" and avg_knee > 155:
            rep_done = True
            self.phase = "sprinting"
            self.active_side = 'right' if self.active_side == 'left' else 'left'
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
            if form_score >= 80:
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
            'rep_count': self.rep_count,
            'rejected_count': self.rejected_count,
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps,
        }
