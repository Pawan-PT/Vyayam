"""
Sit-to-Stand V2 - Functional ADL Assessment

Reference Video: https://www.youtube.com/watch?v=t7Oj8-8Htyw
(Sit to Stand - Functional Movement Assessment)
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class SitToStandV2:
    """Sit-to-Stand - Functional movement assessment"""
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=t7Oj8-8Htyw"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "sitting"
        self.last_phase = "sitting"
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        self.form_scores = []
        self.current_rep_form_scores = []
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
        avg_knee = (left_knee + right_knee) / 2
        
        # Detect sitting vs standing based on hip height
        hip_height = (lh[1] + rh[1]) / 2
        if not hasattr(self, 'baseline_hip_height'):
            self.baseline_hip_height = hip_height
        
        height_change = self.baseline_hip_height - hip_height
        is_sitting = height_change < 50
        is_standing = height_change > 150
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'hip_height_change': height_change,
            'is_sitting': is_sitting,
            'is_standing': is_standing,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        return {
            'sitting': {'avg_knee': 90, 'tolerance': 15},
            'standing_up': {'avg_knee': 135, 'tolerance': 15},
            'standing': {'avg_knee': 175, 'tolerance': 10},
            'sitting_down': {'avg_knee': 120, 'tolerance': 15}
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        knee_angle = angles.get('avg_knee', 0)
        targets = self.get_target_poses()[phase]
        
        if phase == 'standing':
            if knee_angle >= 165:
                feedback['position'] = JointFeedback(FormStatus.CORRECT, knee_angle, "Fully upright")
            else:
                feedback['position'] = JointFeedback(FormStatus.NEEDS_ADJUSTMENT, knee_angle, "Stand fully straight")
        elif phase == 'sitting':
            if 80 <= knee_angle <= 110:
                feedback['position'] = JointFeedback(FormStatus.CORRECT, knee_angle, "Good seated position")
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        
        if self.phase == "sitting" and angle > 130:
            self.phase = "standing_up"
            self.tempo_detector.start_phase('standing_up')
            voice.speak("Stand up", priority=False)
        
        elif self.phase == "standing_up" and angle >= 165:
            self.phase = "standing"
            voice.speak("Good stand", priority=False)
        
        elif self.phase == "standing" and angle < 155:
            self.phase = "sitting_down"
            self.tempo_detector.start_phase('sitting_down')
            voice.speak("Sit down", priority=False)
        
        elif self.phase == "sitting_down" and angle <= 110:
            rep_done = True
            self.phase = "sitting"
            
            form_score = self._calculate_rep_form_score()
            self._handle_rep_completion(form_score, voice)
        
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
            angles=angles,
            target_angles=target_angles,
            stability=stability_data,
            tempo=tempo_data
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
    print("SIT-TO-STAND V2 - Functional ADL movement assessment")