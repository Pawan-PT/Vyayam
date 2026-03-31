"""
Knee Push-Up - Floor push-up from kneeling position

NEW EXERCISE - Created for VYAYAM V1
"""
import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class KneePushUpV2:
    """Knee Push-Up - Level: building | Push pattern

    Biomechanics:
    - Knees on floor, straight line from knees to shoulders
    - Elbow angle to ~90° at bottom (chest near floor)
    - Hip-shoulder alignment must remain neutral
    - Stepping stone to full floor push-up

    Key Landmarks (MediaPipe):
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    - LEFT_ELBOW (13), RIGHT_ELBOW (14)
    - LEFT_WRIST (15), RIGHT_WRIST (16)
    - LEFT_HIP (23), LEFT_KNEE (25)
    """


    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "start"
        self.last_phase = "start"
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
        """Elbow angle + trunk alignment (knees-to-shoulders line)."""
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        le = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ELBOW, shape)
        lw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_WRIST, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        re = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ELBOW, shape)
        rw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_WRIST, shape)
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)

        left_elbow  = analyzer.smooth_angle(analyzer.calculate_angle(ls, le, lw), 'left_elbow')
        right_elbow = analyzer.smooth_angle(analyzer.calculate_angle(rs, re, rw), 'right_elbow')
        avg_elbow   = (left_elbow + right_elbow) / 2
        trunk_angle = analyzer.calculate_angle(lk, lh, ls)   # knees→hips→shoulders

        return {
            'left_elbow': left_elbow, 'right_elbow': right_elbow,
            'avg_elbow': avg_elbow, 'trunk_angle': trunk_angle,
            'joints_coords': {'ls': ls, 'le': le, 'lw': lw,
                              'rs': rs, 're': re, 'rw': rw, 'lh': lh, 'lk': lk},
        }

    def get_target_poses(self):
        return {
            'start':  {'avg_elbow': 170, 'trunk_angle': 175, 'tolerance': 10},
            'down':   {'avg_elbow': 90,  'trunk_angle': 175, 'tolerance': 15},
            'up':     {'avg_elbow': 170, 'trunk_angle': 175, 'tolerance': 10},
        }

    def validate_form(self, angles, phase):
        feedback = {}
        ta = angles.get('trunk_angle', 180)
        ea = angles.get('avg_elbow', 180)
        if ta < 160:
            feedback['trunk'] = JointFeedback('hip', FormStatus.WARNING,
                'Keep straight line from knees to shoulders')
        if phase == 'down' and ea < 70:
            feedback['depth'] = JointFeedback('elbow', FormStatus.GOOD,
                'Chest to floor — excellent depth')
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        avg_elbow = angle.get('avg_elbow', 180) if isinstance(angle, dict) else angle

        if self.phase == 'start' and avg_elbow < 150:
            self.phase = 'down'
            self.tempo_detector.start_phase('down')
        elif self.phase == 'down' and avg_elbow < 100:
            self.phase = 'bottom'
        elif self.phase == 'bottom' and avg_elbow > 110:
            self.phase = 'up'
            self.tempo_detector.start_phase('up')
        elif self.phase == 'up' and avg_elbow >= 160:
            rep_done = True
            self.phase = 'start'
            self._handle_rep_completion(self._calculate_rep_form_score(), voice)

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
                voice.announce_practice_rep(self.practice_reps_completed, self.practice_reps_needed, form_score)
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

    def get_session_summary(self):
        avg_form = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        return {
            'rep_count': self.rep_count,
            'rejected_count': self.rejected_count,
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps,
        }
