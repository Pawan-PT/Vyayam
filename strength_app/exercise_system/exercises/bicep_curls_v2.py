"""
Bicep Curls V2 - Arm flexion exercise

NEW EXERCISE for arm strength

Level: Foundation
Category: Strength (Upper Body)
Target: Biceps, brachialis
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class BicepCurlsV2:
    """
    Bicep Curls - Classic arm flexion exercise
    
    Level: Foundation
    Category: Strength (Upper Body)
    Target: Biceps brachii, brachialis, brachioradialis
    
    Reference Video: https://www.youtube.com/watch?v=ykJmrZ5v0Oo
    (Dumbbell Bicep Curl - Proper Form Tutorial)
    
    Biomechanics:
    - Primary: Elbow flexion (shoulder → elbow → wrist)
    - Starting: 170° elbow extension (arms down, straight)
    - Top: 30-45° elbow flexion (fully contracted bicep)
    - CRITICAL: Elbows stay stable (no swinging)
    - Shoulder stays stable (no momentum)
    
    BILATERAL: Both arms curl together
    
    Phases:
    1. Extended (arms down, elbows straight)
    2. Flexing (curling weight up)
    3. Contracted (biceps fully flexed at top)
    4. Extending (lowering weight controlled)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=ykJmrZ5v0Oo"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        self.phase = "extended"
        self.last_phase = "extended"
        
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        
        self.form_scores = []
        self.current_rep_form_scores = []
        
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """Calculate elbow angles"""
        # Get joints
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        le = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ELBOW, shape)
        lw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_WRIST, shape)
        
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        re = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ELBOW, shape)
        rw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_WRIST, shape)
        
        # Elbow angles
        left_elbow = analyzer.calculate_angle(ls, le, lw)
        right_elbow = analyzer.calculate_angle(rs, re, rw)
        
        # Smooth
        left_elbow = analyzer.smooth_angle(left_elbow, 'left')
        right_elbow = analyzer.smooth_angle(right_elbow, 'right')
        
        # Average
        avg_elbow = (left_elbow + right_elbow) / 2
        
        return {
            'left_elbow': left_elbow,
            'right_elbow': right_elbow,
            'avg_elbow': avg_elbow,
            'joints_coords': {
                'ls': ls, 'le': le, 'lw': lw,
                'rs': rs, 're': re, 'rw': rw
            }
        }
    
    def get_target_poses(self):
        """Target angles for each phase"""
        return {
            'extended': {
                'avg_elbow': 170,  # Arms straight
                'tolerance': 10
            },
            'flexing': {
                'avg_elbow': 100,  # Midway curl
                'tolerance': 15
            },
            'contracted': {
                'avg_elbow': 40,   # Fully curled
                'tolerance': 12
            },
            'extending': {
                'avg_elbow': 120,  # Lowering
                'tolerance': 15
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate form"""
        feedback = {}
        targets = self.get_target_poses()[phase]
        
        # Elbow angle
        elbow_angle = angles.get('avg_elbow', 0)
        elbow_target = targets['avg_elbow']
        
        if abs(elbow_angle - elbow_target) <= 12:
            feedback['elbow'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=elbow_angle,
                message="Good curl"
            )
        elif abs(elbow_angle - elbow_target) <= 20:
            feedback['elbow'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=elbow_angle,
                message="Full range needed"
            )
        else:
            feedback['elbow'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=elbow_angle,
                message="Check form"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """Update rep counter"""
        rep_done = False
        warnings = []
        
        # State machine
        if self.phase == "extended" and angle < 150:
            self.phase = "flexing"
            self.tempo_detector.start_phase('flexing')
            voice.speak("Curl up", priority=False)
        
        elif self.phase == "flexing" and angle < 55:
            self.phase = "contracted"
            self.tempo_detector.start_phase('contracted')
            voice.speak("Squeeze biceps", priority=False)
        
        elif self.phase == "contracted" and angle > 65:
            self.phase = "extending"
            self.tempo_detector.start_phase('extending')
            voice.speak("Lower controlled", priority=False)
        
        elif self.phase == "extending" and angle > 165:
            # Rep complete
            rep_done = True
            self.phase = "extended"
            
            form_score = self._calculate_rep_form_score()
            self._handle_rep_completion(form_score, voice)
        
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate form score"""
        if self.current_rep_form_scores:
            avg = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg
        return 85.0
    
    def _handle_rep_completion(self, form_score, voice):
        """Handle rep completion"""
        if self.probation_mode:
            if form_score >= 85:
                self.practice_reps_completed += 1
                voice.announce_practice_rep(
                    self.practice_reps_completed,
                    self.practice_reps_needed,
                    form_score
                )
                
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
        """Calculate real-time form score"""
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
        
        # Penalty for swinging (wild movement)
        if stability_data.get('wild_movement'):
            form_score -= 15
        
        self.current_rep_form_scores.append(form_score)
        return form_score
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        """Draw AR overlay"""
        if self.probation_mode:
            frame, _ = self.ar.draw_practice_mode(
                frame=frame,
                joints=joints_coords,
                current_angles=angles,
                target_angles=self.get_target_poses()[self.phase],
                form_score=form_score
            )
        else:
            frame = self.ar.draw_counted_mode(
                frame=frame,
                joints=joints_coords,
                form_score=form_score
            )
        
        return frame
    
    def get_stats(self):
        """Get statistics"""
        avg_form = (sum(self.form_scores) / len(self.form_scores) 
                   if self.form_scores else 0)
        
        return {
            'reps_completed': self.rep_count,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("BICEP CURLS V2 - Arm flexion exercise")
    print("No swinging, controlled movement")
    print("Ready to run!")