"""
Hip Abduction Sideline V2 - Side-lying hip strengthening

Reference Video: https://www.youtube.com/watch?v=1TO1KA_WBpg
(Side-Lying Hip Abduction Technique)
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class HipAbductionSidelineV2:
    """Hip Abduction Sideline - Side-lying lateral leg raise"""
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=1TO1KA_WBpg"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "down"
        self.last_phase = "down"
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
        
        left_knee = analyzer.smooth_angle(analyzer.calculate_angle(lh, lk, la), 'left')
        right_knee = analyzer.smooth_angle(analyzer.calculate_angle(rh, rk, ra), 'right')
        
        # Leg separation (vertical distance between ankles when on side)
        leg_separation = abs(la[1] - ra[1])
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'leg_separation': leg_separation,
            'joints_coords': {'lh': lh, 'lk': lk, 'la': la, 'rh': rh, 'rk': rk, 'ra': ra}
        }
    
    def get_target_poses(self):
        return {
            'down': {'leg_separation': 40, 'left_knee': 165, 'tolerance': 10},
            'lifting': {'leg_separation': 100, 'left_knee': 165, 'tolerance': 10},
            'top': {'leg_separation': 150, 'left_knee': 165, 'tolerance': 8},
            'lowering': {'leg_separation': 100, 'left_knee': 165, 'tolerance': 10}
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        left_knee = angles.get('left_knee', 0)
        separation = angles.get('leg_separation', 0)
        
        # Top leg should stay straight
        if phase in ['lifting', 'top', 'lowering']:
            if left_knee >= 160:
                feedback['knee'] = JointFeedback(FormStatus.CORRECT, left_knee, "Leg straight")
            elif left_knee >= 150:
                feedback['knee'] = JointFeedback(FormStatus.NEEDS_ADJUSTMENT, left_knee, "Keep leg straighter")
            else:
                feedback['knee'] = JointFeedback(FormStatus.INCORRECT, left_knee, "Leg must be straight")
        
        # Check abduction range
        if phase == 'top':
            if separation > 150:
                feedback['range'] = JointFeedback(FormStatus.CORRECT, separation, "Perfect height")
            elif separation > 100:
                feedback['range'] = JointFeedback(FormStatus.NEEDS_ADJUSTMENT, separation, "Lift higher")
            else:
                feedback['range'] = JointFeedback(FormStatus.INCORRECT, separation, "Not high enough")
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        separation = angle
        
        if self.phase == "down" and separation < 80:
            self.tempo_detector.start_phase('down')
        elif self.phase == "down" and separation > 90:
            self.phase = "lifting"
            voice.speak("Lift leg", priority=False)
        elif self.phase == "lifting" and separation > 140:
            self.phase = "top"
            voice.speak("Hold", priority=False)
        elif self.phase == "top" and separation < 130:
            self.phase = "lowering"
            voice.speak("Lower", priority=False)
        elif self.phase == "lowering" and separation < 80:
            rep_done = True
            self.phase = "down"
            form_score = self._calculate_rep_form_score()
            self._handle_rep_completion(form_score, voice)
        
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
    print("HIP ABDUCTION SIDELINE V2 - Side-lying hip strengthening")