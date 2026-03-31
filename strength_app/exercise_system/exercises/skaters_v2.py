"""
Skaters V2 - Lateral Power Exercise

Reference Video: https://www.youtube.com/watch?v=qVek72z3F1U
(Skater Jumps - Proper Technique)

NEW EXERCISE - Created for VYAYAM cardio module
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class SkatersV2:
    """
    Skaters - Lateral plyometric exercise
    
    Level: Intermediate
    Category: Cardio/Power
    Target: Lateral power, single-leg stability, cardiovascular endurance
    
    Reference Video: https://www.youtube.com/watch?v=qVek72z3F1U
    (Skater Jumps Proper Technique)
    
    Biomechanics:
    - Single-leg lateral jumps (like speed skating)
    - Push off from one leg, land on opposite
    - Trailing leg swings behind for balance
    - Slight forward lean
    
    Movement Detection:
    - Weight shift (left leg vs right leg weight-bearing)
    - Lateral displacement
    - Single-leg balance
    - Trailing leg position
    
    Phases (per jump):
    1. Left stance (balanced on left)
    2. Jumping right (in air)
    3. Right stance (balanced on right)
    4. Jumping left (returning)
    
    Rep = one complete cycle (left → right → left)
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=qVek72z3F1U"
    
    def __init__(self, target_reps=15):  # Fewer reps - more intense
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "left_stance"
        self.last_phase = "left_stance"
        
        # Position tracking
        self.center_x = None
        self.left_landings = 0
        self.right_landings = 0
        
        # Practice mode
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
        Calculate angles for skaters
        
        Key measurements:
        - Hip position (lateral displacement)
        - Weight-bearing leg (ankle-knee alignment)
        - Trailing leg position
        """
        # Extract joints
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        # Hip center for position tracking
        hip_center_x = (lh[0] + rh[0]) / 2
        
        # Calibrate center
        if self.center_x is None:
            self.center_x = hip_center_x
        
        displacement = hip_center_x - self.center_x
        
        # Determine weight-bearing leg based on ankle-knee vertical alignment
        # Weight-bearing leg has ankle more directly under knee
        left_alignment = abs(la[0] - lk[0])
        right_alignment = abs(ra[0] - rk[0])
        
        # Also check which ankle is lower (on ground)
        left_lower = la[1] > ra[1]  # Higher Y = lower on screen
        right_lower = ra[1] > la[1]
        
        if left_alignment < right_alignment and left_lower:
            weight_bearing = "left"
        elif right_alignment < left_alignment and right_lower:
            weight_bearing = "right"
        else:
            weight_bearing = "transitioning"
        
        # Knee angles
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        return {
            'hip_center_x': hip_center_x,
            'displacement': displacement,
            'weight_bearing': weight_bearing,
            'left_knee': left_knee,
            'right_knee': right_knee,
            'left_alignment': left_alignment,
            'right_alignment': right_alignment,
            'joints_coords': {
                'lh': lh, 'rh': rh, 'lk': lk, 'rk': rk,
                'la': la, 'ra': ra
            }
        }
    
    def get_target_poses(self):
        """Target positions for skaters"""
        return {
            'left_stance': {
                'displacement': -60,
                'weight_bearing': 'left',
                'left_knee': 155,      # Slightly bent
                'tolerance': 20
            },
            'jumping_right': {
                'displacement': 0,
                'tolerance': 40
            },
            'right_stance': {
                'displacement': 60,
                'weight_bearing': 'right',
                'right_knee': 155,
                'tolerance': 20
            },
            'jumping_left': {
                'displacement': 0,
                'tolerance': 40
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate skater form"""
        feedback = {}
        
        weight_bearing = angles.get('weight_bearing', '')
        
        # Single-leg stance validation
        if phase == 'left_stance':
            if weight_bearing == 'left':
                feedback['stance'] = JointFeedback(
                    FormStatus.CORRECT, 0, "Good balance"
                )
            else:
                feedback['stance'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, 0, "Balance on left leg"
                )
        
        elif phase == 'right_stance':
            if weight_bearing == 'right':
                feedback['stance'] = JointFeedback(
                    FormStatus.CORRECT, 0, "Good balance"
                )
            else:
                feedback['stance'] = JointFeedback(
                    FormStatus.NEEDS_ADJUSTMENT, 0, "Balance on right leg"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter for skaters
        
        Rep = complete cycle (left → right → left)
        """
        rep_done = False
        warnings = []
        
        weight_bearing = angle.get('weight_bearing', '')
        displacement = angle.get('displacement', 0)
        
        # State machine
        if self.phase == "left_stance":
            # Push off to right
            if weight_bearing == "transitioning" or (displacement > 20 and weight_bearing == "right"):
                self.phase = "jumping_right"
                self.tempo_detector.start_phase('jumping_right')
        
        elif self.phase == "jumping_right":
            # Landed on right
            if weight_bearing == "right" and displacement > 30:
                self.phase = "right_stance"
                self.right_landings += 1
        
        elif self.phase == "right_stance":
            # Push off to left
            if weight_bearing == "transitioning" or (displacement < -20 and weight_bearing == "left"):
                self.phase = "jumping_left"
        
        elif self.phase == "jumping_left":
            # Completed one cycle
            if weight_bearing == "left" and displacement < -30:
                rep_done = True
                self.phase = "left_stance"
                self.left_landings += 1
                
                # Calculate form score
                form_score = self._calculate_rep_form_score()
                self._handle_rep_completion(form_score, voice)
        
        # Track phase changes
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate form score for completed cycle"""
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
        else:
            self.rep_count += 1
            self.form_scores.append(form_score)
            
            # Announce every 3 reps (more intense exercise)
            if self.rep_count % 3 == 0:
                voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score"""
        self.stability_detector.update(joints_coords)
        
        weight_bearing = angles.get('weight_bearing', '')
        displacement = angles.get('displacement', 0)
        
        # Score based on single-leg balance and position
        if self.phase == 'left_stance' and weight_bearing == 'left' and displacement < -40:
            form_score = 95.0
        elif self.phase == 'right_stance' and weight_bearing == 'right' and displacement > 40:
            form_score = 95.0
        elif self.phase in ['left_stance', 'right_stance']:
            form_score = 80.0  # In stance but not perfect
        else:
            form_score = 85.0  # Transitioning
        
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
            'left_landings': self.left_landings,
            'right_landings': self.right_landings,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("="*70)
    print("SKATERS V2 - Lateral Power Exercise")
    print("="*70)
    print("\n✅ Single-leg balance tracking")
    print("✅ Lateral jump detection")
    print("✅ Weight-bearing leg identification")
    print("✅ Plyometric movement support")
    print("="*70)
