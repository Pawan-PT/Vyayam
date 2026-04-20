"""
Overhead Carry - Both arms overhead holding weight walk for distance.

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2, time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class OverheadCarryV2:
    """Overhead Carry. Level: intermediate (L3). Category: carry. Target: deltoids, core stability, traps."""

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "walking"
        self.last_phase = "walking"
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
        return {phase:{'avg_knee':90,'tolerance':20} for phase in ['start', 'active', 'walking']}

    def validate_form(self, angles, phase):
        feedback = {}
        targets = self.get_target_poses().get(phase, {})
        tolerance = targets.get('tolerance', 20)
        for angle_key in ('avg_knee', 'avg_hip', 'avg_elbow'):
            target_val = targets.get(angle_key)
            if target_val is None or angle_key not in angles:
                continue
            diff = abs(angles[angle_key] - target_val)
            if diff <= tolerance:
                status, msg = FormStatus.CORRECT, 'Good position'
            elif diff <= tolerance * 1.5:
                status, msg = FormStatus.NEEDS_ADJUSTMENT, 'Adjust position'
            else:
                status, msg = FormStatus.INCORRECT, 'Check alignment'
            feedback[angle_key] = JointFeedback(
                status=status,
                angle=angles[angle_key],
                message=msg,
            )
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        angles_dict = angle if isinstance(angle, dict) else {}
        avg_hip = angles_dict.get('avg_hip', 175)
        if self.phase == "start" and avg_hip < 155:
            self.phase = "active"
            self.tempo_detector.start_phase('active')
        elif self.phase == "active" and avg_hip >= 165:
            rep_done = True
            self.phase = "start"
            form_score = self._calculate_rep_form_score()
            self._handle_rep_completion(form_score, voice)
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        return rep_done, self.phase, warnings

    def _calculate_rep_form_score(self):
        if self.current_rep_form_scores:
            avg = sum(self.current_rep_form_scores)/len(self.current_rep_form_scores)
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

    def get_summary(self):
        avg_form = sum(self.form_scores)/len(self.form_scores) if self.form_scores else 0
        return {'rep_count':self.rep_count,'rejected_count':self.rejected_count,
                'avg_form_score':round(avg_form,1),'target_reps':self.target_reps}
