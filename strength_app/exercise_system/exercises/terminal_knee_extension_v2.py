"""
Terminal Knee Extension (TKE) V2 - Gold Standard for PFPS and Patellar Instability

Reference Video: https://www.youtube.com/watch?v=FLOy8aOw0FM
(Terminal Knee Extension - Physiotherapy Demonstration)

CHANGES FROM V1:
- Added form calculator integration for real-time scoring
- Integrated voice coach V2 with atomic sentences
- Added AR overlay V2 with Green/Yellow/Red in both modes
- Improved hold counting at lockout phase
- Added stability and tempo tracking
- Fixed practice mode logic (3 GREEN reps required)
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class TerminalKneeExtensionV2:
    """
    Terminal Knee Extension (TKE)
    
    Level: Foundation
    Category: Strength
    Target: Vastus Medialis Oblique (VMO), Quadriceps
    
    Reference Video: https://www.youtube.com/watch?v=FLOy8aOw0FM
    (Terminal Knee Extension Technique)
    
    Biomechanics:
    - Primary angle: Knee extension (hip → knee → ankle)
    - Starting: 150-165° (slight bend)
    - Target: 175-180° (near-complete extension, VMO activation)
    - Hold: 2 seconds at lockout
    - Critical: Last 30° of extension where VMO works hardest
    - Avoid hyperextension (>185°)
    
    Phases:
    1. Bent (starting position, slight knee bend)
    2. Extending (pushing toward lockout)
    3. Locked (full extension, VMO engaged)
    4. Holding (2-second hold at lockout)
    5. Returning (controlled return to bent)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=FLOy8aOw0FM"
    
    def __init__(self, target_reps=10):
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "bent"
        self.last_phase = "bent"
        
        # Practice mode (3 GREEN reps required)
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        
        # Hold tracking
        self.hold_start_time = None
        self.hold_duration_required = 2.0  # 2 seconds at lockout
        self.hold_announced_seconds = set()
        
        # Form tracking
        self.form_scores = []
        self.current_rep_form_scores = []
        
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
        Calculate knee angles for TKE
        
        CRITICAL: Track knee extension angle (hip-knee-ankle)
        
        Returns:
            Dict with angles and joint coordinates
        """
        # Extract joint coordinates
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        # Calculate knee angles
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        # Smooth angles
        left_knee = analyzer.smooth_angle(left_knee, 'left')
        right_knee = analyzer.smooth_angle(right_knee, 'right')
        
        # Average for bilateral symmetry
        avg_knee = (left_knee + right_knee) / 2
        
        # Check for hyperextension (dangerous)
        hyperextension = avg_knee > 185 or left_knee > 185 or right_knee > 185
        
        # Check symmetry
        knee_diff = abs(left_knee - right_knee)
        asymmetric = knee_diff > 15
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'knee_diff': knee_diff,
            'hyperextension': hyperextension,
            'asymmetric': asymmetric,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        """
        Define target angles for each phase
        
        Returns:
            Dict of target angles with tolerances
        """
        return {
            'bent': {
                'avg_knee': 155,      # Starting position (slight bend)
                'tolerance': 10
            },
            'extending': {
                'avg_knee': 170,      # Mid-extension
                'tolerance': 10
            },
            'locked': {
                'avg_knee': 178,      # Full lockout (near-straight)
                'tolerance': 5        # Strict tolerance for lockout
            },
            'holding': {
                'avg_knee': 178,      # Maintain lockout
                'tolerance': 5
            },
            'returning': {
                'avg_knee': 165,      # Controlled return
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
        
        # CRITICAL: Check for hyperextension first (dangerous)
        if angles.get('hyperextension', False):
            feedback['hyperextension'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=angles['avg_knee'],
                message="STOP - Hyperextension dangerous"
            )
            return feedback  # Return immediately, don't check other things
        
        # Check knee asymmetry
        if angles.get('asymmetric', False):
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=angles['knee_diff'],
                message="Keep knees even"
            )
        
        # Check knee extension
        knee_angle = angles.get('avg_knee', 0)
        knee_target = targets['avg_knee']
        knee_tolerance = targets['tolerance']
        
        knee_diff = abs(knee_angle - knee_target)
        
        if phase in ['locked', 'holding']:
            # Strict validation for lockout phase
            if knee_angle >= 175:
                feedback['extension'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=knee_angle,
                    message="Perfect lockout - VMO engaged"
                )
            elif knee_angle >= 170:
                feedback['extension'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=knee_angle,
                    message="Lock out completely"
                )
            else:
                feedback['extension'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=knee_angle,
                    message="Must achieve full extension"
                )
        
        elif phase == 'bent':
            # Starting position check
            if 150 <= knee_angle <= 165:
                feedback['position'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=knee_angle,
                    message="Good starting position"
                )
            elif knee_angle > 165:
                feedback['position'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=knee_angle,
                    message="Bend knees slightly"
                )
            elif knee_angle < 140:
                feedback['position'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=knee_angle,
                    message="Too bent - this is terminal extension"
                )
        
        elif phase == 'extending':
            # Progressive extension
            if knee_diff <= knee_tolerance:
                feedback['progress'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=knee_angle,
                    message="Good extension"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter with form scoring
        
        Args:
            angle: Current knee angle (avg_knee)
            feedback: Form validation feedback
            voice: Voice coach instance
        
        Returns:
            Tuple: (rep_done, current_phase, warnings)
        """
        rep_done = False
        warnings = []
        
        # Check for immediate stop condition (hyperextension)
        if 'hyperextension' in feedback:
            # Reset to bent position
            self.phase = "bent"
            self.hold_start_time = None
            voice.speak("Stop hyperextension", priority=True)
            return False, self.phase, warnings
        
        # Phase state machine
        if self.phase == "bent":
            # Ready position
            if 150 <= angle <= 165:
                # In correct starting position
                if self.tempo_detector.current_phase != 'bent':
                    self.tempo_detector.start_phase('bent')
            
            # Detect start of extension
            if angle > 165:
                self.phase = "extending"
                self.tempo_detector.start_phase('extending')
                voice.give_atomic_command('start_ascent', priority=False)  # "Push up"
        
        elif self.phase == "extending":
            # Extending toward lockout
            if angle >= 175:
                self.phase = "locked"
                self.tempo_detector.start_phase('locked')
                voice.speak("Lock it out", priority=False)
        
        elif self.phase == "locked":
            # Achieved lockout - start hold timer
            if angle >= 175:
                if self.hold_start_time is None:
                    self.hold_start_time = time.time()
                    self.hold_announced_seconds = set()
                    self.phase = "holding"
                    voice.speak("Hold tight", priority=False)
        
        elif self.phase == "holding":
            # Holding at lockout
            if angle < 170:
                # Lost lockout during hold
                warnings.append("Hold lost - maintain extension")
                self.phase = "bent"
                self.hold_start_time = None
                self.rejected_count += 1
                return False, self.phase, warnings
            
            # Count hold duration
            if self.hold_start_time:
                hold_elapsed = time.time() - self.hold_start_time
                current_second = int(hold_elapsed)
                
                # Announce each second
                if current_second > 0 and current_second not in self.hold_announced_seconds:
                    self.hold_announced_seconds.add(current_second)
                    voice.count_hold_seconds(current_second, int(self.hold_duration_required))
                
                # Check if hold complete
                if hold_elapsed >= self.hold_duration_required:
                    self.phase = "returning"
                    self.hold_start_time = None
                    voice.speak("Return slowly", priority=False)
        
        elif self.phase == "returning":
            # Returning to bent position
            if angle <= 165:
                # Rep completed
                rep_done = True
                self.phase = "bent"
                
                # Calculate form score for this rep
                form_score = self._calculate_rep_form_score()
                
                # Handle rep based on mode
                self._handle_rep_completion(form_score, voice)
        
        # Track phase change
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate average form score for completed rep"""
        if self.current_rep_form_scores:
            avg_form = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg_form
        return 85.0
    
    def _handle_rep_completion(self, form_score, voice):
        """Handle rep completion based on practice vs counted mode"""
        if self.probation_mode:
            # PRACTICE MODE: Only count if GREEN (≥85)
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
            # COUNTED MODE: All reps count
            self.rep_count += 1
            self.form_scores.append(form_score)
            voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """
        Calculate form score in real-time (called every frame)
        
        Args:
            angles: Current angles dict
            joints_coords: Current joint positions
        
        Returns:
            Float: Form score 0-100
        """
        # Update stability detector
        self.stability_detector.update(joints_coords)
        
        # Get target angles for current phase
        target_angles = self.get_target_poses()[self.phase]
        
        # Get stability data
        stability_data = self.stability_detector.get_stability_data()
        
        # Get tempo data
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
        """Draw AR overlay based on current mode"""
        if self.probation_mode:
            # PRACTICE MODE
            frame, position_matched = self.ar.draw_practice_mode(
                frame=frame,
                joints=joints_coords,
                current_angles=angles,
                target_angles=self.get_target_poses()[self.phase],
                form_score=form_score
            )
        else:
            # COUNTED MODE
            frame = self.ar.draw_counted_mode(
                frame=frame,
                joints=joints_coords,
                form_score=form_score
            )
        
        return frame
    
    def get_stats(self):
        """Get exercise statistics"""
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
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("TERMINAL KNEE EXTENSION V2")
    print("="*70)
    
    exercise = TerminalKneeExtensionV2(target_reps=10)
    
    print("\n✅ Features:")
    print("- Accurate knee extension tracking (hip-knee-ankle)")
    print("- 2-second hold counting at lockout")
    print("- Hyperextension detection (safety)")
    print("- Form calculator (real scores)")
    print("- Voice coach V2 (atomic sentences)")
    print("- AR overlay V2 (Green/Yellow/Red)")
    print("- Practice mode (3 GREEN reps)")
    
    print("\n📊 Target Poses:")
    for phase, targets in exercise.get_target_poses().items():
        print(f"  {phase}: {targets['avg_knee']}° (±{targets['tolerance']}°)")
    
    print("\n🎯 Ready to run!")
    print("="*70)