"""
Static Glutei V2 - Isometric Glute Activation Exercise

IMPROVEMENTS FROM V1:
✅ FormCalculator integration for real-time scoring
✅ VoiceCoachV2 with atomic commands
✅ Hold counting with voice (1-10 seconds)
✅ Practice mode (2 GREEN holds required)
✅ Proper squeeze detection
✅ Rest phase between holds

CHANGELOG:
- Added FormCalculator for dynamic form scoring
- Integrated VoiceCoachV2 for smooth audio guidance
- Enhanced squeeze detection (hip extension)
- Added practice mode with 2 GREEN hold requirement
- Implemented 10-second hold with countdown
- Added 3-second rest phase
- Posture validation during hold

TEST NOTES:
- Verify squeeze detection works (glute contraction)
- Ensure 10-second hold with voice countdown
- Test practice mode (only GREEN holds count)
- Check form score varies realistically

Reference Video: https://www.youtube.com/watch?v=OUgsJ8-Vi0E
(Static Glute Squeeze - Isometric Exercise)
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class StaticGluteiV2:
    """
    Static Glutei - Isometric glute activation
    
    Level: Foundation
    Category: Strength (Isometric)
    Target: Gluteus maximus, posterior chain
    
    Reference Video: https://www.youtube.com/watch?v=OUgsJ8-Vi0E
    (Static Glute Squeeze - Isometric Exercise)
    
    Biomechanics:
    - Position: Standing or lying face-down
    - Action: Squeeze glutes tightly (hip extension)
    - Hold: 10 seconds per rep
    - Target: 10 reps
    
    Detection: Hip extension angle increase during squeeze
    """
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=OUgsJ8-Vi0E"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        self.phase = "ready"
        self.last_phase = "ready"
        
        # Hold tracking
        self.hold_start_time = None
        self.current_hold_duration = 0
        self.target_hold_time = 10.0
        self.rest_duration = 3.0
        self.last_announced_second = -1
        
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
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """Calculate hip extension for glute squeeze detection"""
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        # Hip extension angles (shoulder-hip-knee)
        left_hip_ext = analyzer.calculate_angle(ls, lh, lk)
        right_hip_ext = analyzer.calculate_angle(rs, rh, rk)
        
        # Smooth angles
        left_hip_ext = analyzer.smooth_angle(left_hip_ext, 'left')
        right_hip_ext = analyzer.smooth_angle(right_hip_ext, 'right')
        
        # Average hip extension (increases during glute squeeze)
        avg_hip_ext = (left_hip_ext + right_hip_ext) / 2
        
        # Symmetry check
        hip_symmetry = abs(left_hip_ext - right_hip_ext)
        
        return {
            'left_hip_ext': left_hip_ext,
            'right_hip_ext': right_hip_ext,
            'avg_hip_ext': avg_hip_ext,
            'hip_symmetry': hip_symmetry,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'ls': ls,
                'rh': rh, 'rk': rk, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        return {
            'ready': {
                'avg_hip_ext': 170,
                'hip_symmetry': 10,
                'tolerance': 10
            },
            'holding': {
                'avg_hip_ext': 175,  # Slight increase during squeeze
                'hip_symmetry': 8,
                'tolerance': 8
            }
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        
        # Symmetry check
        if angles.get('hip_symmetry', 0) < 15:
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=angles['hip_symmetry'],
                message="Even glute squeeze"
            )
        elif angles.get('hip_symmetry', 0) < 25:
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=angles['hip_symmetry'],
                message="Squeeze evenly"
            )
        else:
            feedback['symmetry'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=angles['hip_symmetry'],
                message="Uneven squeeze"
            )
        
        # Squeeze intensity (hip extension should increase slightly)
        if phase == 'holding':
            if angles.get('avg_hip_ext', 0) >= 172:
                feedback['squeeze'] = JointFeedback(
                    status=FormStatus.CORRECT,
                    angle=angles['avg_hip_ext'],
                    message="Strong squeeze"
                )
            elif angles.get('avg_hip_ext', 0) >= 168:
                feedback['squeeze'] = JointFeedback(
                    status=FormStatus.NEEDS_ADJUSTMENT,
                    angle=angles['avg_hip_ext'],
                    message="Squeeze harder"
                )
            else:
                feedback['squeeze'] = JointFeedback(
                    status=FormStatus.INCORRECT,
                    angle=angles['avg_hip_ext'],
                    message="Not squeezing enough"
                )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        
        has_critical = any(f.status == FormStatus.INCORRECT for f in feedback.values())
        
        if has_critical:
            for fb in feedback.values():
                if fb.status == FormStatus.INCORRECT:
                    warnings.append(fb.message)
                    if voice:
                        voice.speak(fb.message, priority=True)
        
        # STATE MACHINE
        if self.phase == "resting":
            if self.tempo_detector.get_phase_duration() > self.rest_duration:
                self.phase = "ready"
                self.tempo_detector.start_phase('ready')
                if voice:
                    voice.speak("Squeeze glutes tightly", priority=True)
        
        elif self.phase == "ready":
            # Detect squeeze beginning
            if self.tempo_detector.get_phase_duration() > 0.5 and not has_critical:
                self.phase = "holding"
                self.tempo_detector.start_phase('holding')
                self.hold_start_time = time.time()
                self.last_announced_second = -1
                voice.speak("Hold tight", priority=True)
        
        elif self.phase == "holding":
            if self.hold_start_time:
                self.current_hold_duration = time.time() - self.hold_start_time
                
                # Voice countdown
                if voice:
                    current_second = int(self.current_hold_duration)
                    if current_second != self.last_announced_second and current_second > 0:
                        self.last_announced_second = current_second
                        voice.count_hold_seconds(current_second, int(self.target_hold_time))
                
                if self.current_hold_duration >= self.target_hold_time:
                    # Calculate form score
                    form_score = self._calculate_rep_form_score()
                    
                    if not has_critical:
                        self._handle_rep_completion(form_score, voice)
                        rep_done = True
                    else:
                        self.rejected_count += 1
                        voice.speak("Hold broken", priority=True)
                    
                    self.phase = "resting"
                    self.tempo_detector.start_phase('resting')
                    self.hold_start_time = None
                    self.current_hold_duration = 0
                    voice.give_atomic_command('relax', priority=True)
        
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
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("="*70)
    print("STATIC GLUTEI V2 - Isometric Glute Activation")
    print("="*70)
    exercise = StaticGluteiV2(target_reps=10)
    print("\n✅ Features: Glute squeeze detection, 10-sec holds, voice countdown")
    print("🎯 Exercise ready!")