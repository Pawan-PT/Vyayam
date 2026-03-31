"""
Single Leg Landing V2 - Jump and stick a single-leg landing

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class SingleLegLandingV2:
    """Single Leg Landing - Jump from two feet and land on one leg; hold 3 seconds.

    Level: advanced
    Category: strength (power / neuromuscular control)
    Movement Pattern: lunge
    Target: quadriceps, glutes, ankle stabilisers, neuromuscular control

    Biomechanics:
    - Jump forward or vertically from both feet
    - Land on a single leg with soft knee (~30–40° flexion)
    - Hold the landing for 3 seconds — no additional hops or adjustments
    - Key ACL injury prevention drill: trains deceleration on one leg
    - No excessive knee valgus on landing
    - Alternate landing leg each rep

    Key Landmarks (MediaPipe):
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    - LEFT_ANKLE (27), RIGHT_ANKLE (28)
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    """

    REFERENCE_VIDEO_URL = ""
    HOLD_DURATION = 3.0  # seconds

    def __init__(self, target_reps=8):
        self.target_reps = target_reps  # per side
        self.rep_count_left = 0
        self.rep_count_right = 0
        self.rejected_count = 0
        self.active_side = 'left'   # landing leg
        self.phase = "ready"        # ready → airborne → landing → holding → complete
        self.last_phase = "ready"
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

        landing_knee = left_knee if self.active_side == 'left' else right_knee

        # Valgus proxy on landing leg
        if self.active_side == 'left':
            valgus_offset = lk[0] - lh[0]
        else:
            valgus_offset = rh[0] - rk[0]

        # Hip height ratio for detecting airborne
        hip_mid_y = (lh[1] + rh[1]) / 2
        ankle_mid_y = (la[1] + ra[1]) / 2
        hip_height_ratio = hip_mid_y / max(1, ankle_mid_y)

        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'landing_knee': landing_knee,
            'valgus_offset': valgus_offset,
            'hip_height_ratio': hip_height_ratio,
            'hold_elapsed': self.hold_elapsed,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        return {
            'ready':    {'landing_knee': 170, 'tolerance': 15},
            'airborne': {'avg_knee': 140,     'tolerance': 25},
            'landing':  {'landing_knee': 140, 'tolerance': 20},
            'holding':  {'landing_knee': 140, 'tolerance': 20},
        }

    def validate_form(self, angles, phase):
        feedback = {}
        valgus = angles.get('valgus_offset', 10)
        landing_knee = angles.get('landing_knee', 170)
        hold_elapsed = angles.get('hold_elapsed', 0)

        if phase in ('landing', 'holding'):
            if valgus < -15:
                feedback['valgus'] = JointFeedback(
                    joint='knee', status=FormStatus.WARNING,
                    message="Knee caving — push knee out over toes"
                )
            if landing_knee > 155:
                feedback['soft_land'] = JointFeedback(
                    joint='knee', status=FormStatus.WARNING,
                    message="Bend the knee more — absorb the landing"
                )
            if phase == 'holding' and hold_elapsed < self.HOLD_DURATION:
                remaining = self.HOLD_DURATION - hold_elapsed
                feedback['hold'] = JointFeedback(
                    joint='hold', status=FormStatus.INFO,
                    message=f"Hold... {remaining:.1f}s"
                )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        angles_dict = angle if isinstance(angle, dict) else {}
        hip_ratio = angles_dict.get('hip_height_ratio', 0.6)
        landing_knee = angles_dict.get('landing_knee', 170)

        if self.phase == "ready" and hip_ratio < 0.42:
            self.phase = "airborne"
            self.tempo_detector.start_phase('airborne')

        elif self.phase == "airborne" and hip_ratio > 0.5 and landing_knee < 155:
            self.phase = "landing"
            self.tempo_detector.start_phase('landing')
            voice.say("Stick it")

        elif self.phase == "landing" and landing_knee < 150:
            self.phase = "holding"
            self.hold_start_time = time.time()
            self.hold_elapsed = 0.0

        elif self.phase == "holding":
            if self.hold_start_time:
                self.hold_elapsed = time.time() - self.hold_start_time
            if self.hold_elapsed >= self.HOLD_DURATION:
                rep_done = True
                self.phase = "ready"
                self.hold_start_time = None
                form_score = self._calculate_rep_form_score()
                self._handle_rep_completion(form_score, voice)
                self.active_side = 'right' if self.active_side == 'left' else 'left'
                self.hold_elapsed = 0.0

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
            if form_score >= 82:
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
