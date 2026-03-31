"""
Jumping Jacks V2 - Classic Cardio Exercise

Reference Video: https://www.youtube.com/watch?v=UpH7rm0cYbM
(Jumping Jacks - Proper Form and Technique)

NEW EXERCISE - Created for VYAYAM cardio module
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class JumpingJacksV2:
    """
    Jumping Jacks - Cardio conditioning
    
    Level: Foundation
    Category: Cardio
    Target: Cardiovascular endurance, full body coordination
    
    Reference Video: https://www.youtube.com/watch?v=UpH7rm0cYbM
    (Jumping Jacks Proper Technique)
    
    Biomechanics:
    - Starting position: Feet together, arms at sides
    - Jump: Feet apart (wider than shoulders), arms overhead
    - Return: Jump back to starting position
    - One complete cycle = 1 rep
    
    Movement Detection:
    - Feet separation (hip-width vs shoulder-width+)
    - Arm position (down at sides vs overhead)
    - Fast movement (cardio pace)
    
    Phases:
    1. Together (feet together, arms down)
    2. Jumping out (transitioning)
    3. Apart (feet wide, arms up)
    4. Jumping in (returning)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=UpH7rm0cYbM"
    
    def __init__(self, target_reps=20):
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "together"
        self.last_phase = "together"
        
        # Practice mode (3 reps for cardio)
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        
        # Form tracking
        self.form_scores = []
        self.current_rep_form_scores = []
        
        # Detectors
        self.stability_detector = StabilityDetector()
        self.tempo_detector = TempoDetector()
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """
        Calculate positions for jumping jacks
        
        Key measurements:
        - Feet separation (ankle distance)
        - Arm height (wrist vs shoulder position)
        """
        # Extract joints
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        lw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_WRIST, shape)
        rw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_WRIST, shape)
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        # Feet separation (horizontal distance)
        feet_distance = abs(la[0] - ra[0])
        
        # Classify feet position
        if feet_distance < 50:
            feet_position = "together"
        elif feet_distance < 150:
            feet_position = "transitioning"
        else:
            feet_position = "apart"
        
        # Arm height (average wrist height vs shoulder height)
        avg_wrist_y = (lw[1] + rw[1]) / 2
        avg_shoulder_y = (ls[1] + rs[1]) / 2
        
        # Arms raised (wrists above shoulders)
        arms_raised = avg_wrist_y < avg_shoulder_y
        
        # Arm separation (hands coming together overhead)
        arm_distance = abs(lw[0] - rw[0])
        
        return {
            'feet_distance': feet_distance,
            'feet_position': feet_position,
            'arms_raised': arms_raised,
            'arm_distance': arm_distance,
            'avg_wrist_y': avg_wrist_y,
            'avg_shoulder_y': avg_shoulder_y,
            'joints_coords': {
                'ls': ls, 'rs': rs, 'lw': lw, 'rw': rw,
                'lh': lh, 'rh': rh, 'la': la, 'ra': ra
            }
        }
    
    def get_target_poses(self):
        """Target positions for jumping jacks"""
        return {
            'together': {
                'feet_distance': 40,      # Feet together
                'arms_raised': False,     # Arms down
                'tolerance': 20
            },
            'jumping_out': {
                'feet_distance': 100,     # Mid-jump
                'tolerance': 30
            },
            'apart': {
                'feet_distance': 160,     # Feet wide
                'arms_raised': True,      # Arms overhead
                'tolerance': 20
            },
            'jumping_in': {
                'feet_distance': 100,     # Returning
                'tolerance': 30
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate jumping jack form"""
        feedback = {}
        
        feet_pos = angles.get('feet_position', '')
        arms_raised = angles.get('arms_raised', False)
        
        # Together position validation
        if phase == 'together':
            if feet_pos == 'together' and not arms_raised:
                feedback['position'] = JointFeedback(
                    FormStatus.CORRECT, 0, "Good starting position"
                )
            elif feet_pos != 'together':
                feedback['position'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, 0, "Bring feet together"
                )
        
        # Apart position validation
        elif phase == 'apart':
            if feet_pos == 'apart' and arms_raised:
                feedback['position'] = JointFeedback(
                    FormStatus.CORRECT, 0, "Perfect jack!"
                )
            elif feet_pos != 'apart':
                feedback['position'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, 0, "Jump wider"
                )
            elif not arms_raised:
                feedback['arms'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, 0, "Raise arms overhead"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter for jumping jacks
        
        Rep = complete cycle (together → apart → together)
        """
        rep_done = False
        warnings = []
        
        feet_pos = angle  # Using feet_position as primary metric
        
        # Fast state machine for cardio exercise
        if self.phase == "together":
            # Wait for jump out
            if feet_pos == "transitioning" or feet_pos == "apart":
                self.phase = "jumping_out"
                self.tempo_detector.start_phase('jumping_out')
        
        elif self.phase == "jumping_out":
            # Reached apart position
            if feet_pos == "apart":
                self.phase = "apart"
                # Quick validation - arms should be up
                # No voice here - too fast for cardio
        
        elif self.phase == "apart":
            # Wait for jump back
            if feet_pos == "transitioning" or feet_pos == "together":
                self.phase = "jumping_in"
        
        elif self.phase == "jumping_in":
            # Completed one rep
            if feet_pos == "together":
                rep_done = True
                self.phase = "together"
                
                # Calculate form score
                form_score = self._calculate_rep_form_score()
                self._handle_rep_completion(form_score, voice)
        
        # Track phase changes
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate form score for completed rep"""
        if self.current_rep_form_scores:
            avg = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg
        return 85.0  # Default good form for cardio
    
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
                # For cardio, be less strict - keep going
        else:
            self.rep_count += 1
            self.form_scores.append(form_score)
            
            # Only announce every 5 reps for cardio (too fast otherwise)
            if self.rep_count % 5 == 0:
                voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score"""
        self.stability_detector.update(joints_coords)
        
        target_angles = self.get_target_poses()[self.phase]
        stability_data = self.stability_detector.get_stability_data()
        
        # For cardio, tempo is less important (fast is OK)
        tempo_data = {'too_fast': False, 'too_slow': False}
        
        # Simple form scoring for cardio (mostly position-based)
        feet_pos = angles.get('feet_position', '')
        arms_raised = angles.get('arms_raised', False)
        
        if self.phase == 'together' and feet_pos == 'together' and not arms_raised:
            form_score = 95.0
        elif self.phase == 'apart' and feet_pos == 'apart' and arms_raised:
            form_score = 95.0
        elif self.phase in ['jumping_out', 'jumping_in']:
            form_score = 85.0  # Transition phases
        else:
            form_score = 70.0  # Not in target position
        
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
        avg_form_score = (
            sum(self.form_scores) / len(self.form_scores)
            if self.form_scores else 0
        )
        
        return {
            'reps_completed': self.rep_count,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("="*70)
    print("JUMPING JACKS V2 - Cardio Exercise")
    print("="*70)
    print("\n✅ Fast movement detection")
    print("✅ Feet separation tracking")
    print("✅ Arm overhead detection")
    print("✅ Rep counting for cardio")
    print("="*70)
