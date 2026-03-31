"""
Band-Assisted Pull-Up - Resistance band reduces effective bodyweight

NEW EXERCISE - Created for VYAYAM V1
"""
import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class BandAssistedPullUpV2:
    """Band-Assisted Pull-Up - Level: building | Pull pattern (bar track)

    Biomechanics:
    - Loop resistance band around bar; knee in band reduces effective load
    - Full ROM: dead hang → chin over bar
    - Band assistance decreases as you strengthen — progress to no band
    - No kipping; control both concentric and eccentric

    Key Landmarks (MediaPipe):
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    - LEFT_ELBOW (13), RIGHT_ELBOW (14)
    - LEFT_WRIST (15), RIGHT_WRIST (16)
    - NOSE (0) for chin-over-bar detection
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
        """Elbow angle + chin height relative to wrists (bar clearance proxy)."""
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        le = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ELBOW, shape)
        lw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_WRIST, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        re = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ELBOW, shape)
        rw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_WRIST, shape)
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        nose = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.NOSE, shape)

        left_elbow  = analyzer.smooth_angle(analyzer.calculate_angle(ls, le, lw), 'left_elbow')
        right_elbow = analyzer.smooth_angle(analyzer.calculate_angle(rs, re, rw), 'right_elbow')
        avg_elbow   = (left_elbow + right_elbow) / 2
        # Chin above bar: nose y < wrist y (inverted MediaPipe coords)
        chin_clear  = 1 if (nose and lw and nose[1] < lw[1]) else 0

        return {
            'left_elbow': left_elbow, 'right_elbow': right_elbow,
            'avg_elbow': avg_elbow, 'chin_clear': chin_clear,
            'joints_coords': {'ls': ls, 'le': le, 'lw': lw,
                              'rs': rs, 're': re, 'rw': rw, 'lh': lh},
        }

    def get_target_poses(self):
        return {
            'hang': {'avg_elbow': 175, 'chin_clear': 0, 'tolerance': 10},
            'top':  {'avg_elbow': 60,  'chin_clear': 1, 'tolerance': 15},
        }

    def validate_form(self, angles, phase):
        feedback = {}
        cc  = angles.get('chin_clear', 0)
        ea  = angles.get('avg_elbow', 180)
        if phase == 'top' and cc == 0:
            feedback['chin'] = JointFeedback('shoulder', FormStatus.WARNING,
                'Pull higher — chin must clear the bar')
        if phase == 'hang' and ea < 165:
            feedback['dead_hang'] = JointFeedback('elbow', FormStatus.WARNING,
                'Full dead hang — extend arms completely')
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        avg_elbow = angle.get('avg_elbow', 180) if isinstance(angle, dict) else angle
        chin_clear = angle.get('chin_clear', 0) if isinstance(angle, dict) else 0

        if self.phase == 'hang' and avg_elbow < 120:
            self.phase = 'pull'
            self.tempo_detector.start_phase('pull')
        elif self.phase == 'pull' and avg_elbow < 70 and chin_clear:
            self.phase = 'top'
        elif self.phase == 'top' and avg_elbow > 80:
            self.phase = 'lower'
            self.tempo_detector.start_phase('lower')
        elif self.phase == 'lower' and avg_elbow >= 165:
            rep_done = True
            self.phase = 'hang'
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
