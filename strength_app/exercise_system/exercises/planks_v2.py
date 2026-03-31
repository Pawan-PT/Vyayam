"""
Planks V2 - Reference Implementation
Following the GOLD STANDARD structure from partial_squats_v2.py

COMPLETE INTEGRATION:
✅ Accurate angle detection (elbow angle, back straightness)
✅ Form calculator (real scores, not 100%)
✅ Voice coach V2 (atomic sentences, encouragement)
✅ AR overlay V2 (Green/Yellow/Red in both modes)
✅ Practice mode (3 GREEN holds required)
✅ Hold counting (critical for static exercise)
✅ Stability and tempo tracking
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class PlanksV2:
    """
    Planks - Core strengthening static hold exercise
    
    Level: Advanced
    Category: Strength
    Target: Core, shoulders, glutes
    
    Reference Video: https://www.youtube.com/watch?v=ASdvN_XEl_c
    (Perfect Plank Form - Physiotherapy Demo)
    
    Biomechanics:
    - Primary angle: Elbow angle (shoulder → elbow → wrist) = 90°
    - Back angle: Shoulder → hip → knee = 175-180° (straight line)
    - Hip angle: Should not sag (maintain neutral spine)
    - Key checkpoints:
      * Elbows directly under shoulders
      * Body in straight line (no sagging or piking)
      * Core engaged throughout hold
      * Neutral neck position
    
    Phases:
    1. Setup (getting into position)
    2. Holding (maintaining plank position)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=ASdvN_XEl_c"
    
    def __init__(self, target_holds=3, target_hold_time=30):
        # Exercise parameters
        self.target_holds = target_holds
        self.target_hold_time = target_hold_time  # seconds
        self.hold_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "setup"
        self.last_phase = "setup"
        
        # Hold timing
        self.hold_start_time = None
        self.current_hold_time = 0
        self.hold_times = []  # Store duration of each successful hold
        
        # Practice mode (3 GREEN holds required)
        self.probation_mode = True
        self.practice_holds_needed = 3
        self.practice_holds_completed = 0
        
        # Form tracking
        self.form_scores = []  # Store form score for each hold
        self.current_hold_form_scores = []  # Form scores within current hold
        
        # Stability and tempo detectors
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        
        # Session start
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """
        Calculate elbow angles, back angle, and joint positions
        
        CRITICAL: This tracks the CORRECT biomechanical angles
        - Elbow angle = shoulder → elbow → wrist angle
        - Back angle = shoulder → hip → knee (should be straight ~180°)
        - Hip sag detection
        
        Returns:
            Dict with angles and joint coordinates
        """
        # Extract joint coordinates
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        le = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ELBOW, shape)
        lw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_WRIST, shape)
        
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        re = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ELBOW, shape)
        rw = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_WRIST, shape)
        
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        
        # Calculate elbow angles (should be ~90°)
        left_elbow = analyzer.calculate_angle(ls, le, lw)
        right_elbow = analyzer.calculate_angle(rs, re, rw)
        
        # Calculate back angle (should be ~180° - straight line)
        left_back = analyzer.calculate_angle(ls, lh, lk)
        right_back = analyzer.calculate_angle(rs, rh, rk)
        
        # Smooth angles to reduce jitter
        left_elbow = analyzer.smooth_angle(left_elbow, 'left_elbow')
        right_elbow = analyzer.smooth_angle(right_elbow, 'right_elbow')
        
        # Average for bilateral symmetry
        avg_elbow = (left_elbow + right_elbow) / 2
        avg_back = (left_back + right_back) / 2
        
        return {
            'left_elbow': left_elbow,
            'right_elbow': right_elbow,
            'avg_elbow': avg_elbow,
            'avg_back': avg_back,
            'joints_coords': {
                'ls': ls, 'le': le, 'lw': lw,
                'rs': rs, 're': re, 'rw': rw,
                'lh': lh, 'rh': rh,
                'lk': lk, 'rk': rk
            }
        }
    
    def get_target_poses(self):
        """
        Define target angles for each phase
        
        Returns:
            Dict of target angles with tolerances
        """
        return {
            'setup': {
                'avg_elbow': 90,      # Elbows at 90°
                'avg_back': 175,      # Nearly straight
                'tolerance': 15
            },
            'holding': {
                'avg_elbow': 90,      # Maintain 90°
                'avg_back': 178,      # Straight body line
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles, phase):
        """
        Validate form for current phase
        
        Args:
            angles: Current measured angles
            phase: Current exercise phase
        
        Returns:
            Dict of JointFeedback for each joint
        """
        feedback = {}
        targets = self.get_target_poses()[phase]
        
        # Check elbow angle
        elbow_angle = angles.get('avg_elbow', 0)
        elbow_target = targets['avg_elbow']
        elbow_tolerance = targets['tolerance']
        
        elbow_diff = abs(elbow_angle - elbow_target)
        
        if elbow_diff <= elbow_tolerance:
            feedback['elbow'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=elbow_angle,
                message="Good elbow position"
            )
        elif elbow_diff <= elbow_tolerance * 1.5:
            feedback['elbow'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=elbow_angle,
                message="Adjust elbow angle"
            )
        else:
            feedback['elbow'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=elbow_angle,
                message="Elbow position incorrect"
            )
        
        # Check back angle (body alignment)
        back_angle = angles.get('avg_back', 0)
        back_target = targets.get('avg_back', 178)
        
        if back_angle < 160:
            feedback['back'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=back_angle,
                message="Hips sagging - engage core"
            )
        elif back_angle > 190:
            feedback['back'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=back_angle,
                message="Hips too high - lower slightly"
            )
        else:
            feedback['back'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=back_angle,
                message="Body aligned"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update hold counter with form scoring
        
        For planks, we track HOLDS instead of REPS
        
        Args:
            angle: Current elbow angle (avg_elbow)
            feedback: Form validation feedback
            voice: Voice coach instance
        
        Returns:
            Tuple: (hold_done, current_phase, warnings)
        """
        hold_done = False
        warnings = []
        
        # Check if form is good (all feedback CORRECT or NEEDS_ADJUSTMENT)
        has_critical_error = any(
            f.status == FormStatus.INCORRECT 
            for f in feedback.values()
        )
        
        # Phase state machine for plank hold
        if self.phase == "setup":
            # Check if in proper plank position
            if not has_critical_error and 85 <= angle <= 95:
                # Good position - start holding
                self.phase = "holding"
                self.hold_start_time = time.time()
                self.tempo_detector.start_phase('holding')
                voice.give_atomic_command('start_hold', priority=False)
        
        elif self.phase == "holding":
            if has_critical_error:
                # Form broke - reset hold
                self.phase = "setup"
                self.hold_start_time = None
                self.rejected_count += 1
                voice.give_atomic_command('form_break', priority=True)
                warnings.append("Form broke - hold reset")
            else:
                # Update hold time
                self.current_hold_time = time.time() - self.hold_start_time
                
                # Check if target hold time reached
                if self.current_hold_time >= self.target_hold_time:
                    # Completed hold
                    hold_done = True
                    self.phase = "setup"
                    
                    # Calculate form score for this completed hold
                    form_score = self._calculate_hold_form_score()
                    
                    # Handle hold based on mode (practice vs counted)
                    self._handle_hold_completion(form_score, voice)
                    
                    # Reset hold timer
                    self.hold_start_time = None
                    self.current_hold_time = 0
        
        # Track phase change for logging
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return hold_done, self.phase, warnings
    
    def _calculate_hold_form_score(self):
        """
        Calculate form score for the completed hold
        
        Returns:
            Float: Form score 0-100
        """
        # Get average form score across this hold
        if self.current_hold_form_scores:
            avg_form = sum(self.current_hold_form_scores) / len(self.current_hold_form_scores)
            self.current_hold_form_scores = []  # Reset for next hold
            return avg_form
        else:
            # Fallback if no scores tracked
            return 85.0  # Assume good form
    
    def _handle_hold_completion(self, form_score, voice):
        """
        Handle hold completion based on practice vs counted mode
        
        Args:
            form_score: Form score for the hold (0-100)
            voice: Voice coach instance
        """
        if self.probation_mode:
            # PRACTICE MODE: Only count if GREEN (form_score ≥ 85)
            if form_score >= 85:
                self.practice_holds_completed += 1
                voice.announce_practice_rep(
                    self.practice_holds_completed,
                    self.practice_holds_needed,
                    form_score
                )
                
                # Check if practice complete
                if self.practice_holds_completed >= self.practice_holds_needed:
                    self.probation_mode = False
                    voice.announce_phase_transition(from_practice_to_counted=True)
            else:
                # Form not good enough - hold doesn't count
                self.rejected_count += 1
                voice.provide_ar_feedback(form_score)
        
        else:
            # COUNTED MODE: All holds count, but track form
            self.hold_count += 1
            self.form_scores.append(form_score)
            self.hold_times.append(self.current_hold_time)
            voice.announce_rep(self.hold_count, self.target_holds, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """
        Calculate form score in real-time (called every frame)
        
        This is the KEY to getting real scores instead of stuck-at-100%
        
        Args:
            angles: Current angles dict
            joints_coords: Current joint positions
        
        Returns:
            Float: Form score 0-100
        """
        # Update stability detector with current joint positions
        self.stability_detector.update(joints_coords)
        
        # Get current target angles for this phase
        target_angles = self.get_target_poses()[self.phase]
        
        # Get stability data
        stability_data = self.stability_detector.get_stability_data()
        
        # Get tempo data (for static holds, this checks steadiness)
        tempo_data = self.tempo_detector.check_tempo()
        
        # Calculate form score using FormCalculator
        form_score = FormCalculator.calculate_form_score(
            angles=angles,
            target_angles=target_angles,
            stability=stability_data,
            tempo=tempo_data
        )
        
        # Track this frame's score for averaging over the hold
        self.current_hold_form_scores.append(form_score)
        
        return form_score
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        """
        Draw AR overlay based on current mode
        
        Args:
            frame: Video frame
            angles: Current angles
            joints_coords: Joint positions
            form_score: Current form score
        
        Returns:
            Annotated frame
        """
        if self.probation_mode:
            # PRACTICE MODE: Show target overlay + arrows + form-colored skeleton
            frame, position_matched = self.ar.draw_practice_mode(
                frame=frame,
                joints=joints_coords,
                current_angles=angles,
                target_angles=self.get_target_poses()[self.phase],
                form_score=form_score
            )
        else:
            # COUNTED MODE: Just form-colored skeleton + score indicator
            frame = self.ar.draw_counted_mode(
                frame=frame,
                joints=joints_coords,
                form_score=form_score
            )
        
        # Add hold timer overlay if holding
        if self.phase == "holding":
            elapsed = int(self.current_hold_time)
            target = int(self.target_hold_time)
            timer_text = f"HOLD: {elapsed}s / {target}s"
            
            cv2.rectangle(frame, (10, 10), (300, 50), (40, 40, 40), -1)
            cv2.putText(frame, timer_text, (20, 38),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        return frame
    
    def get_stats(self):
        """
        Get exercise statistics
        
        Returns:
            Dict with session stats
        """
        avg_form_score = (
            sum(self.form_scores) / len(self.form_scores) 
            if self.form_scores else 0
        )
        
        avg_hold_time = (
            sum(self.hold_times) / len(self.hold_times)
            if self.hold_times else 0
        )
        
        return {
            'holds_completed': self.hold_count,
            'practice_holds': self.practice_holds_completed,
            'rejected_holds': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'avg_hold_time': round(avg_hold_time, 1),
            'form_scores': self.form_scores,
            'hold_times': self.hold_times,
            'target_holds': self.target_holds,
            'target_hold_time': self.target_hold_time
        }


# ============================================================================
# USAGE EXAMPLE (for testing)
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("PLANKS V2 - Reference Implementation")
    print("="*70)
    
    exercise = PlanksV2(target_holds=3, target_hold_time=30)
    
    print("\n✅ Features Implemented:")
    print("- Accurate elbow angle detection (shoulder-elbow-wrist)")
    print("- Back alignment tracking (shoulder-hip-knee)")
    print("- Form calculator integration (real scores)")
    print("- Voice coach V2 (atomic sentences)")
    print("- AR overlay V2 (Green/Yellow/Red in both modes)")
    print("- Practice mode (3 GREEN holds required)")
    print("- Hold counting (static exercise)")
    print("- Stability tracking")
    print("- Form break detection")
    
    print("\n📊 Target Poses:")
    for phase, targets in exercise.get_target_poses().items():
        print(f"  {phase}: Elbow {targets['avg_elbow']}°, Back {targets['avg_back']}° (±{targets['tolerance']}°)")
    
    print("\n🎯 Exercise ready to run!")
    print("Use with headless_runner_v2 or integrate into your system.")
    print("="*70)