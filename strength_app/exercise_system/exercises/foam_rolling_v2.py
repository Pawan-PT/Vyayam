"""
Foam Rolling V2 - Myofascial Release Exercise

Reference Video: https://www.youtube.com/watch?v=5g7taLvZZnQ
(Foam Rolling ITB and Quads Technique)
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class FoamRollingV2:
    """Foam Rolling - 60-second timed myofascial release"""
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=5g7taLvZZnQ"
    
    def __init__(self, target_reps=2):  # 2 areas (ITB and Quads)
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "rolling"
        self.probation_mode = True
        self.practice_reps_needed = 1
        self.practice_reps_completed = 0
        self.form_scores = []
        self.roll_start_time = None
        self.roll_duration_required = 60.0  # 60 seconds
        self.announced_seconds = set()
        self.current_area = "ITB"
        self.stability_detector = StabilityDetector()
        self.tempo_detector = TempoDetector()
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        
        # Detect movement (rolling)
        if not hasattr(self, 'last_hip_pos'):
            self.last_hip_pos = (lh[1] + rh[1]) / 2
        
        current_hip_pos = (lh[1] + rh[1]) / 2
        movement = abs(current_hip_pos - self.last_hip_pos)
        rolling_detected = movement > 3
        self.last_hip_pos = current_hip_pos
        
        return {
            'rolling_detected': rolling_detected,
            'movement': movement,
            'joints_coords': {'lh': lh, 'rh': rh}
        }
    
    def get_target_poses(self):
        return {'rolling': {'movement': 3, 'tolerance': 5}}
    
    def validate_form(self, angles, phase):
        feedback = {}
        if angles.get('rolling_detected'):
            feedback['movement'] = JointFeedback(FormStatus.CORRECT, 0, "Good rolling")
        else:
            feedback['movement'] = JointFeedback(FormStatus.NEEDS_ADJUSTMENT, 0, "Keep rolling")
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        
        if self.roll_start_time is None:
            self.roll_start_time = time.time()
            self.announced_seconds = set()
        
        elapsed = time.time() - self.roll_start_time
        current_second = int(elapsed)
        
        # Announce milestones
        if current_second in [15, 30, 45] and current_second not in self.announced_seconds:
            self.announced_seconds.add(current_second)
            voice.speak(f"{current_second} seconds", priority=False)
        
        warnings.append(f"{self.current_area} Roll: {int(elapsed)}s / {int(self.roll_duration_required)}s")
        
        if elapsed >= self.roll_duration_required:
            rep_done = True
            form_score = 85.0  # Completion-based
            
            if self.probation_mode:
                self.practice_reps_completed += 1
                if self.practice_reps_completed >= self.practice_reps_needed:
                    self.probation_mode = False
                    voice.speak("Now counting", priority=True)
            else:
                self.rep_count += 1
                self.form_scores.append(form_score)
                voice.announce_rep(self.rep_count, self.target_reps, form_score)
                # Switch areas
                self.current_area = "Quads" if self.current_area == "ITB" else "ITB"
                voice.speak(f"Switch to {self.current_area}", priority=True)
            
            self.roll_start_time = None
        
        return rep_done, self.phase, warnings
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        return 85.0  # Foam rolling is completion-based
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        if self.probation_mode:
            frame, _ = self.ar.draw_practice_mode(frame, joints_coords, angles, self.get_target_poses()[self.phase], form_score)
        else:
            frame = self.ar.draw_counted_mode(frame, joints_coords, form_score)
        return frame
    
    def get_stats(self):
        return {
            'areas_completed': self.rep_count,
            'practice_areas': self.practice_reps_completed,
            'target_areas': self.target_reps
        }