"""
Plank Shoulder Tap - Plank with alternating shoulder taps resisting hip rotation.

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2, time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class PlankShoulderTapV2:
    """Plank Shoulder Tap. Level: foundation (L2). Category: rotate. Target: core anti-rotation, shoulders."""

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=20):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "plank"
        self.last_phase = "plank"
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        self.form_scores = []
        self.current_rep_form_scores = []
        self.stability_detector = StabilityDetector()
        self.tempo_detector = TempoDetector()
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        self._tap_side = None
        self._TAP_ASYMMETRY_THRESHOLD = 0.05  # 5% of shoulder-to-hip dist (~2.5 cm); captures shallow taps
        # Unilateral rep tracking for asymmetry detection (Agent 5 requirement)
        self.left_rep_count = 0
        self.right_rep_count = 0
        self.form_scores_left = []
        self.form_scores_right = []

    def calculate_angles(self, analyzer, results, shape):
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        le = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ELBOW, shape)
        re = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ELBOW, shape)
        lw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_WRIST, shape)
        rw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_WRIST, shape)
        avg_knee = (analyzer.smooth_angle(analyzer.calculate_angle(lh,lk,la),'left') +
                    analyzer.smooth_angle(analyzer.calculate_angle(rh,rk,ra),'right')) / 2
        avg_hip  = (analyzer.calculate_angle(ls,lh,lk) + analyzer.calculate_angle(rs,rh,rk)) / 2
        avg_elbow= (analyzer.smooth_angle(analyzer.calculate_angle(ls,le,lw),'left') +
                    analyzer.smooth_angle(analyzer.calculate_angle(rs,re,rw),'right')) / 2

        return {'avg_knee':avg_knee,'avg_hip':avg_hip,'avg_elbow':avg_elbow,
                'joints_coords':{'ls':ls,'rs':rs,'lh':lh,'rh':rh,'lk':lk,'rk':rk,
                                  'la':la,'ra':ra,'le':le,'re':re,'lw':lw,'rw':rw}}

    def get_target_poses(self):
        return {phase:{'avg_knee':90,'tolerance':20} for phase in ['plank', 'tapping']}

    def validate_form(self, angles, phase):
        feedback = {}
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        """State machine for plank shoulder tap.

        Phase "plank"   — both wrists approximately level (on the ground).
        Phase "tapping" — one wrist is raised significantly above the other,
                          indicating the shoulder-tap arm is lifted.

        Transition plank → tapping : wrist Y-asymmetry exceeds threshold
                                      (in image coordinates, a *lower* Y value
                                       means *higher* in the frame, i.e. the
                                       wrist is further from the ground).
        Transition tapping → plank : wrist Y-asymmetry falls back below threshold.
        Rep counted                 : on the tapping → plank transition (one
                                      complete lift-and-return constitutes one rep).
        """
        rep_done = False
        warnings = []
        angles_dict = angle if isinstance(angle, dict) else {}

        # Pull wrist coordinates from the joints_coords sub-dict if present.
        # calculate_angles() stores them as pixel (x, y) tuples.
        joints_coords = angles_dict.get('joints_coords', {})
        lw = joints_coords.get('lw')
        rw = joints_coords.get('rw')

        if lw is not None and rw is not None:
            # Y-coordinate: smaller value = higher in the image = wrist is lifted.
            # Normalise the difference against a rough frame-height proxy using the
            # shoulder–hip distance so the threshold is scale-independent.
            ls = joints_coords.get('ls')
            lh = joints_coords.get('lh')
            if ls is not None and lh is not None:
                ref_dist = abs(ls[1] - lh[1]) or 1  # pixels, never zero
            else:
                ref_dist = 100  # fallback pixels

            wrist_y_diff = (rw[1] - lw[1]) / ref_dist  # positive → left wrist higher

            left_raised  = wrist_y_diff >  self._TAP_ASYMMETRY_THRESHOLD
            right_raised = wrist_y_diff < -self._TAP_ASYMMETRY_THRESHOLD

            if self.phase == "plank":
                if left_raised or right_raised:
                    # One hand has left the ground — entering the tap phase
                    self._tap_side = "left" if left_raised else "right"
                    self.phase = "tapping"
                    self.tempo_detector.start_phase("tapping")

            elif self.phase == "tapping":
                if not left_raised and not right_raised:
                    # Both wrists are back near ground level — tap complete
                    rep_done = True
                    completed_side = self._tap_side
                    self.phase = "plank"
                    form_score = self._calculate_rep_form_score()
                    self._handle_rep_completion(form_score, voice, side=completed_side)
                    self._tap_side = None

        if self.phase != self.last_phase:
            self.last_phase = self.phase

        return rep_done, self.phase, warnings

    def _calculate_rep_form_score(self):
        if self.current_rep_form_scores:
            avg = sum(self.current_rep_form_scores)/len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg
        return 85.0

    def _handle_rep_completion(self, form_score, voice, side=None):
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
            # Unilateral tracking for asymmetry detection
            if side == 'left':
                self.left_rep_count += 1
                self.form_scores_left.append(form_score)
            elif side == 'right':
                self.right_rep_count += 1
                self.form_scores_right.append(form_score)
            voice.announce_rep(self.rep_count, self.target_reps, form_score)

    def calculate_real_time_form_score(self, angles, joints_coords):
        self.stability_detector.update(joints_coords)
        target_angles = self.get_target_poses().get(self.phase, {'avg_knee':90,'tolerance':20})
        stability_data = self.stability_detector.get_stability_data()
        tempo_data = self.tempo_detector.check_tempo()
        form_score = FormCalculator.calculate_form_score(angles=angles, target_angles=target_angles,
            stability=stability_data, tempo=tempo_data)
        self.current_rep_form_scores.append(form_score)
        return form_score

    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        if self.probation_mode:
            frame, _ = self.ar.draw_practice_mode(frame, joints_coords, angles,
                                                   self.get_target_poses().get(self.phase,{'avg_knee':90,'tolerance':20}), form_score)
        else:
            frame = self.ar.draw_counted_mode(frame, joints_coords, form_score)
        return frame

    def get_asymmetry(self):
        total = self.left_rep_count + self.right_rep_count
        if total == 0:
            return 'none'
        asymmetry_pct = abs(self.left_rep_count - self.right_rep_count) / total * 100
        if asymmetry_pct > 20:
            return 'significant'
        elif asymmetry_pct > 10:
            return 'mild'
        return 'none'

    def get_summary(self):
        avg_form = sum(self.form_scores)/len(self.form_scores) if self.form_scores else 0
        return {
            'rep_count': self.rep_count,
            'left_rep_count': self.left_rep_count,
            'right_rep_count': self.right_rep_count,
            'tap_asymmetry': self.get_asymmetry(),
            'rejected_count': self.rejected_count,
            'avg_form_score': round(avg_form, 1),
            'target_reps': self.target_reps,
        }
