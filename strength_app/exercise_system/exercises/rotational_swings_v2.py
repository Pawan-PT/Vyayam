"""
Rotational Swings V2 - Core rotation exercise

NEW EXERCISE for core and oblique strength

Level: Intermediate
Category: Core, Power
Target: Obliques, rotational power
"""

import cv2
import time
import math
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class RotationalSwingsV2:
    """
    Rotational Swings - Core rotation exercise (Wood Chops)
    
    Level: Intermediate
    Category: Core, Power
    Target: Obliques, transverse abdominis, shoulders
    
    Reference Video: https://www.youtube.com/watch?v=pAplQXk3dkU
    (Wood Chop Exercise - Core Rotation)
    
    Biomechanics:
    - Primary: Torso rotation (shoulder line angle)
    - Starting: Center position (shoulders parallel to camera)
    - Rotation: ~45° rotation left/right
    - CRITICAL: Rotation from core, not just arms
    - Back stays straight during rotation
    
    BILATERAL: Rotate to both sides
    
    Phases:
    1. Center (neutral position)
    2. Rotating Right (twisting to right)
    3. Right Peak (maximum right rotation)
    4. Returning to Center
    5. Rotating Left (twisting to left)
    6. Left Peak (maximum left rotation)
    7. Returning to Center
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=pAplQXk3dkU"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        self.phase = "center"
        self.last_phase = "center"
        self.rotation_side = "right"  # Alternate: right, left
        
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
        """Calculate shoulder rotation angle"""
        # Get shoulders
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        # Get hips for back angle check
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        
        # Calculate shoulder line angle (rotation indicator)
        # Angle of line from left shoulder to right shoulder
        dx = rs[0] - ls[0]
        dy = rs[1] - ls[1]
        shoulder_angle = math.degrees(math.atan2(dy, dx))
        
        # Normalize to 0-180 range
        if shoulder_angle < 0:
            shoulder_angle += 180
        
        # Calculate rotation from center (90° = centered)
        rotation = abs(shoulder_angle - 90)
        
        # Back angle (approximate - should stay straight)
        back_angle = 165  # Simplified for rotation exercise
        
        return {
            'shoulder_angle': shoulder_angle,
            'rotation': rotation,
            'back_angle': back_angle,
            'joints_coords': {
                'ls': ls, 'rs': rs,
                'lh': lh, 'rh': rh
            }
        }
    
    def get_target_poses(self):
        """Target angles for each phase"""
        return {
            'center': {
                'rotation': 5,  # Minimal rotation at center
                'back_angle': 165,
                'tolerance': 10
            },
            'rotating': {
                'rotation': 25,  # Mid rotation
                'back_angle': 165,
                'tolerance': 15
            },
            'peak': {
                'rotation': 45,  # Max rotation
                'back_angle': 165,
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate form"""
        feedback = {}
        targets = self.get_target_poses().get(phase, self.get_target_poses()['center'])
        
        # Rotation
        rotation = angles.get('rotation', 0)
        rotation_target = targets['rotation']
        
        if abs(rotation - rotation_target) <= 15:
            feedback['rotation'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=rotation,
                message="Good rotation"
            )
        else:
            feedback['rotation'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=rotation,
                message="Rotate more" if rotation < rotation_target else "Too much"
            )
        
        # Back should stay straight
        back_angle = angles.get('back_angle', 165)
        
        if back_angle >= 155:
            feedback['back'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=back_angle,
                message="Back straight"
            )
        else:
            feedback['back'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=back_angle,
                message="Keep back straight"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """Update rep counter"""
        rep_done = False
        warnings = []
        
        rotation = angle  # Using rotation value
        
        # Simplified state machine for rotations
        # One complete cycle: center → right → center → left → center = 1 rep
        
        if self.phase == "center" and rotation > 15:
            if self.rotation_side == "right":
                self.phase = "rotating_right"
                voice.speak("Rotate right", priority=False)
            else:
                self.phase = "rotating_left"
                voice.speak("Rotate left", priority=False)
        
        elif self.phase == "rotating_right" and rotation > 40:
            self.phase = "peak_right"
            voice.speak("Hold", priority=False)
        
        elif self.phase == "peak_right" and rotation < 35:
            self.phase = "returning_right"
        
        elif self.phase == "returning_right" and rotation < 10:
            self.phase = "center"
            self.rotation_side = "left"  # Switch to left
        
        elif self.phase == "rotating_left" and rotation > 40:
            self.phase = "peak_left"
            voice.speak("Hold", priority=False)
        
        elif self.phase == "peak_left" and rotation < 35:
            self.phase = "returning_left"
        
        elif self.phase == "returning_left" and rotation < 10:
            # Rep complete (one full cycle)
            rep_done = True
            self.phase = "center"
            self.rotation_side = "right"  # Reset to right
            
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
        
        # Simplified targets for rotation
        target_angles = {'rotation': 45, 'back_angle': 165, 'tolerance': 15}
        stability_data = self.stability_detector.get_stability_data()
        tempo_data = {'too_fast': False, 'too_slow': False}
        
        form_score = FormCalculator.calculate_form_score(
            angles=angles,
            target_angles=target_angles,
            stability=stability_data,
            tempo=tempo_data
        )
        
        self.current_rep_form_scores.append(form_score)
        return form_score
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        """Draw AR overlay"""
        if self.probation_mode:
            frame, _ = self.ar.draw_practice_mode(
                frame=frame,
                joints=joints_coords,
                current_angles=angles,
                target_angles={'rotation': 45, 'tolerance': 15},
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
    print("ROTATIONAL SWINGS V2 - Core rotation exercise")
    print("Rotate from core, not just arms")
    print("Ready to run!")