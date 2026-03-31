"""
Knee Extension Sitting V2 - Quadriceps Strengthening

Reference Video: https://www.youtube.com/watch?v=v_R4c04GuKE
(Seated Knee Extension - Quad Strengthening)
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class KneeExtensionSittingV2:
    """Knee Extension - Seated quadriceps strengthening"""
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=v_R4c04GuKE"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "bent"
        self.last_phase = "bent"
        self.probation_mode = True
        self.practice_reps_needed = 2
        self.practice_reps_completed = 0
        self.form_scores = []
        self.current_rep_form_scores = []
        self.working_leg = 'left'  # Detect which leg is working
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
        
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right')
        
        # Detect working leg (more extended)
        if left_knee > right_knee + 20:
            self.working_leg = 'left'
            working_knee = left_knee
            resting_knee = right_knee
        elif right_knee > left_knee + 20:
            self.working_leg = 'right'
            working_knee = right_knee
            resting_knee = left_knee
        else:
            working_knee = max(left_knee, right_knee)
            resting_knee = min(left_knee, right_knee)
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'working_knee': working_knee,
            'resting_knee': resting_knee,
            'working_leg': self.working_leg,
            'joints_coords': {'lh': lh, 'lk': lk, 'la': la, 'rh': rh, 'rk': rk, 'ra': ra}
        }
    
    def get_target_poses(self):
        return {
            'bent': {'working_knee': 95, 'tolerance': 10},
            'extending': {'working_knee': 130, 'tolerance': 15},
            'extended': {'working_knee': 165, 'tolerance': 8},
            'flexing': {'working_knee': 130, 'tolerance': 15}
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        working_knee = angles.get('working_knee', 0)
        resting_knee = angles.get('resting_knee', 0)
        
        # Resting leg should stay bent
        if resting_knee > 120:
            feedback['resting'] = JointFeedback(FormStatus.INCORRECT, resting_knee, "Keep other leg still")
        
        if phase == 'extended':
            if working_knee >= 165:
                feedback['extension'] = JointFeedback(FormStatus.CORRECT, working_knee, "Perfect extension")
            elif working_knee >= 155:
                feedback['extension'] = JointFeedback(FormStatus.NEEDS_ADJUSTMENT, working_knee, "Straighten more")
            else:
                feedback['extension'] = JointFeedback(FormStatus.INCORRECT, working_knee, "Full extension needed")
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        working_knee = angle
        
        if self.phase == "bent" and 80 <= working_knee <= 110:
            self.tempo_detector.start_phase('bent')
        elif self.phase == "bent" and working_knee > 115:
            self.phase = "extending"
            voice.speak("Straighten knee", priority=False)
        elif self.phase == "extending" and working_knee >= 155:
            self.phase = "extended"
            voice.speak("Hold", priority=False)
        elif self.phase == "extended" and working_knee < 150:
            self.phase = "flexing"
            voice.speak("Lower slowly", priority=False)
        elif self.phase == "flexing" and working_knee <= 110:
            rep_done = True
            self.phase = "bent"
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
    print("KNEE EXTENSION SITTING V2 - Seated quad strengthening")