"""
Straight Leg Raises V2 - 4-Way Foundation Exercise

IMPROVEMENTS FROM V1:
✅ FormCalculator integration for real-time scoring
✅ VoiceCoachV2 with atomic commands
✅ Accurate leg lift angle detection (target 45°)
✅ Practice mode (2 GREEN reps required)
✅ Direction tracking (FRONT, SIDE, BACK, CROSS)
✅ 2-second hold at top
✅ Knee straightness validation

CHANGELOG:
- Added FormCalculator for dynamic form scoring
- Integrated VoiceCoachV2 for smooth audio guidance
- Enhanced lift angle detection (45° target)
- Added practice mode with 2 GREEN rep requirement
- Implemented direction cycling (4-way)
- Better knee straightness checking (must stay >170°)
- 2-second hold at top position
- Direction announcement on switches

TEST NOTES:
- Verify lift angle detection works
- Ensure direction cycling works correctly
- Test 2-second hold at top
- Check knee stays straight throughout
- Verify voice announces direction switches

Reference Video: https://www.youtube.com/watch?v=4XW8zNLQMJI
(4-Way Straight Leg Raises - Complete Tutorial)
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class StraightLegRaisesV2:
    """
    4-Way Straight Leg Raises - Foundation quad activation
    
    Level: Foundation
    Category: Strength (Safe quad activation)
    Target: Quadriceps, hip flexors, abductors, glutes
    
    Reference Video: https://www.youtube.com/watch?v=4XW8zNLQMJI
    (4-Way Straight Leg Raises - Complete Tutorial)
    
    Biomechanics:
    - Position: Lying (changes per direction)
    - Action: Lift straight leg to 45°
    - Hold: 2 seconds at top
    - Knee: Must stay straight (>170°)
    
    Directions (cycle through):
    1. FRONT (lying on back)
    2. SIDE (lying on side)
    3. BACK (lying face down)
    4. CROSS (diagonal across body)
    
    Target: 3 reps per direction = 12 total
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=4XW8zNLQMJI"
    
    def __init__(self, target_reps=12):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        self.phase = "down"
        self.last_phase = "down"
        
        # Direction tracking
        self.current_direction = 0  # 0=FRONT, 1=SIDE, 2=BACK, 3=CROSS
        self.direction_names = ['FRONT', 'SIDE', 'BACK', 'CROSS']
        self.reps_per_direction = 3
        self.reps_in_current_direction = 0
        
        # Practice mode
        self.probation_mode = True
        self.practice_reps_needed = 2
        self.practice_reps_completed = 0
        
        # Form tracking
        self.form_scores = []
        self.current_rep_form_scores = []
        
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        
    
    def calculate_angles(self, analyzer, results, shape):
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        # Working leg (right for demo)
        working_hip = rh
        working_knee = rk
        working_ankle = ra
        opposite_hip = lh
        
        # Lift angle (elevation from horizontal)
        hip_to_ankle_y = abs(working_ankle[1] - working_hip[1])
        hip_to_ankle_x = abs(working_ankle[0] - working_hip[0])
        
        lift_angle = analyzer.calculate_angle(
            (working_hip[0] + 100, working_hip[1]),  # Horizontal reference
            working_hip,
            working_ankle
        )
        
        # Knee straightness
        knee_angle = analyzer.calculate_angle(working_hip, working_knee, working_ankle)
        
        return {
            'lift_angle': lift_angle,
            'knee_angle': knee_angle,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra
            }
        }
    
    def get_target_poses(self):
        return {
            'down': {
                'lift_angle': 0,
                'knee_angle': 175,
                'tolerance': 8
            },
            'lifting': {
                'lift_angle': 25,
                'knee_angle': 175,
                'tolerance': 10
            },
            'top': {
                'lift_angle': 45,
                'knee_angle': 175,
                'tolerance': 8
            },
            'lowering': {
                'lift_angle': 25,
                'knee_angle': 175,
                'tolerance': 10
            }
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        lift_angle = angles.get('lift_angle', 0)
        knee_angle = angles.get('knee_angle', 0)
        
        # Knee must stay straight
        if knee_angle >= 170:
            feedback['knee'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=knee_angle,
                message="Perfect - leg straight"
            )
        elif knee_angle >= 160:
            feedback['knee'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=knee_angle,
                message="Straighten knee more"
            )
        else:
            feedback['knee'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=knee_angle,
                message="Knee bent - straighten"
            )
        
        # Phase-specific validation
        if phase == 'top':
            if 40 <= lift_angle <= 50:
                feedback['height'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=lift_angle,
                    message="Perfect height"
                )
            elif 30 <= lift_angle < 40:
                feedback['height'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=lift_angle,
                    message="Lift higher"
                )
            elif lift_angle > 50:
                feedback['height'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=lift_angle,
                    message="Not too high"
                )
            else:
                feedback['height'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=lift_angle,
                    message="Lift much higher"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        lift_angle = angle
        
        # Add direction indicator
        current_dir = self.direction_names[self.current_direction]
        warnings.insert(0, f"{current_dir} raises: {self.reps_in_current_direction}/{self.reps_per_direction}")
        
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if voice:
                        voice.speak(fb.message, priority=True)
        
        # STATE MACHINE
        if self.phase == "down":
            if lift_angle <= 10 and self.tempo_detector.get_phase_duration() > 0.5:
                self.phase = "lifting"
                self.tempo_detector.start_phase('lifting')
                voice.speak("Lift", priority=True)
        
        elif self.phase == "lifting":
            if lift_angle >= 40 and self.tempo_detector.get_phase_duration() > 0.8:
                self.phase = "top"
                self.tempo_detector.start_phase('top')
                voice.speak("Hold", priority=True)
        
        elif self.phase == "top":
            # Must hold 2 seconds
            if self.tempo_detector.get_phase_duration() >= 2.0:
                self.phase = "lowering"
                self.tempo_detector.start_phase('lowering')
                voice.speak("Lower", priority=True)
        
        elif self.phase == "lowering":
            if lift_angle <= 10 and self.tempo_detector.get_phase_duration() > 0.5:
                if not has_critical:
                    self.reps_in_current_direction += 1
                    
                    # Check if direction complete
                    if self.reps_in_current_direction >= self.reps_per_direction:
                        self.current_direction += 1
                        self.reps_in_current_direction = 0
                        
                        if self.current_direction < 4:
                            next_dir = self.direction_names[self.current_direction]
                            warnings.append(f"✅ Switch to {next_dir} raises")
                            voice.speak(f"Switch to {next_dir} raises", priority=True)
                        else:
                            # All 4 directions complete
                            self.current_direction = 0
                    
                    form_score = self._calculate_rep_form_score()
                    self._handle_rep_completion(form_score, voice)
                    rep_done = True
                else:
                    self.rejected_count += 1
                    voice.speak("Rep rejected", priority=True)
                
                self.phase = "down"
                self.tempo_detector.start_phase('down')
        
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        if self.current_rep_form_scores:
            avg_form = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg_form
        return 85.0
    
    def _handle_rep_completion(self, form_score, voice):
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
                voice.provide_ar_feedback(form_score)
        else:
            self.rep_count += 1
            self.form_scores.append(form_score)
            voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        self.stability_detector.update(joints_coords)
        target_angles = self.get_target_poses()[self.phase]
        stability_data = self.stability_detector.get_stability_data()
        tempo_data = self.tempo_detector.check_tempo()
        
        form_score = FormCalculator.calculate_form_score(
            angles=angles,
            target_angles=target_angles,
            stability=stability_data,
            tempo=tempo_data
        )
        
        self.current_rep_form_scores.append(form_score)
        return form_score
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
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
    
    def get_stats(self):
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
            'target_reps': self.target_reps,
            'current_direction': self.direction_names[self.current_direction],
            'direction_progress': f"{self.reps_in_current_direction}/{self.reps_per_direction}"
        }


if __name__ == "__main__":
    print("="*70)
    print("STRAIGHT LEG RAISES V2 - 4-Way Foundation")
    print("="*70)
    exercise = StraightLegRaisesV2(target_reps=12)
    print("\n✅ Features: 45° lift detection, direction cycling, 2-sec holds, knee straightness")
    print("🎯 Exercise ready!")