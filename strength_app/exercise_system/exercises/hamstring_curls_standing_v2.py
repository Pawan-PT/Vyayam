"""
Hamstring Curls Standing V2 - Single-leg hamstring strengthening

Reference Video: https://www.youtube.com/watch?v=1Tq3QdYUuHs
(Standing Hamstring Curl Technique)
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class HamstringCurlsStandingV2:
    """Hamstring Curls - Standing single-leg hamstring work"""
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=1Tq3QdYUuHs"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "straight"
        self.last_phase = "straight"
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        self.form_scores = []
        self.current_rep_form_scores = []
        self.working_leg = 'left'
        self.stability_detector = StabilityDetector()
        self.tempo_detector = TempoDetector()
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
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
        left_hip = analyzer.calculate_angle(ls, lh, lk)
        right_hip = analyzer.calculate_angle(rs, rh, rk)
        
        # Detect working leg (more bent knee)
        if left_knee < right_knee - 20:
            self.working_leg = 'left'
            working_knee = left_knee
            working_hip = left_hip
            support_knee = right_knee
        elif right_knee < left_knee - 20:
            self.working_leg = 'right'
            working_knee = right_knee
            working_hip = right_hip
            support_knee = left_knee
        else:
            working_knee = min(left_knee, right_knee)
            working_hip = min(left_hip, right_hip)
            support_knee = max(left_knee, right_knee)
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'left_hip': left_hip,
            'right_hip': right_hip,
            'working_knee': working_knee,
            'working_hip': working_hip,
            'support_knee': support_knee,
            'working_leg': self.working_leg,
            'joints_coords': {'lh': lh, 'lk': lk, 'la': la, 'rh': rh, 'rk': rk, 'ra': ra, 'ls': ls, 'rs': rs}
        }
    
    def get_target_poses(self):
        return {
            'straight': {'working_knee': 170, 'working_hip': 170, 'tolerance': 8},
            'curling': {'working_knee': 120, 'working_hip': 165, 'tolerance': 12},
            'top': {'working_knee': 85, 'working_hip': 165, 'tolerance': 12},
            'extending': {'working_knee': 120, 'working_hip': 165, 'tolerance': 12}
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        working_knee = angles.get('working_knee', 0)
        working_hip = angles.get('working_hip', 0)
        support_knee = angles.get('support_knee', 0)
        
        # Hip must stay neutral (don't lean forward)
        if phase in ['curling', 'top', 'extending']:
            if 160 <= working_hip <= 180:
                feedback['hip'] = JointFeedback(FormStatus.CORRECT, working_hip, "Good hip position")
            elif 150 <= working_hip < 160:
                feedback['hip'] = JointFeedback(FormStatus.NEEDS_ADJUSTMENT, working_hip, "Keep thigh vertical")
            else:
                feedback['hip'] = JointFeedback(FormStatus.INCORRECT, working_hip, "Don't lean forward")
        
        # Support leg should stay straight
        if support_knee < 160:
            feedback['support'] = JointFeedback(FormStatus.INCORRECT, support_knee, "Support leg straight")
        
        # Knee flexion
        if phase == 'top':
            if working_knee <= 100:
                feedback['curl'] = JointFeedback(FormStatus.CORRECT, working_knee, "Perfect curl")
            elif working_knee <= 125:
                feedback['curl'] = JointFeedback(FormStatus.NEEDS_ADJUSTMENT, working_knee, "Curl more")
            else:
                feedback['curl'] = JointFeedback(FormStatus.INCORRECT, working_knee, "Not enough flexion")
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        working_knee = angle
        
        if self.phase == "straight" and working_knee >= 165:
            self.tempo_detector.start_phase('straight')
        elif self.phase == "straight" and working_knee < 160:
            self.phase = "curling"
            voice.speak("Curl up", priority=False)
        elif self.phase == "curling" and working_knee <= 125:
            self.phase = "top"
            voice.speak("Hold", priority=False)
        elif self.phase == "top" and working_knee > 110:
            self.phase = "extending"
            voice.speak("Lower slowly", priority=False)
        elif self.phase == "extending" and working_knee >= 160:
            rep_done = True
            self.phase = "straight"
            form_score = self._calculate_rep_form_score()
            self._handle_rep_completion(form_score, voice)
        
        warnings.append(f"Working: {self.working_leg}")
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
        form_score = FormCalculator.calculate_form_score(
            angles=angles,
            target_angles=self.get_target_poses()[self.phase],
            stability=self.stability_detector.get_stability_data(),
            tempo=self.tempo_detector.check_tempo()
        )
        self.current_rep_form_scores.append(form_score)
        return form_score
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        if self.probation_mode:
            frame, _ = self.ar.draw_practice_mode(frame, joints_coords, angles, self.get_target_poses()[self.phase], form_score)
        else:
            frame = self.ar.draw_counted_mode(frame, joints_coords, form_score)
        return frame
    
    def get_stats(self):
        avg_form_score = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        return {
            'reps_completed': self.rep_count,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("HAMSTRING CURLS STANDING V2 - Single-leg hamstring strengthening")