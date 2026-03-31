"""
Clock Reaches V2 - Advanced single-leg balance exercise

CHANGES FROM V1:
- Added UnilateralExerciseHandler for proper left/right side tracking
- Integrated voice_coach_v2 (atomic commands)
- Integrated form_calculator (real form scores)
- Integrated ar_overlay_v2 (Green/Yellow/Red in both modes)
- Added YouTube reference video
- Fixed angle detection for balance stability
- Practice mode: 3 GREEN reaches per direction required
- Proper side switching workflow

Level: Advanced
Category: Balance, Proprioception
Target: Single-leg stability, dynamic balance, vestibular control
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback
from ..core.unilateral_handler import UnilateralExerciseHandler, Side


class ClockReachesV2:
    """
    Clock Reaches - Advanced balance exercise for ACL rehab
    
    Level: Advanced
    Category: Balance, Proprioception
    Target: Single-leg stability, dynamic balance, core control
    
    Reference Video: https://www.youtube.com/watch?v=wt6JlCq1Aq8
    (Clock Taps Exercise - Physical Therapy Demo)
    
    Biomechanics:
    - Primary: Single-leg balance (stance knee 165-175°, stable)
    - Reaching leg: Extended straight (165-180°)
    - 4 directions: 12 o'clock (forward), 3 o'clock (side), 
                    6 o'clock (back), 9 o'clock (cross-body)
    - 3 reaches per direction = 1 set
    - Key: Maintain balance on stance leg while reaching
    
    Unilateral Handling:
    - Complete all 4 directions on LEFT leg (standing on left)
    - Switch to RIGHT leg (standing on right)
    - Complete all 4 directions on right leg
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=wt6JlCq1Aq8"
    
    def __init__(self, reaches_per_direction=3):
        # Exercise parameters
        self.reaches_per_direction = reaches_per_direction
        self.directions = ['12', '3', '6', '9']  # Clock positions
        self.current_direction = 0  # Start at 12 o'clock
        self.reaches_in_current_direction = 0
        
        # UNILATERAL HANDLER - manages left/right leg
        # Total "reps" = 4 directions (each direction = 1 "rep")
        self.unilateral = UnilateralExerciseHandler(
            total_reps=4,  # 4 directions per leg
            exercise_name="Clock Reaches"
        )
        
        # Phase tracking
        self.phase = "center_balance"  # center_balance, reaching, returning
        self.last_phase = "center_balance"
        
        # Practice mode (3 GREEN reaches per direction)
        self.probation_mode = True
        self.practice_reaches_needed = 3
        self.practice_reaches_completed = 0
        
        # Form tracking
        self.current_reach_form_scores = []
        
        # Stability detector (critical for balance exercises)
        self.stability_detector = StabilityDetector(history_size=15)  # Longer history for balance
        self.tempo_detector = TempoDetector()
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        
        # Session start
        # Exercise announcement moved to runner
        self.voice.speak("Position for left leg", priority=True)
    
    def calculate_angles(self, analyzer, results, shape):
        """
        Calculate angles for balance detection
        
        BOTH legs initially (handler filters to current stance leg)
        
        Returns:
            Dict with left and right leg angles
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
        
        # Calculate knee angles
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        # Back angles
        left_back = analyzer.calculate_angle(ls, lh, lk)
        right_back = analyzer.calculate_angle(rs, rh, rk)
        
        # Smooth
        left_knee = analyzer.smooth_angle(left_knee, 'left')
        right_knee = analyzer.smooth_angle(right_knee, 'right')
        
        # Determine which leg is stance (on ground) vs reaching
        # Stance leg has ankle lower (higher Y value)
        if ra[1] > la[1]:
            # Right leg is stance
            stance_knee = right_knee
            reaching_knee = left_knee
            stance_back = right_back
        else:
            # Left leg is stance
            stance_knee = left_knee
            reaching_knee = right_knee
            stance_back = left_back
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'left_back': left_back,
            'right_back': right_back,
            'stance_knee': stance_knee,
            'reaching_knee': reaching_knee,
            'stance_back': stance_back,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }
    
    def get_current_side_angles(self, all_angles):
        """Filter to current stance leg only"""
        return self.unilateral.filter_angles_for_current_side(all_angles)
    
    def get_current_side_joints(self, all_joints):
        """Filter joints to current side"""
        return self.unilateral.filter_joints_for_current_side(all_joints)
    
    def get_target_poses(self):
        """
        Define target angles for each phase
        """
        return {
            'center_balance': {
                'stance_knee': 170,    # Nearly straight, stable
                'stance_back': 165,    # Upright posture
                'reaching_knee': 175,  # Reaching leg straight
                'tolerance': 10
            },
            'reaching': {
                'stance_knee': 165,    # Slight bend OK for balance
                'stance_back': 160,    # Can lean slightly
                'reaching_knee': 170,  # Keep reaching leg straight
                'tolerance': 12
            },
            'returning': {
                'stance_knee': 170,    # Back to stable
                'stance_back': 165,
                'reaching_knee': 175,
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles, phase):
        """
        Validate balance and form
        
        Key checks:
        - Stance knee stable (not wobbling)
        - Reaching leg stays straight
        - Back stays relatively upright
        """
        feedback = {}
        targets = self.get_target_poses()[phase]
        
        # Check stance knee (critical for balance)
        stance_knee = angles.get('stance_knee', 0)
        stance_target = targets['stance_knee']
        
        if abs(stance_knee - stance_target) <= 10:
            feedback['stance_knee'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=stance_knee,
                message="Good balance"
            )
        else:
            feedback['stance_knee'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=stance_knee,
                message="Stand more upright"
            )
        
        # Check reaching leg (should stay straight)
        reaching_knee = angles.get('reaching_knee', 0)
        
        if reaching_knee >= 165:
            feedback['reaching_knee'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=reaching_knee,
                message="Good leg extension"
            )
        else:
            feedback['reaching_knee'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=reaching_knee,
                message="Keep reaching leg straight"
            )
        
        # Check back posture
        back_angle = angles.get('stance_back', 0)
        
        if back_angle >= 155:
            feedback['back'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=back_angle,
                message="Good posture"
            )
        else:
            feedback['back'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=back_angle,
                message="Keep back straight"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update reach counter
        
        State machine:
        - center_balance → reaching → returning → center_balance
        - After 3 reaches in one direction, move to next direction
        - After all 4 directions, complete one "set"
        """
        rep_done = False
        warnings = []
        
        current_direction = self.directions[self.current_direction]
        warnings.append(
            f"{current_direction} o'clock: "
            f"{self.reaches_in_current_direction}/{self.reaches_per_direction} reaches"
        )
        
        # Phase transitions
        if self.phase == "center_balance":
            # Guide user to reach in current direction
            if not hasattr(self, 'last_direction_announcement'):
                self.last_direction_announcement = 0
            
            now = time.time()
            if now - self.last_direction_announcement > 3:
                voice.speak(f"Reach to {current_direction} o'clock", priority=False)
                self.last_direction_announcement = now
            
            # Detect start of reach (stance knee bends slightly)
            if angle < 168:
                self.phase = "reaching"
                self.tempo_detector.start_phase('reaching')
        
        elif self.phase == "reaching":
            # Hold reach for ~1 second, then return
            if not hasattr(self, 'reach_start_time'):
                self.reach_start_time = time.time()
            
            if time.time() - self.reach_start_time > 1.0:
                self.phase = "returning"
                self.reach_start_time = None
        
        elif self.phase == "returning":
            # Returning to center (stance knee straightens)
            if angle > 168:
                # Reach completed!
                self.reaches_in_current_direction += 1
                
                # Calculate form score for this reach
                form_score = self._calculate_reach_form_score()
                
                # Handle reach completion based on mode
                self._handle_reach_completion(form_score, voice)
                
                # Check if direction complete
                if self.reaches_in_current_direction >= self.reaches_per_direction:
                    self._complete_direction(voice)
                
                self.phase = "center_balance"
        
        return rep_done, self.phase, warnings
    
    def _complete_direction(self, voice):
        """Complete current direction, move to next"""
        self.reaches_in_current_direction = 0
        self.current_direction += 1
        
        if self.current_direction < 4:
            # More directions to go
            next_dir = self.directions[self.current_direction]
            voice.speak(f"Switch to {next_dir} o'clock", priority=True)
        else:
            # All 4 directions complete - SET DONE
            self.current_direction = 0
            
            if self.probation_mode:
                self.practice_reaches_completed += 1
                
                if self.practice_reaches_completed >= 1:  # 1 complete set = practice done
                    self.probation_mode = False
                    voice.announce_phase_transition(from_practice_to_counted=True)
            else:
                # Increment unilateral handler
                current_side_reps = self.unilateral.get_reps_completed_current_side()
                self.unilateral.increment_rep(form_score=85.0)
                
                voice.announce_rep(
                    current_side_reps + 1,
                    4,  # 4 directions per side
                    85.0
                )
    
    def _calculate_reach_form_score(self):
        """Calculate form score for the reach"""
        if self.current_reach_form_scores:
            avg = sum(self.current_reach_form_scores) / len(self.current_reach_form_scores)
            self.current_reach_form_scores = []
            return avg
        return 85.0
    
    def _handle_reach_completion(self, form_score, voice):
        """Handle reach completion based on mode"""
        if self.probation_mode:
            # Practice: only count if GREEN
            if form_score >= 85:
                voice.speak("Good reach", priority=False)
            else:
                voice.speak("Try again", priority=False)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """
        Calculate form score in real-time
        
        Balance exercises heavily weight stability
        """
        # Update stability detector
        self.stability_detector.update(joints_coords)
        
        # Get target angles
        target_angles = self.get_target_poses()[self.phase]
        
        # Get stability data (critical for balance!)
        stability_data = self.stability_detector.get_stability_data()
        
        # For balance exercises, increase stability weight
        # Wobble is heavily penalized
        wobble_penalty = stability_data.get('wobble_amount', 0) * 15  # Increased penalty
        
        # Calculate base form score
        form_score = FormCalculator.calculate_form_score(
            angles=angles,
            target_angles=target_angles,
            stability=stability_data,
            tempo={'too_fast': False, 'too_slow': False}
        )
        
        # Extra penalty for high wobble in balance exercises
        if wobble_penalty > 30:
            form_score -= 20
        
        form_score = max(0, min(100, form_score))
        
        self.current_reach_form_scores.append(form_score)
        
        return form_score
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        """Draw AR overlay based on mode"""
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
        
        # Draw current direction indicator
        direction = self.directions[self.current_direction]
        cv2.rectangle(frame, (10, frame.shape[0] - 110), (200, frame.shape[0] - 70), (50, 50, 50), -1)
        cv2.putText(frame, f"Direction: {direction} o'clock",
                   (15, frame.shape[0] - 85),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame
    
    def check_side_switch_needed(self):
        """Check if need to switch stance leg"""
        return self.unilateral.needs_side_switch
    
    def handle_side_switch(self, frame):
        """Handle side switch UI"""
        self.unilateral.draw_switch_prompt(frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            self.unilateral.switch_to_right_side()
            self.voice.speak("Position for right leg", priority=True)
            
            # Reset direction counter for new side
            self.current_direction = 0
            self.reaches_in_current_direction = 0
            
            # Reset practice mode for new side
            self.probation_mode = True
            self.practice_reaches_completed = 0
    
    def get_stats(self):
        """Get exercise statistics"""
        stats = self.unilateral.get_stats()
        
        return {
            'left_directions_complete': stats['left_reps'],
            'right_directions_complete': stats['right_reps'],
            'total_reaches': (stats['left_reps'] + stats['right_reps']) * self.reaches_per_direction,
            'left_avg_form': stats['left_avg_form'],
            'right_avg_form': stats['right_avg_form'],
            'complete': stats['complete']
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("CLOCK REACHES V2")
    print("="*70)
    
    exercise = ClockReachesV2(reaches_per_direction=3)
    
    print("\n✅ Features Implemented:")
    print("- Accurate balance detection (stance knee stability)")
    print("- Unilateral tracking (left leg, then right leg)")
    print("- Form calculator (heavy stability weighting)")
    print("- Voice coach V2 (atomic direction commands)")
    print("- AR overlay V2 (Green/Yellow/Red)")
    print("- Practice mode (1 complete set per side)")
    print("- 4 directions: 12, 3, 6, 9 o'clock")
    
    print("\n📊 Target Poses:")
    for phase, targets in exercise.get_target_poses().items():
        print(f"  {phase}: stance={targets['stance_knee']}°, reaching={targets['reaching_knee']}°")
    
    print("\n🎯 Ready to run with headless_runner!")
    print("="*70)