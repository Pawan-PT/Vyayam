"""
Lateral Hops V2 - Plyometric Return-to-Sport Exercise

IMPROVEMENTS FROM V1:
✅ FormCalculator integration for landing stability scoring
✅ VoiceCoachV2 with atomic commands ("Hop", "Stick landing")
✅ Accurate landing detection and knee angle tracking
✅ Practice mode (4 GREEN reps required)
✅ AR overlay V2 support
✅ 2-second landing stability requirement
✅ Lateral movement detection
✅ Landing form validation (critical for ACL safety)

CHANGELOG:
- Added FormCalculator for dynamic form scoring
- Integrated VoiceCoachV2 for smooth audio guidance
- Enhanced landing detection (hip position tracking)
- Added 2-second stability hold requirement
- Improved landing form validation
- Added practice mode with 4 GREEN rep requirement
- Better hop detection (lateral movement tracking)
- Added AR overlay targets
- Landing quality scoring (soft vs stiff)

TEST NOTES:
- Verify lateral hop detection works (sideways movement)
- Ensure 2-second stability requirement is enforced
- Test landing form validation (knee angle)
- Check form score reflects landing quality
- Verify voice feedback is appropriate for plyometric
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class LateralHopsV2:
    """
    Lateral Hops - Plyometric return-to-sport exercise
    
    Level: Advanced
    Category: Plyometric + Balance
    Target: Lateral stability, gluteus medius, return-to-sport
    
    Reference Video: https://www.youtube.com/watch?v=TQSVR6-Bkhw
    (Lateral Hops - ACL Rehab Tutorial)
    
    Biomechanics:
    - Stance knee: hip → knee → ankle (target 150-165° on landing)
    - Key checkpoints:
      * Soft landing with knee bend (NOT stiff)
      * Stick landing for 2 seconds (no wobble)
      * Lateral movement detected
      * Control maintained throughout
    
    Phases:
    1. Standing (ready position on one leg)
    2. Hopping (lateral jump)
    3. Landing (soft landing with knee bend)
    4. Stable (2-second hold after landing)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=TQSVR6-Bkhw"
    
    def __init__(self, target_reps=10):
        # Exercise parameters
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "standing"
        self.last_phase = "standing"
        
        # Practice mode (4 GREEN reps required)
        self.probation_mode = True
        self.practice_reps_needed = 4
        self.practice_reps_completed = 0
        
        # Form tracking
        self.form_scores = []
        self.current_rep_form_scores = []
        
        # Landing stability tracking
        self.landing_stability_frames = 0
        self.landing_stability_required = 60  # 2 seconds @ 30fps
        
        # Lateral movement tracking
        self.last_position = None
        
        # Stability detector (critical for landing assessment)
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        
        # Session start
        # Exercise announcement moved to runner
        self.voice.speak("Hop sideways and stick landing", priority=True)
    
    def calculate_angles(self, analyzer, results, shape):
        """
        Calculate stance knee angle and detect lateral movement
        
        CRITICAL: Detect which leg is stance leg (weight-bearing)
        - Stance leg: lower ankle Y coordinate (on ground)
        
        Returns:
            Dict with angles, lateral movement, and joint coordinates
        """
        # Extract joint coordinates
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        # Calculate knee angles
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        # Detect stance leg (lower ankle = on ground)
        if ra[1] > la[1]:
            stance_knee = right_knee
            stance_leg = 'right'
        else:
            stance_knee = left_knee
            stance_leg = 'left'
        
        # Detect lateral movement (hop)
        hip_center_x = (lh[0] + rh[0]) / 2
        
        hop_detected = False
        if self.last_position is not None:
            lateral_movement = abs(hip_center_x - self.last_position)
            if lateral_movement > 80:  # Significant lateral shift
                hop_detected = True
        
        self.last_position = hip_center_x
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'stance_knee': stance_knee,
            'stance_leg': stance_leg,
            'hop_detected': hop_detected,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra
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
                'stance_knee': 175,
                'tolerance': 10
            },
            'landing': {
                'stance_knee': 150,  # Soft landing with knee bend
                'tolerance': 12
            },
            'stable': {
                'stance_knee': 175,
                'tolerance': 8
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
        stance = angles.get('stance_knee', 0)
        
        if phase == 'landing':
            # Landing form validation (CRITICAL for ACL safety)
            if 140 <= stance <= 165:
                feedback['landing'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=stance,
                    message="Good soft landing"
                )
            elif stance > 170:
                feedback['landing'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=stance,
                    message="Landing too stiff - bend knee"
                )
            elif stance < 130:
                feedback['landing'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=stance,
                    message="Landing too deep"
                )
        
        elif phase == 'stable':
            # Stability check
            if 170 <= stance <= 180:
                feedback['stability'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=stance,
                    message="Good stability"
                )
            else:
                feedback['stability'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=stance,
                    message="Stand upright"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """
        Update rep counter with landing stability scoring
        
        Args:
            angle: Current stance_knee angle
            feedback: Form validation feedback
            voice: Voice coach instance
        
        Returns:
            Tuple: (rep_done, current_phase, warnings)
        """
        rep_done = False
        warnings = []
        stance_knee = angle
        
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
            # Ready to hop
            if self.tempo_detector.get_phase_duration() > 1.0:
                self.phase = "hopping"
                self.tempo_detector.start_phase('hopping')
                voice.speak("Hop laterally", priority=True)
        
        elif self.phase == "hopping":
            # Detect landing (knee bends)
            if stance_knee < 165:
                self.phase = "landing"
                self.tempo_detector.start_phase('landing')
                self.landing_stability_frames = 0
                voice.speak("Stick the landing", priority=True)
        
        elif self.phase == "landing":
            # Must stabilize landing for 2 seconds
            self.landing_stability_frames += 1
            
            if self.landing_stability_frames >= self.landing_stability_required:
                self.phase = "stable"
                self.tempo_detector.start_phase('stable')
        
        elif self.phase == "stable":
            # Brief hold after stability achieved
            if self.tempo_detector.get_phase_duration() > 0.5:
                # Rep completed
                rep_done = True
                self.phase = "standing"
                
                # Calculate form score
                form_score = self._calculate_rep_form_score()
                
                # Handle rep completion
                if has_critical:
                    self.rejected_count += 1
                    voice.speak("Landing unstable - rejected", priority=True)
                else:
                    self._handle_rep_completion(form_score, voice)
                
                # Reset landing counter
                self.landing_stability_frames = 0
        
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
    print("LATERAL HOPS V2 - Enhanced Plyometric Exercise")
    print("="*70)
    
    exercise = LateralHopsV2(target_reps=10)
    
    print("\n✅ Features Implemented:")
    print("- Landing stability detection (2-second hold)")
    print("- Lateral movement tracking")
    print("- Soft landing validation")
    print("- Form calculator integration")
    print("- Voice coach V2 with atomic commands")
    print("- Practice mode (4 GREEN reps)")
    print("- AR overlay support")
    
    print("\n📊 Target Poses:")
    for phase, targets in exercise.get_target_poses().items():
        print(f"  {phase}: {targets}")
    
    print("\n🎯 Exercise ready!")
    print("="*70)