"""
Superman Hold - Face-down isometric hold lifting arms and legs

NEW EXERCISE - Created for VYAYAM V1
"""
import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class SupermanHoldV2:
    """Superman Hold - Level: foundation | Pull pattern (isometric)

    Biomechanics:
    - Face down; simultaneously lift arms and legs off floor
    - Primary muscles: erector spinae, glutes, posterior deltoids
    - Lift from upper back, not just arms — scapular retraction key
    - Head in neutral — look at floor, not forward
    - target_duration = 30 seconds

    Key Landmarks (MediaPipe):
    - LEFT_SHOULDER (11), RIGHT_SHOULDER (12)
    - LEFT_ELBOW (13), LEFT_WRIST (15)
    - LEFT_HIP (23), LEFT_KNEE (25)
    """


    REFERENCE_VIDEO_URL = ""

    # Form thresholds
    ARM_ELEVATION_ENTRY  = 55   # degrees — minimum to enter hold phase
    ARM_ELEVATION_TARGET = 80   # degrees — ideal arm elevation
    HIP_EXTENSION_MIN    = 160  # degrees — legs must be near straight
    HIP_EXTENSION_TARGET = 175  # degrees — ideal leg extension

    # Progression milestones (seconds)
    BEGINNER_TARGET   = 10
    INTERMEDIATE_TARGET = 20
    ADVANCED_TARGET   = 30

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
        """Arm elevation + hip extension for superman position."""
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        le = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ELBOW, shape)
        lw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_WRIST, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)

        arm_elevation = analyzer.calculate_angle(lh, ls, le)
        hip_extension = analyzer.calculate_angle(ls, lh, lk)
        left_elbow    = analyzer.smooth_angle(analyzer.calculate_angle(ls, le, lw), 'left_elbow')

        return {
            'arm_elevation': arm_elevation, 'hip_extension': hip_extension,
            'left_elbow': left_elbow,
            'joints_coords': {'ls': ls, 'le': le, 'lw': lw, 'rs': rs, 'lh': lh, 'lk': lk},
        }

    def get_target_poses(self):
        return {
            'rest': {'arm_elevation': 15, 'tolerance': 20},
            'hold': {'arm_elevation': 80, 'hip_extension': 175, 'tolerance': 15},
        }

    def validate_form(self, angles, phase):
        feedback = {}
        if phase == 'hold':
            ae = angles.get('arm_elevation', 0)
            he = angles.get('hip_extension', 180)
            if ae < self.ARM_ELEVATION_ENTRY:
                feedback['arms'] = JointFeedback('shoulder', FormStatus.WARNING,
                    'Lift arms higher — squeeze from upper back')
            elif ae < self.ARM_ELEVATION_TARGET:
                feedback['arms'] = JointFeedback('shoulder', FormStatus.GOOD,
                    'Arms lifting — aim for full extension')
            if he < self.HIP_EXTENSION_MIN:
                feedback['legs'] = JointFeedback('hip', FormStatus.WARNING,
                    'Keep legs straight and lifted')
            if ae >= self.ARM_ELEVATION_TARGET and he >= self.HIP_EXTENSION_MIN:
                feedback['position'] = JointFeedback('shoulder', FormStatus.GOOD,
                    'Perfect superman position — breathe steadily')
        elif phase == 'rest':
            feedback['rest'] = JointFeedback('shoulder', FormStatus.GOOD,
                'Ready — lift arms and legs simultaneously to begin')
        return feedback

    def update_hold_timer(self, angles, voice):
        """Isometric hold timer for superman position."""
        ae = angles.get('arm_elevation', 0)
        he = angles.get('hip_extension', 180)
        in_position = ae >= 55 and he >= 160

        if in_position and self.phase == 'rest':
            self.phase = 'hold'
            self.hold_start_time = time.time()
            voice.cue('Hold — squeeze from upper back')

        if self.phase == 'hold':
            if in_position:
                self.elapsed = time.time() - self.hold_start_time
                if self.elapsed > self.best_hold_time:
                    self.best_hold_time = self.elapsed
                if self.elapsed >= self.target_duration and not self.hold_completed:
                    self.hold_completed = True
                    voice.cue(f'Hold complete — {self.target_duration}s superman hold!')
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
