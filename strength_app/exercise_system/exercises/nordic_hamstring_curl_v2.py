"""
Nordic Hamstring Curl V2 - Eccentric hamstring loading for ACL prevention

NEW EXERCISE - Created for VYAYAM V1
*** CRITICAL ACL PREVENTION EXERCISE ***
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class NordicHamstringCurlV2:
    """Nordic Hamstring Curl - Kneeling eccentric fall controlled by hamstrings.

    *** CRITICAL ACL PREVENTION EXERCISE — Priority in VYAYAM V1 ***

    Level: intermediate
    Category: strength (eccentric)
    Movement Pattern: hinge
    Target: hamstrings (eccentric), gluteus maximus

    Biomechanics:
    - Patient kneels, feet anchored; body falls forward under hamstring control
    - Body must remain straight from knees to head (no hip break)
    - SLOWER fall = better form (hamstrings working harder)
    - Hands catch at bottom; push back to start counts as the return phase
    - Eccentric hamstring strength is the primary ACL injury prevention mechanism

    Key Landmarks (MediaPipe):
    - LEFT_HIP (23), RIGHT_HIP (24)
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    - LEFT_ANKLE (27), RIGHT_ANKLE (28)
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    """

    REFERENCE_VIDEO_URL = ""
    SLOW_FALL_THRESHOLD_SECONDS = 2.0  # Minimum duration for a quality eccentric fall

    def __init__(self, target_reps=6):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "kneeling"   # kneeling → falling → caught → returning
        self.last_phase = "kneeling"
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        self.form_scores = []
        self.current_rep_form_scores = []
        self.fall_start_time = None
        self.fall_duration = 0.0
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

        # Body straightness: shoulder-hip-knee should be ~180° (straight line kneeling)
        left_body = analyzer.calculate_angle(ls, lh, lk)
        right_body = analyzer.calculate_angle(rs, rh, rk)
        avg_body = (left_body + right_body) / 2

        # Torso forward angle: tracked via shoulder y-position vs hip y-position
        # As body falls forward, shoulders drop below knees
        shoulder_mid_y = (ls[1] + rs[1]) / 2
        hip_mid_y = (lh[1] + rh[1]) / 2
        knee_mid_y = (lk[1] + rk[1]) / 2
        # Normalized fall: 0 = upright kneeling, 1 = fully fallen
        fall_progress = max(0.0, min(1.0, (shoulder_mid_y - hip_mid_y) /
                                    max(1, knee_mid_y - hip_mid_y)))

        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'avg_body': avg_body,
            'fall_progress': fall_progress,
            'fall_duration': self.fall_duration,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }

    def get_target_poses(self):
        return {
            'kneeling':  {'avg_body': 175, 'tolerance': 10},
            'falling':   {'avg_body': 175, 'tolerance': 15},  # body must stay straight
            'caught':    {'avg_body': 170, 'tolerance': 20},
            'returning': {'avg_body': 175, 'tolerance': 15},
        }

    def validate_form(self, angles, phase):
        """Check body straight (no hip pike) and fall speed."""
        feedback = {}
        body = angles.get('avg_body', 175)
        fall_dur = angles.get('fall_duration', 0)

        if phase == 'falling':
            if body < 155:
                feedback['hip_pike'] = JointFeedback(
                    joint='hip', status=FormStatus.WARNING,
                    message="Keep body straight — don't pike at hips"
                )
            if fall_dur > 0.5 and fall_dur < self.SLOW_FALL_THRESHOLD_SECONDS:
                feedback['tempo'] = JointFeedback(
                    joint='tempo', status=FormStatus.INFO,
                    message="Fall slower — control with your hamstrings"
                )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        angles_dict = angle if isinstance(angle, dict) else {}
        fall_progress = angles_dict.get('fall_progress', 0.0)

        if self.phase == "kneeling" and fall_progress > 0.15:
            self.phase = "falling"
            self.fall_start_time = time.time()
            self.fall_duration = 0.0
            self.tempo_detector.start_phase('falling')

        elif self.phase == "falling":
            if self.fall_start_time:
                self.fall_duration = time.time() - self.fall_start_time
            if fall_progress > 0.8:
                self.phase = "caught"

        elif self.phase == "caught" and fall_progress < 0.7:
            self.phase = "returning"
            self.tempo_detector.start_phase('returning')

        elif self.phase == "returning" and fall_progress < 0.1:
            rep_done = True
            self.phase = "kneeling"
            form_score = self._calculate_rep_form_score()
            # Penalise fast falls
            if self.fall_duration < self.SLOW_FALL_THRESHOLD_SECONDS:
                form_score = max(50, form_score - 20)
                voice.say("Control the fall — use your hamstrings")
            self._handle_rep_completion(form_score, voice)
            self.fall_start_time = None
            self.fall_duration = 0.0

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
