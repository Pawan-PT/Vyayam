"""
Clamshells V2 - Hip External Rotation Exercise

Reference Video: https://www.youtube.com/watch?v=bO4Bc8w4IGE
(Clamshells - Hip External Rotation Technique)
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class ClamshellsV2:
    """Clamshells - Hip external rotation for PFPS/ITBS"""
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=bO4Bc8w4IGE"
    
    def __init__(self, target_reps=15):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "closed"
        self.last_phase = "closed"
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
        
        # Knee separation (vertical when lying on side)
        knee_separation = abs(lk[1] - rk[1])
        
        # Hip stacking check
        hip_separation = abs(lh[0] - rh[0])
        hips_stacked = hip_separation < 40
        pelvis_rotated = hip_separation > 60
        
        # Knee angles (should stay bent ~90)
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        avg_knee_bend = (left_knee + right_knee) / 2
        
        return {
            'knee_separation': knee_separation,
            'hips_stacked': hips_stacked,
            'pelvis_rotated': pelvis_rotated,
            'avg_knee_bend': avg_knee_bend,
            'joints_coords': {'lh': lh, 'lk': lk, 'la': la, 'rh': rh, 'rk': rk, 'ra': ra}
        }
    
    def get_target_poses(self):
        return {
            'closed': {'knee_separation': 0, 'tolerance': 10},
            'opening': {'knee_separation': 30, 'tolerance': 12},
            'open': {'knee_separation': 45, 'tolerance': 10},
            'closing': {'knee_separation': 20, 'tolerance': 12}
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        
        if angles.get('pelvis_rotated'):
            feedback['pelvis'] = JointFeedback(FormStatus.INCORRECT, 0, "Keep hips stacked")
        elif angles.get('hips_stacked'):
            feedback['pelvis'] = JointFeedback(FormStatus.CORRECT, 0, "Good hip position")
        
        if phase == 'open' and angles['knee_separation'] >= 40:
            feedback['rotation'] = JointFeedback(FormStatus.CORRECT, angles['knee_separation'], "Perfect rotation")
        elif phase == 'open':
            feedback['rotation'] = JointFeedback(FormStatus.NEEDS_ADJUSTMENT, angles['knee_separation'], "Open more")
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        separation = angle  # knee_separation is primary
        
        if self.phase == "closed" and separation <= 15:
            self.tempo_detector.start_phase('closed')
        elif self.phase == "closed" and separation > 20:
            self.phase = "opening"
            voice.speak("Lift knee", priority=False)
        elif self.phase == "opening" and separation >= 35:
            self.phase = "open"
            voice.speak("Hold", priority=False)
        elif self.phase == "open" and separation < 30:
            self.phase = "closing"
            voice.speak("Lower", priority=False)
        elif self.phase == "closing" and separation <= 15:
            rep_done = True
            self.phase = "closed"
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