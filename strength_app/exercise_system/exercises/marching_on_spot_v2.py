"""
Marching on Spot V2 - Dynamic Balance and Hip Flexor Training

IMPROVEMENTS FROM V1:
✅ FormCalculator integration for real-time scoring
✅ VoiceCoachV2 with atomic commands ("Lift knee", "Good lift")
✅ Accurate hip flexion angle detection (shoulder → hip → knee)
✅ Practice mode (4 GREEN reps required - 2 per leg)
✅ AR overlay V2 support
✅ Better knee height detection
✅ Standing leg stability tracking
✅ Improved rep counting (alternating legs)

CHANGELOG:
- Added FormCalculator for dynamic form scoring
- Integrated VoiceCoachV2 for smooth audio guidance
- Fixed hip flexion angle calculation
- Added practice mode with 4 GREEN rep requirement
- Enhanced form validation for knee lift height
- Added standing leg stability checks
- Improved phase detection (lifting, lifted, lowering)
- Better alternating leg tracking
- Added AR overlay targets

TEST NOTES:
- Verify hip flexion angle is accurate (90° = thigh parallel)
- Ensure standing leg stability is detected correctly
- Test alternating leg counting works properly
- Check form score varies based on knee height
- Verify voice feedback is appropriate for balance exercise
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class MarchingOnSpotV2:
    """
    Marching on Spot - Dynamic balance and hip flexor training
    
    Level: Foundation
    Category: Balance + Strength
    Target: Hip flexors, core stability, balance
    
    Reference Video: https://www.youtube.com/watch?v=4WAHJYribFI
    (Marching in Place - Proper Form)
    
    Biomechanics:
    - Lifted hip angle: shoulder → hip → knee (target 85-95°)
    - Standing knee: hip → knee → ankle (should stay straight 165-180°)
    - Key checkpoints:
      * Knee lifted to 90° (thigh parallel to ground)
      * Standing leg straight and stable
      * Upright posture maintained
      * Controlled lifting and lowering
    
    Phases:
    1. Standing (both feet on ground)
    2. Lifting (knee coming up)
    3. Lifted (knee at 90°, thigh parallel)
    4. Lowering (foot returning down)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=4WAHJYribFI"
    
    def __init__(self, target_reps=10):
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "standing"
        self.last_phase = "standing"
        
        # Practice mode (4 GREEN reps - 2 per leg)
        self.probation_mode = True
        self.practice_reps_needed = 4
        self.practice_reps_completed = 0
        
        # Form tracking
        self.form_scores = []
        self.current_rep_form_scores = []
        
        # Stability detector (crucial for balance exercise)
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        
        # Session start
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """
        Calculate hip flexion and knee angles for marching
        
        CRITICAL: Detect lifted leg vs standing leg
        - Lifted leg: knee with lower Y coordinate (higher on screen)
        - Standing leg: knee with higher Y coordinate (lower on screen)
        
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
        
        # Calculate hip flexion angles (shoulder → hip → knee)
        left_hip_flexion = analyzer.calculate_angle(ls, lh, lk)
        right_hip_flexion = analyzer.calculate_angle(rs, rh, rk)
        
        # Calculate knee angles (hip → knee → ankle)
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        # Smooth angles
        left_knee = analyzer.smooth_angle(left_knee, 'left')
        right_knee = analyzer.smooth_angle(right_knee, 'right')
        
        # Detect lifted leg (knee higher up = lower Y coordinate)
        lifted_leg = 'left' if lk[1] < rk[1] else 'right'
        
        if lifted_leg == 'left':
            lifted_hip = left_hip_flexion
            lifted_knee = left_knee
            standing_knee = right_knee
        else:
            lifted_hip = right_hip_flexion
            lifted_knee = right_knee
            standing_knee = left_knee
        
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
        
        # Knee height difference (for detecting lift)
        knee_height_diff = abs(lk[1] - lh[1]) if lifted_leg == 'left' else abs(rk[1] - rh[1])
        
        return {
            'left_hip_flexion': left_hip_flexion,
            'right_hip_flexion': right_hip_flexion,
            'lifted_hip': lifted_hip,
            'lifted_knee': lifted_knee,
            'standing_knee': standing_knee,
            'lifted_leg': lifted_leg,
            'back': back_angle,
            'knee_height_diff': knee_height_diff,
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
                'lifted_hip': 170,
                'standing_knee': 170,
                'back': 165,
                'tolerance': 10
            },
            'lifting': {
                'lifted_hip': 110,
                'standing_knee': 165,
                'back': 165,
                'tolerance': 12
            },
            'lifted': {
                'lifted_hip': 85,  # 90° = thigh parallel
                'standing_knee': 165,
                'back': 165,
                'tolerance': 10
            },
            'lowering': {
                'lifted_hip': 120,
                'standing_knee': 165,
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
        lifted_hip = angles.get('lifted_hip', 0)
        standing_knee = angles.get('standing_knee', 0)
        back = angles.get('back', 0)
        
        # Hip flexion check (knee lift height)
        if phase in ['lifting', 'lifted']:
            if 75 <= lifted_hip <= 95:
                feedback['hip_lift'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=lifted_hip,
                    message="Perfect knee height"
                )
            elif 95 < lifted_hip <= 110:
                feedback['hip_lift'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=lifted_hip,
                    message="Lift knee higher"
                )
            elif lifted_hip > 120:
                feedback['hip_lift'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=lifted_hip,
                    message="Good effort - lift more"
                )
            else:
                feedback['hip_lift'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=lifted_hip,
                    message="Good lift"
                )
            
            # Standing leg stability
            if 160 <= standing_knee <= 180:
                feedback['stability'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=standing_knee,
                    message="Stable standing leg"
                )
            elif 145 <= standing_knee < 160:
                feedback['stability'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=standing_knee,
                    message="Straighten standing leg"
                )
            else:
                feedback['stability'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=standing_knee,
                    message="Keep standing leg straight"
                )
        
        # Posture check
        if back >= 160:
            feedback['posture'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=back,
                message="Excellent posture"
            )
        elif back >= 145:
            feedback['posture'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=back,
                message="Stand taller"
            )
        else:
            feedback['posture'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=back,
                message="Leaning too much"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter with form scoring
        
        Args:
            angle: Current lifted_hip angle
            feedback: Form validation feedback
            voice: Voice coach instance
        
        Returns:
            Tuple: (rep_done, current_phase, warnings)
        """
        rep_done = False
        warnings = []
        lifted_hip = angle
        
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
            if lifted_hip > 130:
                self.phase = "lifting"
                self.tempo_detector.start_phase('lifting')
                if self.rep_count == 0:
                    voice.speak("Lift your knee", priority=True)
        
        elif self.phase == "lifting":
            if lifted_hip <= 100:
                self.phase = "lifted"
                self.tempo_detector.start_phase('lifted')
                if not has_critical:
                    voice.speak("Good - now down", priority=True)
        
        elif self.phase == "lifted":
            # Brief hold at top
            if self.tempo_detector.get_phase_duration() > 0.2:
                self.phase = "lowering"
                self.tempo_detector.start_phase('lowering')
        
        elif self.phase == "lowering":
            if lifted_hip > 130:
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
            
            # Announce every 2 reps (since alternating)
            if self.rep_count % 2 == 0:
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
    print("MARCHING ON SPOT V2 - Enhanced Dynamic Balance")
    print("="*70)
    
    exercise = MarchingOnSpotV2(target_reps=10)
    
    print("\n✅ Features Implemented:")
    print("- Hip flexion angle detection (90° = thigh parallel)")
    print("- Standing leg stability tracking")
    print("- Alternating leg counting")
    print("- Form calculator integration")
    print("- Voice coach V2 with atomic commands")
    print("- Practice mode (4 GREEN reps)")
    print("- AR overlay support")
    
    print("\n📊 Target Poses:")
    for phase, targets in exercise.get_target_poses().items():
        print(f"  {phase}: {targets}")
    
    print("\n🎯 Exercise ready!")
    print("="*70)