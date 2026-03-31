"""
Push Ups V2 - Reference Implementation
Following the GOLD STANDARD structure from partial_squats_v2.py

COMPLETE INTEGRATION:
✅ Accurate angle detection (elbow flexion, back alignment)
✅ Form calculator (real scores, not 100%)
✅ Voice coach V2 (atomic sentences, encouragement)
✅ AR overlay V2 (Green/Yellow/Red in both modes)
✅ Practice mode (3 GREEN reps required)
✅ Rep counting (dynamic exercise)
✅ Stability and tempo tracking
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class PushUpsV2:
    """
    Push Ups - Upper body strengthening exercise
    
    Level: Foundation
    Category: Strength
    Target: Chest, triceps, shoulders, core
    
    Reference Video: https://www.youtube.com/watch?v=IODxDxX7oi4
    (Perfect Push-Up Form - Physiotherapy Demo)
    
    Biomechanics:
    - Primary angle: Elbow flexion (shoulder → elbow → wrist)
    - Up position: 165-175° (nearly straight arms)
    - Bottom position: 85-95° (chest near ground)
    - Back angle: Shoulder → hip → knee = 175-180° (straight body line)
    - Key checkpoints:
      * Hands shoulder-width apart
      * Body in straight line (no sagging hips or piking)
      * Full range of motion (chest to ground)
      * Controlled descent and ascent
    
    Phases:
    1. Up (starting position, arms extended)
    2. Descending (lowering body)
    3. Bottom (chest near ground)
    4. Ascending (pushing back up)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=IODxDxX7oi4"
    
    def __init__(self, target_reps=10):
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "up"
        self.last_phase = "up"
        
        # Practice mode (3 GREEN reps required)
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        
        # Form tracking
        self.form_scores = []  # Store form score for each rep
        self.current_rep_form_scores = []  # Form scores within current rep
        
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
        
        # Calculate elbow angles (primary tracking)
        left_elbow = analyzer.calculate_angle(ls, le, lw)
        right_elbow = analyzer.calculate_angle(rs, re, rw)
        
        # Calculate back angle (body alignment check)
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
            'up': {
                'avg_elbow': 170,      # Nearly straight arms
                'avg_back': 178,       # Straight body line
                'tolerance': 10
            },
            'descending': {
                'avg_elbow': 130,      # Midway down
                'avg_back': 175,       # Maintain straight body
                'tolerance': 15
            },
            'bottom': {
                'avg_elbow': 90,       # Chest near ground
                'avg_back': 175,       # Maintain straight body
                'tolerance': 10
            },
            'ascending': {
                'avg_elbow': 140,      # Coming back up
                'avg_back': 175,       # Maintain straight body
                'tolerance': 15
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
                message="Good range of motion"
            )
        elif elbow_diff <= elbow_tolerance * 1.5:
            feedback['elbow'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=elbow_angle,
                message="Adjust depth slightly"
            )
        else:
            feedback['elbow'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=elbow_angle,
                message="Depth incorrect"
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
        elif back_angle > 195:
            feedback['back'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=back_angle,
                message="Hips too high - lower body"
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
        Update rep counter with form scoring
        
        This is called every frame during exercise execution
        
        Args:
            angle: Current elbow angle (avg_elbow)
            feedback: Form validation feedback
            voice: Voice coach instance
        
        Returns:
            Tuple: (rep_done, current_phase, warnings)
        """
        rep_done = False
        warnings = []
        
        # Phase state machine for push-up movement
        if self.phase == "up" and angle < 155:
            # Started descending
            self.phase = "descending"
            self.tempo_detector.start_phase('descending')
            voice.give_atomic_command('start_descent', priority=False)
        
        elif self.phase == "descending" and angle < 105:
            # Reached bottom position
            self.phase = "bottom"
            self.tempo_detector.start_phase('bottom')
            voice.give_atomic_command('reached_bottom', priority=False)
        
        elif self.phase == "bottom" and angle > 110:
            # Started ascending
            self.phase = "ascending"
            self.tempo_detector.start_phase('ascending')
            voice.give_atomic_command('start_ascent', priority=False)
        
        elif self.phase == "ascending" and angle > 160:
            # Completed rep - back to up position
            rep_done = True
            self.phase = "up"
            
            # Calculate form score for this completed rep
            form_score = self._calculate_rep_form_score()
            
            # Handle rep based on mode (practice vs counted)
            self._handle_rep_completion(form_score, voice)
        
        # Track phase change for logging
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """
        Calculate form score for the completed rep
        
        Returns:
            Float: Form score 0-100
        """
        # Get average form score across this rep
        if self.current_rep_form_scores:
            avg_form = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []  # Reset for next rep
            return avg_form
        else:
            # Fallback if no scores tracked
            return 85.0  # Assume good form
    
    def _handle_rep_completion(self, form_score, voice):
        """
        Handle rep completion based on practice vs counted mode
        
        Args:
            form_score: Form score for the rep (0-100)
            voice: Voice coach instance
        """
        if self.probation_mode:
            # PRACTICE MODE: Only count if GREEN (form_score ≥ 85)
            if form_score >= 85:
                self.practice_reps_completed += 1
                voice.announce_practice_rep(
                    self.practice_reps_completed,
                    self.practice_reps_needed,
                    form_score
                )
                
                # Check if practice complete
                if self.practice_reps_completed >= self.practice_reps_needed:
                    self.probation_mode = False
                    voice.announce_phase_transition(from_practice_to_counted=True)
            else:
                # Form not good enough - rep doesn't count
                self.rejected_count += 1
                voice.provide_ar_feedback(form_score)
        
        else:
            # COUNTED MODE: All reps count, but track form
            self.rep_count += 1
            self.form_scores.append(form_score)
            voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
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
        
        # Get tempo data
        tempo_data = self.tempo_detector.check_tempo()
        
        # Calculate form score using FormCalculator
        form_score = FormCalculator.calculate_form_score(
            angles=angles,
            target_angles=target_angles,
            stability=stability_data,
            tempo=tempo_data
        )
        
        # Track this frame's score for averaging over the rep
        self.current_rep_form_scores.append(form_score)
        
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
        
        return {
            'reps_completed': self.rep_count,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


# ============================================================================
# USAGE EXAMPLE (for testing)
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("PUSH UPS V2 - Reference Implementation")
    print("="*70)
    
    exercise = PushUpsV2(target_reps=10)
    
    print("\n✅ Features Implemented:")
    print("- Accurate elbow angle detection (shoulder-elbow-wrist)")
    print("- Back alignment tracking (shoulder-hip-knee)")
    print("- Form calculator integration (real scores)")
    print("- Voice coach V2 (atomic sentences)")
    print("- AR overlay V2 (Green/Yellow/Red in both modes)")
    print("- Practice mode (3 GREEN reps required)")
    print("- Stability tracking")
    print("- Tempo tracking")
    print("- Rep counting with form scoring")
    
    print("\n📊 Target Poses:")
    for phase, targets in exercise.get_target_poses().items():
        print(f"  {phase}: Elbow {targets['avg_elbow']}°, Back {targets['avg_back']}° (±{targets['tolerance']}°)")
    
    print("\n🎯 Exercise ready to run!")
    print("Use with headless_runner_v2 or integrate into your system.")
    print("="*70)