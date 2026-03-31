"""
Lunges V2 - Forward Lunges with Enhanced Tracking

IMPROVEMENTS FROM V1:
✅ FormCalculator integration for real-time scoring (not stuck at 100%)
✅ VoiceCoachV2 with atomic commands ("Bend knees", "Push up")
✅ Accurate angle detection (front knee, back knee, posture)
✅ Practice mode (3 GREEN reps required before counting)
✅ AR overlay V2 support (Green/Yellow/Red in both modes)
✅ Better phase detection and form validation
✅ Side positioning guidance (camera setup)
✅ Improved rep state machine

CHANGELOG:
- Added FormCalculator for dynamic form scoring
- Integrated VoiceCoachV2 for smooth audio guidance
- Fixed angle calculations (both knees + back posture)
- Added practice mode with 3 GREEN rep requirement
- Enhanced form validation with specific feedback
- Added AR overlay targets for each phase
- Improved phase transitions and timing
- Added camera positioning guidance at start
- Fixed neutral stance return guidance

TEST NOTES:
- Verify front/back knee detection works correctly
- Ensure back posture angle is accurate (not too sensitive)
- Test practice mode - should require good form to advance
- Check form score varies realistically (not stuck at 100%)
- Verify voice commands are atomic and non-interrupting
- Test AR overlay shows correct skeleton coloring
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class LungesV2:
    """
    Forward Lunges - Functional closed-chain strengthening
    
    Level: Intermediate-Advanced
    Category: Strength
    Target: Quadriceps, gluteus maximus, hamstrings
    
    Reference Video: https://www.youtube.com/watch?v=QOVaHwm-Q6U
    (Forward Lunges - Proper Technique)
    
    Biomechanics:
    - Front knee angle: hip → knee → ankle (target 90°)
    - Back knee angle: hip → knee → ankle (target 90°)
    - Back posture: shoulder → hip alignment (>155°)
    - Key checkpoints:
      * Front knee behind toes
      * Back knee hovers above ground
      * Upright torso (no excessive forward lean)
      * Controlled descent and ascent
    
    Phases:
    1. Standing (neutral stance, feet together)
    2. Lunge down (step forward + descend)
    3. Bottom (both knees at 90°, hold briefly)
    4. Lunge up (return to standing)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=QOVaHwm-Q6U"
    
    def __init__(self, target_reps=10):
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "standing"
        self.last_phase = "standing"
        
        # Practice mode (3 GREEN reps required)
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        
        # Form tracking
        self.form_scores = []
        self.current_rep_form_scores = []
        
        # Stability and tempo detectors
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        
        # Camera guidance flag
        self.camera_guidance_given = False
        
        # Session start
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """
        Calculate knee and back angles for lunge
        
        CRITICAL: Detect which leg is forward vs back
        - Front leg: lower knee Y coordinate (higher on screen)
        - Back leg: higher knee Y coordinate (lower on screen)
        
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
        
        # Calculate hip angles
        left_hip = analyzer.calculate_angle(ls, lh, lk)
        right_hip = analyzer.calculate_angle(rs, rh, rk)
        
        # Smooth angles
        left_knee = analyzer.smooth_angle(left_knee, 'left')
        right_knee = analyzer.smooth_angle(right_knee, 'right')
        
        # Detect front leg (lower Y coordinate = forward)
        front_leg = 'left' if lk[1] < rk[1] else 'right'
        
        if front_leg == 'left':
            front_knee = left_knee
            back_knee = right_knee
            front_hip = left_hip
        else:
            front_knee = right_knee
            back_knee = left_knee
            front_hip = right_hip
        
        # Calculate back alignment
        shoulder_mid_x = (ls[0] + rs[0]) / 2
        shoulder_mid_y = (ls[1] + rs[1]) / 2
        hip_mid_x = (lh[0] + rh[0]) / 2
        hip_mid_y = (lh[1] + rh[1]) / 2
        
        vertical_offset = abs(shoulder_mid_x - hip_mid_x)
        vertical_height = abs(hip_mid_y - shoulder_mid_y) if hip_mid_y > shoulder_mid_y else 1
        lean_ratio = vertical_offset / max(vertical_height, 1)
        back_angle = 180 - (lean_ratio * 60)
        back_angle = max(120, min(180, back_angle))
        
        # Min knee for detecting standing position
        min_knee = min(left_knee, right_knee)
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'front_knee': front_knee,
            'back_knee': back_knee,
            'front_hip': front_hip,
            'front_leg': front_leg,
            'back': back_angle,
            'min_knee': min_knee,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la, 'ls': ls,
                'rh': rh, 'rk': rk, 'ra': ra, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        """
        Define target angles for each phase
        
        Returns:
            Dict of target angles with tolerances
        """
        return {
            'standing': {
                'min_knee': 165,
                'back': 165,
                'tolerance': 10
            },
            'lunge_down': {
                'front_knee': 90,
                'back_knee': 90,
                'back': 160,
                'tolerance': 10
            },
            'bottom': {
                'front_knee': 90,
                'back_knee': 85,
                'back': 160,
                'tolerance': 8
            },
            'lunge_up': {
                'min_knee': 140,
                'back': 160,
                'tolerance': 12
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
        front_knee = angles.get('front_knee', 0)
        back_knee = angles.get('back_knee', 0)
        back = angles.get('back', 0)
        min_knee = angles.get('min_knee', 0)
        
        # Back posture validation
        if back >= 155:
            feedback['back'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=back,
                message="Good upright posture"
            )
        elif back >= 140:
            feedback['back'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=back,
                message="Keep chest up"
            )
        else:
            feedback['back'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=back,
                message="Too much forward lean"
            )
        
        # Phase-specific validation
        if phase in ['lunge_down', 'bottom']:
            # Front knee validation
            if 75 <= front_knee <= 100:
                feedback['front_knee'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=front_knee,
                    message="Perfect front knee"
                )
            elif front_knee < 65:
                feedback['front_knee'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=front_knee,
                    message="Knee too far forward"
                )
            elif 100 < front_knee <= 120:
                feedback['front_knee'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=front_knee,
                    message="Go lower"
                )
            else:
                feedback['front_knee'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=front_knee,
                    message="Adjust depth"
                )
            
            # Back knee validation
            if 70 <= back_knee <= 95:
                feedback['back_knee'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=back_knee,
                    message="Good back knee"
                )
            elif back_knee < 60:
                feedback['back_knee'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=back_knee,
                    message="Back knee hitting ground"
                )
            elif back_knee > 110:
                feedback['back_knee'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=back_knee,
                    message="Lower back knee"
                )
            else:
                feedback['back_knee'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=back_knee,
                    message="Adjust back position"
                )
        
        elif phase == 'standing':
            if min_knee >= 160:
                feedback['position'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=min_knee,
                    message="Good neutral stance"
                )
            elif min_knee >= 150:
                feedback['position'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=min_knee,
                    message="Stand fully upright"
                )
            else:
                feedback['position'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=min_knee,
                    message="Return to neutral"
                )
        
        elif phase == 'lunge_up':
            if min_knee >= 140:
                feedback['returning'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=min_knee,
                    message="Keep pushing up"
                )
            else:
                feedback['returning'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=min_knee,
                    message="Stand back up"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter with form scoring
        
        Args:
            angle: Current min_knee angle
            feedback: Form validation feedback
            voice: Voice coach instance
        
        Returns:
            Tuple: (rep_done, current_phase, warnings)
        """
        rep_done = False
        warnings = []
        min_knee = angle
        
        # Camera guidance at start
        if not self.camera_guidance_given and voice:
            voice.speak("Position camera to your side", priority=True)
            self.camera_guidance_given = True
        
        # Check for critical form errors
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if voice:
                        voice.speak(fb.message, priority=True)
        
        # Phase state machine
        if self.phase == "standing":
            if min_knee >= 150:
                self.phase = "lunge_down"
                self.tempo_detector.start_phase('lunge_down')
                voice.give_atomic_command('start_descent', priority=False)
        
        elif self.phase == "lunge_down":
            # Check descent speed
            tempo_data = self.tempo_detector.check_tempo()
            if tempo_data.get('too_fast', False):
                warnings.append("Too fast - slow down")
                voice.give_atomic_command('slow_down', priority=False)
            
            if min_knee <= 100:
                self.phase = "bottom"
                self.tempo_detector.start_phase('bottom')
                voice.give_atomic_command('reached_bottom', priority=False)
        
        elif self.phase == "bottom":
            # Brief hold at bottom
            if self.tempo_detector.get_phase_duration() > 0.3:
                self.phase = "lunge_up"
                self.tempo_detector.start_phase('lunge_up')
                voice.give_atomic_command('start_ascent', priority=True)
        
        elif self.phase == "lunge_up":
            if min_knee >= 145:
                # Rep completed
                rep_done = True
                self.phase = "standing"
                
                # Calculate form score
                form_score = self._calculate_rep_form_score()
                
                # Handle rep completion
                self._handle_rep_completion(form_score, voice)
                
                if not self.probation_mode:
                    voice.speak("Return to neutral stance", priority=False)
        
        # Track phase change
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate form score for completed rep"""
        if self.current_rep_form_scores:
            avg_form = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg_form
        else:
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
        
        # Get target angles
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
        
        # Track for rep averaging
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
            # PRACTICE MODE: Full AR with targets
            frame, position_matched = self.ar.draw_practice_mode(
                frame=frame,
                joints=joints_coords,
                current_angles=angles,
                target_angles=self.get_target_poses()[self.phase],
                form_score=form_score
            )
        else:
            # COUNTED MODE: Simple skeleton
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
    print("LUNGES V2 - Enhanced Forward Lunges")
    print("="*70)
    
    exercise = LungesV2(target_reps=10)
    
    print("\n✅ Features Implemented:")
    print("- Front/back knee angle detection")
    print("- Back posture validation")
    print("- Form calculator integration")
    print("- Voice coach V2 with atomic commands")
    print("- Practice mode (3 GREEN reps)")
    print("- AR overlay support")
    print("- Camera positioning guidance")
    
    print("\n📊 Target Poses:")
    for phase, targets in exercise.get_target_poses().items():
        print(f"  {phase}: {targets}")
    
    print("\n🎯 Exercise ready!")
    print("="*70)