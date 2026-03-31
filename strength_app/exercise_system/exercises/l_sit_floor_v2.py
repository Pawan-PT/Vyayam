"""
L-Sit Floor - Seated hands on floor lift body with legs extended isometric hold.

NEW EXERCISE - Created for VYAYAM V1
"""

import cv2, time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class LSitFloorV2:
    """L-Sit Floor. Level: advanced (L4). Category: rotate. Target: hip flexors, triceps, core."""

    REFERENCE_VIDEO_URL = ""

    def __init__(self, target_duration=20):
        self.target_duration = target_duration
        self.phase = "setup"
        self.last_phase = "setup"
        self.hold_start_time = None
        self.elapsed_hold = 0.0
        self.hold_completed = False
        self.form_scores = []
        self.current_rep_form_scores = []
        self._last_milestone = 0
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
        avg_knee = (analyzer.calculate_angle(lh,lk,la) + analyzer.calculate_angle(rh,rk,ra))/2
        avg_hip  = (analyzer.calculate_angle(ls,lh,lk) + analyzer.calculate_angle(rs,rh,rk))/2
        avg_elbow= (analyzer.calculate_angle(ls,le,lw) + analyzer.calculate_angle(rs,re,rw))/2

        return {'avg_knee':avg_knee,'avg_hip':avg_hip,'avg_elbow':avg_elbow,
                'elapsed_hold':self.elapsed_hold,
                'joints_coords':{'ls':ls,'rs':rs,'lh':lh,'rh':rh,'lk':lk,'rk':rk,
                                  'la':la,'ra':ra,'le':le,'re':re,'lw':lw,'rw':rw}}

    def get_target_poses(self):
        return {'setup':{'avg_knee':175,'tolerance':20}, 'holding':{'avg_knee':90,'tolerance':20}}

    def validate_form(self, angles, phase):
        feedback = {}
        return feedback

    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        angles_dict = angle if isinstance(angle, dict) else {}
        avg_hip = angles_dict.get('avg_hip', 175)
        if self.phase == "setup" and avg_hip < 155:
            self.phase = "holding"
            self.hold_start_time = time.time()
            voice.say("Hold")
        elif self.phase == "holding":
            if self.hold_start_time:
                self.elapsed_hold = time.time() - self.hold_start_time
            milestone = int(self.elapsed_hold // 10) * 10
            if milestone > self._last_milestone and milestone > 0:
                self._last_milestone = milestone
                remaining = max(0, self.target_duration - self.elapsed_hold)
                voice.say(f"{int(remaining)} seconds remaining")
            if self.elapsed_hold >= self.target_duration:
                rep_done = True
                self.hold_completed = True
                self.phase = "setup"
                voice.say("Hold complete!")
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        return rep_done, self.phase, warnings

    def _calculate_rep_form_score(self):
        if self.current_rep_form_scores:
            avg = sum(self.current_rep_form_scores)/len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg
        return 85.0

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
        remaining = max(0.0, self.target_duration - self.elapsed_hold)
        frame = self.ar.draw_counted_mode(frame, joints_coords, form_score, timer_remaining=remaining)
        return frame

    def get_summary(self):
        avg_form = sum(self.form_scores)/len(self.form_scores) if self.form_scores else 0
        return {'hold_completed':self.hold_completed,'elapsed_hold':round(self.elapsed_hold,1),
                'target_duration':self.target_duration,'avg_form_score':round(avg_form,1)}
