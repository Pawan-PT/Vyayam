"""
Single Leg Squats V2 - Unilateral Exercise Reference
This shows how to handle ONE-SIDED exercises properly

KEY DIFFERENCE FROM BILATERAL:
✅ Tracks LEFT side only, then RIGHT side only (not both at once)
✅ Uses UnilateralExerciseHandler to manage side switching
✅ Filters angles/joints for current side only
✅ Prompts user to reposition camera between sides
✅ Prevents false rep counting from detecting wrong side
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback
from ..core.unilateral_handler import UnilateralExerciseHandler, Side


class SingleLegSquatsV2:
    """
    Single Leg Squats - Unilateral strength exercise
    
    Level: Advanced
    Category: Strength
    Target: Quadriceps, glutes, balance
    
    Reference Video: https://www.youtube.com/watch?v=2C-uNgKwPLE
    (Single Leg Squat Tutorial - Proper Form)
    
    Biomechanics:
    - Primary angle: Knee flexion (SINGLE leg: hip → knee → ankle)
    - Standing: 170-180° (nearly straight)
    - Target depth: 90-110° (deep single-leg squat)
    - CRITICAL: Track ONE leg at a time (not both simultaneously)
    
    Unilateral Handling:
    1. User positions for LEFT side
    2. Camera sees left leg clearly
    3. Track ONLY left knee angle
    4. Complete 10 reps on left
    5. Prompt to switch sides
    6. User repositions for RIGHT side
    7. Track ONLY right knee angle
    8. Complete 10 reps on right
    
    Phases (per side):
    1. Standing (ready position on one leg)
    2. Descending (bending knee)
    3. Bottom (hold at target depth)
    4. Ascending (returning to standing)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=2C-uNgKwPLE"
    
    def __init__(self, target_reps=10, target_depth=100):
        # Exercise parameters
        self.target_reps_per_side = target_reps
        self.target_depth = target_depth
        
        # UNILATERAL HANDLER - manages left/right tracking
        self.unilateral = UnilateralExerciseHandler(
            total_reps=target_reps,
            exercise_name="Single Leg Squats"
        )
        
        # Phase tracking (per side)
        self.phase = "standing"
        self.last_phase = "standing"
        
        # Practice mode (3 GREEN reps required PER SIDE)
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        
        # Form tracking (current side only)
        self.current_rep_form_scores = []
        
        # Stability and tempo detectors
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        
        # Session start
        # Exercise announcement moved to runner
        self.voice.speak("Position for left side", priority=True)
    
    def calculate_angles(self, analyzer, results, shape):
        """
        Calculate angles for BOTH sides initially
        (Will be filtered by unilateral handler to use only current side)
        
        Returns:
            Dict with LEFT and RIGHT angles separately
        """
        # Left side
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        
        # Right side
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        # Shoulders for posture
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        # Calculate angles SEPARATELY for each side
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        left_back = analyzer.calculate_angle(ls, lh, lk)
        right_back = analyzer.calculate_angle(rs, rh, rk)
        
        # Smooth
        left_knee = analyzer.smooth_angle(left_knee, 'left')
        right_knee = analyzer.smooth_angle(right_knee, 'right')
        
        # Return BOTH sides (handler will filter)
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'left_back': left_back,
            'right_back': right_back,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }
    
    def get_current_side_angles(self, all_angles):
        """
        Filter angles to only use current side
        
        Args:
            all_angles: Dict with both left and right angles
        
        Returns:
            Dict with only current side (renamed to generic 'knee', 'back')
        """
        return self.unilateral.filter_angles_for_current_side(all_angles)
    
    def get_current_side_joints(self, all_joints):
        """
        Filter joints to only use current side
        
        Args:
            all_joints: Dict with both left and right joint positions
        
        Returns:
            Dict with only current side joints
        """
        return self.unilateral.filter_joints_for_current_side(all_joints)
    
    def get_target_poses(self):
        """
        Define target angles for each phase
        (Uses generic 'knee' instead of 'left_knee' or 'right_knee')
        """
        return {
            'standing': {
                'knee': 175,      # Nearly straight
                'back': 165,      # Upright
                'tolerance': 10
            },
            'descending': {
                'knee': 135,      # Midway down
                'back': 160,
                'tolerance': 15
            },
            'bottom': {
                'knee': self.target_depth,  # Target depth (90-110°)
                'back': 155,
                'tolerance': 10
            },
            'ascending': {
                'knee': 155,      # Coming up
                'back': 160,
                'tolerance': 15
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate form for current phase and current side"""
        feedback = {}
        targets = self.get_target_poses()[phase]
        
        # Check knee angle (current side only)
        knee_angle = angles.get('knee', 0)
        knee_target = targets['knee']
        knee_tolerance = targets['tolerance']
        
        knee_diff = abs(knee_angle - knee_target)
        
        if knee_diff <= knee_tolerance:
            feedback['knee'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=knee_angle,
                message="Good depth"
            )
        else:
            feedback['knee'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=knee_angle,
                message="Adjust depth"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter with form scoring
        (Tracks current side only)
        """
        rep_done = False
        warnings = []
        
        # Phase state machine (same as bilateral, but for current side only)
        if self.phase == "standing" and angle < 160:
            self.phase = "descending"
            self.tempo_detector.start_phase('descending')
            voice.give_atomic_command('start_descent', priority=False)
        
        elif self.phase == "descending" and angle < (self.target_depth + 15):
            self.phase = "bottom"
            self.tempo_detector.start_phase('bottom')
            voice.give_atomic_command('reached_bottom', priority=False)
        
        elif self.phase == "bottom" and angle > (self.target_depth + 20):
            self.phase = "ascending"
            self.tempo_detector.start_phase('ascending')
            voice.give_atomic_command('start_ascent', priority=False)
        
        elif self.phase == "ascending" and angle > 165:
            # Rep completed on current side
            rep_done = True
            self.phase = "standing"
            
            # Calculate form score
            form_score = self._calculate_rep_form_score()
            
            # Handle rep completion
            self._handle_rep_completion(form_score, voice)
        
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate form score for completed rep"""
        if self.current_rep_form_scores:
            avg_form = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg_form
        return 85.0
    
    def _handle_rep_completion(self, form_score, voice):
        """Handle rep completion for current side"""
        if self.probation_mode:
            # Practice mode: Only count if GREEN
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
                voice.provide_ar_feedback(form_score)
        
        else:
            # Counted mode: Increment for current side
            self.unilateral.increment_rep(form_score)
            
            current_reps = self.unilateral.get_reps_completed_current_side()
            voice.announce_rep(current_reps, self.target_reps_per_side, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """
        Calculate form score in real-time for CURRENT SIDE
        
        Args:
            angles: Current side angles (already filtered)
            joints_coords: Current side joints (already filtered)
        """
        # Update stability detector
        self.stability_detector.update(joints_coords)
        
        # Get target angles for this phase
        target_angles = self.get_target_poses()[self.phase]
        
        # Get stability and tempo data
        stability_data = self.stability_detector.get_stability_data()
        tempo_data = self.tempo_detector.check_tempo()
        
        # Calculate form score
        form_score = FormCalculator.calculate_form_score(
            angles=angles,
            target_angles=target_angles,
            stability=stability_data,
            tempo=tempo_data
        )
        
        # Track for averaging
        self.current_rep_form_scores.append(form_score)
        
        return form_score
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        """Draw AR overlay for current side"""
        # Add side indicator
        self.unilateral.draw_side_indicator(frame)
        
        # Draw AR based on mode
        if self.probation_mode:
            frame, position_matched = self.ar.draw_practice_mode(
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
    
    def check_side_switch(self):
        """
        Check if need to prompt user to switch sides
        
        Returns:
            True if should show switch prompt
        """
        return self.unilateral.needs_side_switch
    
    def handle_side_switch(self, frame):
        """
        Handle side switching UI
        
        Args:
            frame: Video frame
        
        Returns:
            (frame, should_continue)
        """
        # Draw switch prompt
        self.unilateral.draw_switch_prompt(frame)
        
        # Wait for user to press SPACE
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord(' '):
            # User acknowledged switch
            self.unilateral.acknowledge_switch()
            self.unilateral.switch_to_right_side()
            
            # Reset practice mode for right side
            self.probation_mode = True
            self.practice_reps_completed = 0
            
            # Voice prompt
            self.voice.speak("Position for right side", priority=True)
            
            return frame, True  # Continue
        
        return frame, False  # Keep showing prompt
    
    def check_positioning(self):
        """Check if user needs to position for current side"""
        return self.unilateral.awaiting_position
    
    def handle_positioning(self, frame):
        """
        Handle positioning UI
        
        Returns:
            (frame, ready)
        """
        # Draw positioning prompt
        self.unilateral.draw_positioning_prompt(frame)
        
        # Wait for user to press SPACE
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord(' '):
            self.unilateral.confirm_positioning()
            return frame, True  # Ready
        
        return frame, False  # Still positioning
    
    def get_stats(self):
        """Get complete statistics for both sides"""
        unilateral_stats = self.unilateral.get_stats()
        
        return {
            'exercise': 'Single Leg Squats',
            'left_reps': unilateral_stats['left_reps'],
            'right_reps': unilateral_stats['right_reps'],
            'left_avg_form': unilateral_stats['left_avg_form'],
            'right_avg_form': unilateral_stats['right_avg_form'],
            'total_reps': unilateral_stats['left_reps'] + unilateral_stats['right_reps'],
            'target_reps_per_side': self.target_reps_per_side,
            'complete': unilateral_stats['complete']
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("SINGLE LEG SQUATS V2 - Unilateral Exercise Reference")
    print("="*70)
    
    exercise = SingleLegSquatsV2(target_reps=10, target_depth=100)
    
    print("\n✅ Unilateral Features:")
    print("- Tracks LEFT side only, then RIGHT side only")
    print("- Uses UnilateralExerciseHandler")
    print("- Filters angles/joints per side")
    print("- Prompts user to reposition camera between sides")
    print("- Prevents false rep counting")
    
    print("\n🎯 Workflow:")
    print("1. User positions for LEFT side")
    print("2. Complete 10 reps on left (tracking left knee only)")
    print("3. Prompt to switch sides")
    print("4. User repositions for RIGHT side")
    print("5. Complete 10 reps on right (tracking right knee only)")
    print("6. Exercise complete!")
    
    print("\n📊 This prevents the common issue where:")
    print("❌ Both legs detected simultaneously")
    print("❌ Rep counting gets confused")
    print("❌ Wrong side angles affect form score")
    
    print("\n✅ With UnilateralExerciseHandler:")
    print("✓ Clean, accurate tracking")
    print("✓ Separate stats per side")
    print("✓ Professional UX")
    
    print("="*70)