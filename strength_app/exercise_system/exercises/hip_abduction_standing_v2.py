"""
Hip Abduction Standing V2 - Lateral hip strengthening with hold

Reference Video: https://www.youtube.com/watch?v=kAro58MDrC0
(Standing Hip Abduction Technique)
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class HipAbductionStandingV2:
    """Hip Abduction Standing - Lateral leg raise with 2-second hold"""
    
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=kAro58MDrC0"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        self.phase = "standing"
        self.last_phase = "standing"
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        self.form_scores = []
        self.current_rep_form_scores = []
        self.hold_start_time = None
        self.hold_duration_required = 2.0
        self.hold_announced_seconds = set()
        self.stability_detector = StabilityDetector()
        self.tempo_detector = TempoDetector()
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        # Hip abduction angle (hip-hip-ankle)
        left_abd = analyzer.calculate_angle(rh, lh, la)
        right_abd = analyzer.calculate_angle(lh, rh, ra)
        max_abduction = max(left_abd, right_abd)
        
        # Back alignment
        shoulder_mid_x = (ls[0] + rs[0]) / 2
        hip_mid_x = (lh[0] + rh[0]) / 2
        shoulder_mid_y = (ls[1] + rs[1]) / 2
        hip_mid_y = (lh[1] + rh[1]) / 2
        
        vertical_offset = abs(shoulder_mid_x - hip_mid_x)
        vertical_height = abs(hip_mid_y - shoulder_mid_y) if hip_mid_y > shoulder_mid_y else 1
        lean_ratio = vertical_offset / max(vertical_height, 1)
        back_angle = 180 - (lean_ratio * 60)
        back_angle = max(120, min(180, back_angle))
        
        return {
            'left_abduction': left_abd,
            'right_abduction': right_abd,
            'max_abduction': max_abduction,
            'back': back_angle,
            'joints_coords': {'lh': lh, 'lk': lk, 'la': la, 'rh': rh, 'rk': rk, 'ra': ra, 'ls': ls, 'rs': rs}
        }
    
    def get_target_poses(self):
        return {
            'standing': {'max_abduction': 90, 'back': 165, 'tolerance': 10},
            'lifting': {'max_abduction': 115, 'back': 165, 'tolerance': 10},
            'lifted': {'max_abduction': 135, 'back': 165, 'tolerance': 10},
            'holding': {'max_abduction': 135, 'back': 165, 'tolerance': 8},
            'lowering': {'max_abduction': 115, 'back': 165, 'tolerance': 10}
        }
    
    def validate_form(self, angles, phase):
        feedback = {}
        max_abd = angles.get('max_abduction', 0)
        back = angles.get('back', 0)
        
        # Back posture
        if back >= 155:
            feedback['back'] = JointFeedback(FormStatus.CORRECT, back, "Good posture")
        elif back >= 140:
            feedback['back'] = JointFeedback(FormStatus.NEEDS_ADJUSTMENT, back, "Stand upright")
        else:
            feedback['back'] = JointFeedback(FormStatus.INCORRECT, back, "Too much lean")
        
        # Abduction range
        if phase in ['lifted', 'holding']:
            if 120 <= max_abd <= 150:
                feedback['abduction'] = JointFeedback(FormStatus.CORRECT, max_abd, "Perfect range")
            elif max_abd < 110:
                feedback['abduction'] = JointFeedback(FormStatus.NEEDS_ADJUSTMENT, max_abd, "Lift higher")
            else:
                feedback['abduction'] = JointFeedback(FormStatus.INCORRECT, max_abd, "Too high")
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        rep_done = False
        warnings = []
        max_abd = angle
        
        if self.phase == "standing" and max_abd < 95:
            self.tempo_detector.start_phase('standing')
        elif self.phase == "standing" and max_abd > 100:
            self.phase = "lifting"
            voice.speak("Lift leg", priority=False)
        elif self.phase == "lifting" and max_abd >= 120:
            self.phase = "lifted"
        elif self.phase == "lifted":
            if self.hold_start_time is None:
                self.hold_start_time = time.time()
                self.hold_announced_seconds = set()
                self.phase = "holding"
                voice.speak("Hold steady", priority=False)
        elif self.phase == "holding":
            if self.hold_start_time:
                hold_elapsed = time.time() - self.hold_start_time
                current_second = int(hold_elapsed)
                
                if current_second > 0 and current_second not in self.hold_announced_seconds:
                    self.hold_announced_seconds.add(current_second)
                    voice.count_hold_seconds(current_second, int(self.hold_duration_required))
                
                if hold_elapsed >= self.hold_duration_required:
                    self.phase = "lowering"
                    self.hold_start_time = None
                    voice.speak("Lower slowly", priority=False)
        elif self.phase == "lowering" and max_abd < 95:
            rep_done = True
            self.phase = "standing"
            form_score = self._calculate_rep_form_score()
            self._handle_rep_completion(form_score, voice)
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        if self.current_rep_form_scores:
            avg = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg
        return 85.0
    
    def _handle_rep_completion(self, form_score, voice):
        if self.probation_mode:
            if form_score >= 85:
                self.practice_reps_completed += 1
                voice.announce_practice_rep(self.practice_reps_completed, self.practice_reps_needed, form_score)
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
        form_score = FormCalculator.calculate_form_score(
            angles=angles,
            target_angles=self.get_target_poses()[self.phase],
            stability=self.stability_detector.get_stability_data(),
            tempo=self.tempo_detector.check_tempo()
        )
        self.current_rep_form_scores.append(form_score)
        return form_score
    
    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        if self.probation_mode:
            frame, _ = self.ar.draw_practice_mode(frame, joints_coords, angles, self.get_target_poses()[self.phase], form_score)
        else:
            frame = self.ar.draw_counted_mode(frame, joints_coords, form_score)
        return frame
    
    def get_stats(self):
        avg_form_score = sum(self.form_scores) / len(self.form_scores) if self.form_scores else 0
        return {
            'reps_completed': self.rep_count,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form_score, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("HIP ABDUCTION STANDING V2 - Lateral leg raise with hold")