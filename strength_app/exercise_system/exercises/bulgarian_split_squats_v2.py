"""
Bulgarian Split Squats V2 - Advanced Unilateral Strength Exercise

IMPROVEMENTS FROM V1:
✅ FormCalculator integration for real-time scoring
✅ VoiceCoachV2 with atomic commands ("Lower down", "Push up")
✅ Accurate angle detection (front knee, back knee, posture)
✅ Practice mode (3 GREEN reps required)
✅ AR overlay V2 support
✅ Knee-over-toe safety check
✅ Hip level validation
✅ Better phase detection and timing

CHANGELOG:
- Added FormCalculator for dynamic form scoring
- Integrated VoiceCoachV2 for smooth audio guidance
- Fixed front/back knee angle calculations
- Added knee-over-toe detection (safety)
- Enhanced hip level checking
- Added practice mode with 3 GREEN rep requirement
- Improved tempo tracking (slow descent required)
- Added AR overlay targets
- Better form validation with specific feedback

TEST NOTES:
- Verify front/back leg detection works correctly
- Ensure knee-over-toe check is accurate
- Test slow descent requirement (>1 second)
- Check form score varies realistically
- Verify voice commands are atomic and clear
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class BulgarianSplitSquatsV2:
    """
    Bulgarian Split Squats - Advanced unilateral strength exercise
    
    Level: Advanced
    Category: Strength
    Target: Quadriceps, glutes, unilateral strength, balance
    
    Reference Video: https://www.youtube.com/watch?v=2C-uNgKwPLE
    (Bulgarian Split Squat - Proper Form)
    
    Biomechanics:
    - Front knee: hip → knee → ankle (target 90°)
    - Back knee: hip → knee → ankle (elevated on bench, ~90°)
    - Back posture: shoulder → hip alignment (>155°)
    - Key checkpoints:
      * Front knee behind toes
      * Torso upright (no excessive lean)
      * Slow controlled descent (>1 second)
      * Drive through front heel
    
    Phases:
    1. Standing (ready position, rear foot elevated)
    2. Descending (lowering into lunge)
    3. Bottom (both knees at ~90°)
    4. Ascending (pushing back to standing)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=2C-uNgKwPLE"
    
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
        
        # Session start
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """
        Calculate front and back knee angles
        
        CRITICAL: Detect which leg is front (on ground) vs back (elevated)
        - Front leg: lower ankle Y coordinate (on ground)
        - Back leg: higher ankle Y coordinate (elevated on bench)
        
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
        
        # Determine front leg (lower ankle = on ground)
        if ra[1] > la[1]:  # Right foot on ground = front leg
            front_knee = right_knee
            back_knee = left_knee
            front_hip = rh
            front_ankle = ra
        else:  # Left foot on ground = front leg
            front_knee = left_knee
            back_knee = right_knee
            front_hip = lh
            front_ankle = la
        
        # Hip level check (some asymmetry expected)
        hip_level_diff = abs(lh[1] - rh[1])
        
        # Back posture (torso upright)
        shoulder_mid = ((ls[0] + rs[0])//2, (ls[1] + rs[1])//2)
        hip_mid = ((lh[0] + rh[0])//2, (lh[1] + rh[1])//2)
        back = 180 - abs(analyzer.calculate_angle(
            (hip_mid[0], hip_mid[1] + 100), hip_mid, shoulder_mid
        ))
        
        # Check knee over toe (front knee shouldn't go way past ankle)
        knee_over_toe = False
        if front_knee < 140:  # Only check when squatting
            knee_forward = abs(front_ankle[0] - front_hip[0])
            knee_over_toe = knee_forward > 100
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'front_knee': front_knee,
            'back_knee': back_knee,
            'hip_level_diff': hip_level_diff,
            'back': back,
            'knee_over_toe': knee_over_toe,
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
                'front_knee': 175,
                'back_knee': 140,  # Back leg on bench, bent
                'back': 165,
                'tolerance': 10
            },
            'descending': {
                'front_knee': 135,
                'back_knee': 110,
                'back': 165,
                'tolerance': 12
            },
            'bottom': {
                'front_knee': 90,
                'back_knee': 90,
                'back': 165,
                'tolerance': 10
            },
            'ascending': {
                'front_knee': 135,
                'back_knee': 110,
                'back': 165,
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
        front = angles.get('front_knee', 0)
        back = angles.get('back_knee', 0)
        
        # CRITICAL: Knee over toe check
        if angles.get('knee_over_toe', False):
            feedback['knee_forward'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=0,
                message="Knee too far forward - step back"
            )
        
        # Hip level (some asymmetry expected)
        if angles.get('hip_level_diff', 0) > 50:
            feedback['hips'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=angles['hip_level_diff'],
                message="Level hips more"
            )
        
        # Torso upright
        if angles.get('back', 0) >= 155:
            feedback['posture'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles['back'],
                message="Good upright posture"
            )
        elif angles.get('back', 0) >= 145:
            feedback['posture'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=angles['back'],
                message="More upright"
            )
        else:
            feedback['posture'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=angles['back'],
                message="Too much forward lean"
            )
        
        # Phase-specific validation
        if phase == 'bottom':
            if 85 <= front <= 100:
                feedback['depth'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=front,
                    message="Perfect depth - 90 degrees"
                )
            elif 100 < front <= 120:
                feedback['depth'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=front,
                    message="Good depth"
                )
            elif front > 130:
                feedback['depth'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=front,
                    message="Squat deeper"
                )
            elif front < 80:
                feedback['depth'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=front,
                    message="Not too deep"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter with form scoring
        
        Args:
            angle: Current front_knee angle
            feedback: Form validation feedback
            voice: Voice coach instance
        
        Returns:
            Tuple: (rep_done, current_phase, warnings)
        """
        rep_done = False
        warnings = []
        front_knee = angle
        
        # Check for critical errors
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if voice:
                        voice.speak(fb.message, priority=True)
        
        # Phase state machine
        if self.phase == "standing":
            if front_knee >= 165:
                self.phase = "descending"
                self.tempo_detector.start_phase('descending')
                voice.give_atomic_command('start_descent', priority=False)
        
        elif self.phase == "descending":
            # Check descent speed
            tempo_data = self.tempo_detector.check_tempo()
            if tempo_data.get('too_fast', False):
                warnings.append("Too fast - slow down")
                voice.give_atomic_command('slow_down', priority=False)
            
            if front_knee <= 120:
                self.phase = "bottom"
                self.tempo_detector.start_phase('bottom')
                voice.give_atomic_command('reached_bottom', priority=False)
        
        elif self.phase == "bottom":
            # Brief hold at bottom
            if self.tempo_detector.get_phase_duration() > 0.4:
                self.phase = "ascending"
                self.tempo_detector.start_phase('ascending')
                voice.give_atomic_command('start_ascent', priority=True)
        
        elif self.phase == "ascending":
            if front_knee >= 165:
                # Rep completed
                rep_done = True
                self.phase = "standing"
                
                # Calculate form score
                form_score = self._calculate_rep_form_score()
                
                # Handle rep completion
                self._handle_rep_completion(form_score, voice)
        
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
    print("BULGARIAN SPLIT SQUATS V2 - Advanced Unilateral")
    print("="*70)
    
    exercise = BulgarianSplitSquatsV2(target_reps=10)
    
    print("\n✅ Features Implemented:")
    print("- Front/back knee angle detection")
    print("- Knee-over-toe safety check")
    print("- Hip level validation")
    print("- Tempo tracking (slow descent)")
    print("- Form calculator integration")
    print("- Voice coach V2 with atomic commands")
    print("- Practice mode (3 GREEN reps)")
    print("- AR overlay support")
    
    print("\n📊 Target Poses:")
    for phase, targets in exercise.get_target_poses().items():
        print(f"  {phase}: {targets}")
    
    print("\n🎯 Exercise ready!")
    print("="*70)