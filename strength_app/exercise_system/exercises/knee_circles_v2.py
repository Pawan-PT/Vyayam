"""
Knee Circles V2 - Joint Mobility / Warm-Up

NEW EXERCISE - Created for VYAYAM pre-match stretching protocol
"""

import math
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class KneeCirclesV2:
    """
    Knee Circles - Joint mobility warm-up for knee synovial fluid distribution

    Level: Foundation
    Category: Mobility
    Target: Knee joint capsule, synovial fluid, knee ligament prep

    Biomechanics:
    - Patient stands with feet together, hands on knees
    - Both knees circle together (clockwise then counter-clockwise)
    - Feet stay planted throughout
    - Slow, controlled circular motion (~10 sec per direction)

    CV Tracking:
    - Track knee midpoint relative to ankle midpoint (circular path)
    - Monitor knee symmetry (left-right knees should stay close together)
    - Monitor ankle stability (feet should not move)
    - Phase: clockwise (first 10s) → counter-clockwise (last 10s)

    This is a timed hold exercise (20 seconds), not rep-counted.

    Key Landmarks:
    - LEFT_KNEE (25), RIGHT_KNEE (26)
    - LEFT_ANKLE (27), RIGHT_ANKLE (28)
    - LEFT_HIP (23), RIGHT_HIP (24)
    """

    def __init__(self, target_duration=20):
        self.target_duration = target_duration

        # Time tracking
        self.elapsed_seconds = 0.0
        self.phase = 'clockwise'  # 'clockwise' or 'counter_clockwise'

        # Form tracking
        self.form_scores = []
        self.current_rep_form_scores = []

        # Symmetry tracking — knees should stay together
        self.symmetry_violations = 0
        self.ankle_movement_violations = 0

        # Baseline ankle positions (set on first frame)
        self._baseline_left_ankle = None
        self._baseline_right_ankle = None

        # Detectors
        self.stability_detector = StabilityDetector()

        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()

    def calculate_angles(self, analyzer, results, shape):
        """
        Calculate relevant positions for knee circles.

        Key measurements:
        - Knee midpoint relative to ankle midpoint (tracks circular path)
        - Left-right knee separation (symmetry check)
        - Ankle displacement from baseline (foot stability check)
        """
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)

        # Midpoints
        knee_mid = ((lk[0] + rk[0]) / 2, (lk[1] + rk[1]) / 2)
        ankle_mid = ((la[0] + ra[0]) / 2, (la[1] + ra[1]) / 2)

        # Knee displacement from ankle midpoint (normalised by hip-ankle distance)
        hip_mid = ((lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2)
        ref_height = max(abs(hip_mid[1] - ankle_mid[1]), 1)

        knee_offset_x = (knee_mid[0] - ankle_mid[0]) / ref_height
        knee_offset_y = (knee_mid[1] - ankle_mid[1]) / ref_height

        # Left-right knee horizontal distance (symmetry)
        knee_separation = abs(lk[0] - rk[0])
        ankle_separation = max(abs(la[0] - ra[0]), 1)
        knee_symmetry_ratio = knee_separation / ankle_separation  # ideally ~1.0

        # Ankle stability — how far ankles have drifted from baseline
        if self._baseline_left_ankle is None:
            self._baseline_left_ankle = la
            self._baseline_right_ankle = ra

        left_ankle_drift = math.sqrt(
            (la[0] - self._baseline_left_ankle[0]) ** 2 +
            (la[1] - self._baseline_left_ankle[1]) ** 2
        )
        right_ankle_drift = math.sqrt(
            (ra[0] - self._baseline_right_ankle[0]) ** 2 +
            (ra[1] - self._baseline_right_ankle[1]) ** 2
        )
        max_ankle_drift = max(left_ankle_drift, right_ankle_drift)

        return {
            'knee_offset_x': knee_offset_x,
            'knee_offset_y': knee_offset_y,
            'knee_symmetry_ratio': knee_symmetry_ratio,
            'max_ankle_drift': max_ankle_drift,
            'joints_coords': {
                'lh': lh, 'rh': rh,
                'lk': lk, 'rk': rk,
                'la': la, 'ra': ra,
            }
        }

    def validate_form(self, angles, phase):
        """Validate knee circle form."""
        feedback = {}

        symmetry = angles.get('knee_symmetry_ratio', 1.0)
        ankle_drift = angles.get('max_ankle_drift', 0)

        # Knees should stay roughly together (ratio close to 1)
        if symmetry > 1.5:
            feedback['symmetry'] = JointFeedback(
                FormStatus.NEEDS_ADJUSTMENT, 0,
                "Keep knees together"
            )
        else:
            feedback['symmetry'] = JointFeedback(
                FormStatus.CORRECT, 0,
                "Good symmetry"
            )

        # Feet should stay planted
        if ankle_drift > 20:  # pixels
            feedback['stability'] = JointFeedback(
                FormStatus.NEEDS_ADJUSTMENT, 0,
                "Keep feet planted"
            )

        return feedback

    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score for knee circles."""
        self.stability_detector.update(joints_coords)

        symmetry = angles.get('knee_symmetry_ratio', 1.0)
        ankle_drift = angles.get('max_ankle_drift', 0)

        # Symmetry score (0-50 points)
        if symmetry <= 1.1:
            symmetry_score = 50.0
        elif symmetry <= 1.3:
            symmetry_score = 40.0
        elif symmetry <= 1.5:
            symmetry_score = 25.0
        else:
            symmetry_score = 10.0

        # Foot stability score (0-50 points)
        if ankle_drift <= 5:
            stability_score = 50.0
        elif ankle_drift <= 15:
            stability_score = 40.0
        elif ankle_drift <= 25:
            stability_score = 25.0
        else:
            stability_score = 10.0

        form_score = symmetry_score + stability_score
        self.current_rep_form_scores.append(form_score)
        return form_score

    def update_phase(self, elapsed_seconds):
        """Update clockwise/counter-clockwise phase based on elapsed time."""
        self.elapsed_seconds = elapsed_seconds
        if elapsed_seconds < self.target_duration / 2:
            self.phase = 'clockwise'
        else:
            self.phase = 'counter_clockwise'
        return self.phase

    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        """Draw AR overlay."""
        frame = self.ar.draw_counted_mode(
            frame=frame,
            joints=joints_coords,
            form_score=form_score
        )
        return frame

    def get_stats(self):
        """Get session statistics."""
        avg_form_score = (
            sum(self.form_scores) / len(self.form_scores)
            if self.form_scores else 0
        )

        return {
            'duration_completed': round(self.elapsed_seconds, 1),
            'target_duration': self.target_duration,
            'avg_form_score': round(avg_form_score, 1),
            'form_scores': self.form_scores,
            'symmetry_violations': self.symmetry_violations,
            'ankle_movement_violations': self.ankle_movement_violations,
        }

    def get_summary(self):
        """Get human-readable summary."""
        stats = self.get_stats()
        return (
            f"Knee Circles: {stats['duration_completed']}s completed, "
            f"avg form {stats['avg_form_score']}%"
        )


if __name__ == "__main__":
    print("=" * 70)
    print("KNEE CIRCLES V2 - Joint Mobility Warm-Up")
    print("=" * 70)
    print("\nKnee joint lubrication exercise")
    print("  20 seconds: 10s clockwise + 10s counter-clockwise")
    print("  Feet together, hands on knees")
    print("  Slow controlled circular motion")
    print("=" * 70)
