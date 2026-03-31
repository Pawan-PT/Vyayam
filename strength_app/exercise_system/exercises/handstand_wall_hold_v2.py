"""
Handstand Wall Hold - Isometric handstand against wall, belly facing wall

NEW EXERCISE - Created for VYAYAM V1
"""
import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class HandstandWallHoldV2:
    """Handstand Wall Hold - Level: advanced | Push pattern (isometric)

    Biomechanics:
    - Belly-facing-wall handstand; scapula elevated, arms fully locked
    - Body straight from wrists to ankles — glutes and core braced
    - Shoulder shrug (elevation) is the primary active stabilisation
    - target_duration = 30 seconds; progress toward free-standing

    Key Landmarks (MediaPipe):
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    - LEFT_ELBOW (13), RIGHT_ELBOW (14)
    - LEFT_WRIST (15), RIGHT_WRIST (16)
    - LEFT_HIP (23), LEFT_KNEE (25)
    """


    REFERENCE_VIDEO_URL = ""

    # Form thresholds
    ELBOW_LOCK_MIN       = 155  # degrees — arms must be near straight
    BODY_ALIGN_MIN       = 165  # degrees — no banana arch allowed
    ENTRY_ELBOW_MIN      = 155  # same as lock — must be in position to start timer

    # Progression milestones (seconds)
    BEGINNER_TARGET    = 10
    INTERMEDIATE_TARGET = 20
    ADVANCED_TARGET    = 30

    def __init__(self, target_duration=30):
        self.target_duration = target_duration
        self.phase = "rest"
        self.hold_start_time = None
        self.elapsed = 0.0
        self.best_hold_time = 0.0
        self.hold_completed = False
        self.form_scores = []
        self.stability_detector = StabilityDetector()
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()

    def calculate_angles(self, analyzer, results, shape):
        """Shoulder extension + body alignment for wall-supported handstand."""
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        le = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ELBOW, shape)
        lw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_WRIST, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        re = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ELBOW, shape)
        rw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_WRIST, shape)
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)

        left_elbow   = analyzer.smooth_angle(analyzer.calculate_angle(ls, le, lw), 'left_elbow')
        right_elbow  = analyzer.smooth_angle(analyzer.calculate_angle(rs, re, rw), 'right_elbow')
        avg_elbow    = (left_elbow + right_elbow) / 2
        shoulder_angle = analyzer.calculate_angle(lh, ls, le)   # extension
        body_align   = analyzer.calculate_angle(ls, lh, lk)     # straight body

        return {
            'left_elbow': left_elbow, 'right_elbow': right_elbow,
            'avg_elbow': avg_elbow, 'shoulder_angle': shoulder_angle,
            'body_align': body_align,
            'joints_coords': {'ls': ls, 'le': le, 'lw': lw,
                              'rs': rs, 're': re, 'rw': rw, 'lh': lh, 'lk': lk},
        }

    def get_target_poses(self):
        return {
            'rest': {'avg_elbow': 170, 'tolerance': 20},
            'hold': {'avg_elbow': 175, 'body_align': 175, 'tolerance': 10},
        }

    def validate_form(self, angles, phase):
        feedback = {}
        ea  = angles.get('avg_elbow', 170)
        ba  = angles.get('body_align', 175)
        if phase == 'hold':
            if ea < self.ELBOW_LOCK_MIN:
                feedback['arms'] = JointFeedback('elbow', FormStatus.WARNING,
                    'Lock arms fully — push through shoulders')
            else:
                feedback['arms'] = JointFeedback('elbow', FormStatus.GOOD,
                    'Arms locked — maintain shoulder push')
            if ba < self.BODY_ALIGN_MIN:
                feedback['body'] = JointFeedback('hip', FormStatus.WARNING,
                    'Keep body straight — squeeze glutes and core')
            else:
                feedback['body'] = JointFeedback('hip', FormStatus.GOOD,
                    'Body aligned — solid handstand position')
        elif phase == 'rest':
            feedback['rest'] = JointFeedback('shoulder', FormStatus.GOOD,
                'Kick up into handstand to begin hold timer')
        return feedback

    def get_session_summary(self):
        avg_form = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        milestone = "beginner"
        if self.best_hold_time >= self.ADVANCED_TARGET:
            milestone = "advanced"
        elif self.best_hold_time >= self.INTERMEDIATE_TARGET:
            milestone = "intermediate"
        return {
            'hold_completed': self.hold_completed,
            'best_hold_time': round(self.best_hold_time, 1),
            'avg_form_score': round(avg_form, 1),
            'target_duration': self.target_duration,
            'milestone': milestone,
        }

    def update_hold_timer(self, angles, voice):
        """Isometric hold timer — call each frame during active hold."""
        ea = angles.get('avg_elbow', 170)
        in_position = ea >= 155

        if in_position and self.phase == 'rest':
            self.phase = 'hold'
            self.hold_start_time = time.time()
            voice.cue('Hold position — breathe steadily')

        if self.phase == 'hold':
            if in_position:
                self.elapsed = time.time() - self.hold_start_time
                if self.elapsed > self.best_hold_time:
                    self.best_hold_time = self.elapsed
                if self.elapsed >= self.target_duration and not self.hold_completed:
                    self.hold_completed = True
                    voice.cue(f'Target reached — {self.target_duration}s handstand hold!')
            else:
                self.phase = 'rest'
                voice.cue(f'Hold ended — {self.elapsed:.1f}s')

        return self.phase, round(self.elapsed, 1)

    def calculate_real_time_form_score(self, angles, joints_coords):
        self.stability_detector.update(joints_coords)
        target_angles = self.get_target_poses()[self.phase]
        stability_data = self.stability_detector.get_stability_data()
        form_score = FormCalculator.calculate_form_score(
            angles=angles, target_angles=target_angles,
            stability=stability_data, tempo={}
        )
        self.form_scores.append(form_score)
        return form_score

    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        frame = self.ar.draw_counted_mode(frame, joints_coords, form_score)
        return frame


