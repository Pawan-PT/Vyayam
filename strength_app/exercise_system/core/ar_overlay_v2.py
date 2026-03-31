"""
AR Overlay System V2
GREEN/YELLOW/RED skeleton in BOTH practice and counted modes

CHANGES FROM V1:
- Practice mode: Now shows Green/Yellow/Red (not just yellow)
- Form-based coloring in both modes
- Cleaner visual feedback
"""

import cv2
import numpy as np
from typing import Dict, Tuple, Optional

try:
    from form_calculator import FormCalculator
except ImportError:
    # Fallback if form_calculator not available
    class FormCalculator:
        @staticmethod
        def get_form_color(score):
            if score >= 85:
                return (0, 255, 0)
            elif score >= 70:
                return (0, 255, 255)
            else:
                return (0, 0, 255)


class AROverlayV2:
    """
    Enhanced AR Overlay System
    
    KEY IMPROVEMENT: Green/Yellow/Red in BOTH modes based on form score
    
    PRACTICE MODE: Shows Green/Yellow/Red skeleton + target overlay + arrows
    COUNTED MODE: Shows Green/Yellow/Red skeleton only (simple)
    """
    
    def __init__(self):
        # Colors
        self.target_color = (0, 255, 255)      # Cyan for target skeleton
        self.arrow_color = (255, 165, 0)       # Orange for correction arrows
        self.text_color = (255, 255, 255)      # White for text
        
        # Transparency
        self.target_alpha = 0.4                # Target skeleton transparency
        self.arrow_alpha = 0.8                 # Arrow transparency
        
        # Thresholds
        self.match_threshold = 8               # Within 8° = matched
        self.significant_diff = 10             # >10° = show correction
        
        # Animation
        self.pulse_phase = 0
    
    # ========================================================================
    # MAIN DRAWING METHODS
    # ========================================================================
    
    def draw_practice_mode(self,
                          frame: np.ndarray,
                          joints: Dict,
                          current_angles: Dict,
                          target_angles: Dict,
                          form_score: float) -> Tuple[np.ndarray, bool]:
        """
        PRACTICE MODE: Draw complete AR overlay with form-based coloring
        
        Args:
            frame: Video frame
            joints: Current joint positions
            current_angles: Current measured angles
            target_angles: Target angles for current phase
            form_score: Form score 0-100
        
        Returns:
            (annotated_frame, position_matched)
        """
        if not joints or not target_angles:
            return frame, False
        
        # Get form-based color (GREEN/YELLOW/RED)
        skeleton_color = FormCalculator.get_form_color(form_score)
        
        # Draw current skeleton with form color
        frame = self.draw_colored_skeleton(frame, joints, skeleton_color)
        
        # Draw target skeleton (semi-transparent)
        target_joints = self.calculate_target_joints(
            joints, current_angles, target_angles
        )
        frame = self.draw_target_skeleton(frame, target_joints)
        
        # Calculate angle differences
        differences = self.calculate_angle_differences(current_angles, target_angles)
        tolerance = target_angles.get('tolerance', self.match_threshold)
        position_matched = self.check_position_match(differences, tolerance)
        
        # Draw correction arrows if not matched
        if not position_matched and form_score < 85:
            frame = self.draw_correction_arrows(
                frame, joints, target_joints, differences
            )
        
        # Draw "PERFECT!" banner if matched
        if position_matched or form_score >= 95:
            frame = self.draw_perfect_banner(frame)
        
        # Practice mode indicator
        cv2.rectangle(frame, (5, frame.shape[0] - 70), (250, frame.shape[0] - 40),
                     (100, 100, 255), -1)
        cv2.putText(frame, "PRACTICE MODE - AR ON",
                   (10, frame.shape[0] - 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame, position_matched
    
    def draw_counted_mode(self,
                         frame: np.ndarray,
                         joints: Dict,
                         form_score: float) -> np.ndarray:
        """
        COUNTED MODE: Draw simple colored skeleton based on form
        
        Args:
            frame: Video frame
            joints: Current joint positions
            form_score: Form score 0-100
        
        Returns:
            Annotated frame
        """
        if not joints:
            return frame
        
        # Get form-based color (GREEN/YELLOW/RED)
        skeleton_color = FormCalculator.get_form_color(form_score)
        
        # Draw simple colored skeleton
        frame = self.draw_colored_skeleton(frame, joints, skeleton_color)
        
        # Show form score (optional)
        self.draw_form_score_indicator(frame, form_score)
        
        return frame
    
    # ========================================================================
    # SKELETON DRAWING
    # ========================================================================
    
    def draw_colored_skeleton(self,
                             frame: np.ndarray,
                             joints: Dict,
                             color: Tuple[int, int, int]) -> np.ndarray:
        """
        Draw skeleton with specified color
        
        Args:
            frame: Video frame
            joints: Joint positions {'lk': (x, y), 'rk': (x, y), ...}
            color: BGR color tuple
        """
        # Skeleton lines
        lines = [
            ('ls', 'lh'), ('rs', 'rh'),     # Shoulders to hips
            ('lh', 'lk'), ('rh', 'rk'),     # Hips to knees
            ('lk', 'la'), ('rk', 'ra'),     # Knees to ankles
        ]
        
        for start, end in lines:
            if start in joints and end in joints:
                cv2.line(frame, joints[start], joints[end], color, 3, cv2.LINE_AA)
        
        # Draw joints
        for joint_pos in joints.values():
            cv2.circle(frame, joint_pos, 8, color, -1)
            cv2.circle(frame, joint_pos, 10, (255, 255, 255), 2)
        
        return frame
    
    def draw_target_skeleton(self,
                            frame: np.ndarray,
                            target_joints: Dict,
                            alpha: float = 0.4) -> np.ndarray:
        """
        Draw semi-transparent target skeleton (cyan)
        
        Args:
            frame: Video frame
            target_joints: Target joint positions
            alpha: Transparency (0.0 = invisible, 1.0 = opaque)
        """
        if not target_joints:
            return frame
        
        overlay = frame.copy()
        
        # Skeleton lines
        lines = [
            ('ls', 'lh'), ('rs', 'rh'),
            ('lh', 'lk'), ('rh', 'rk'),
            ('lk', 'la'), ('rk', 'ra'),
        ]
        
        for start, end in lines:
            if start in target_joints and end in target_joints:
                cv2.line(overlay, target_joints[start], target_joints[end],
                        self.target_color, 2, cv2.LINE_AA)
        
        # Draw joints
        for joint_pos in target_joints.values():
            cv2.circle(overlay, joint_pos, 6, self.target_color, -1)
        
        # Blend with original frame
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        
        return frame
    
    # ========================================================================
    # TARGET POSITION CALCULATION
    # ========================================================================
    
    def calculate_target_joints(self,
                                current_joints: Dict,
                                current_angles: Dict,
                                target_angles: Dict) -> Dict:
        """
        Calculate where joints SHOULD be based on target angles
        
        Args:
            current_joints: Current joint positions
            current_angles: Current measured angles
            target_angles: Target angles
        
        Returns:
            Dict of target joint positions
        """
        target_joints = {}
        
        # For squats: adjust knee height based on angle difference
        if 'avg_knee' in target_angles and 'avg_knee' in current_angles:
            angle_diff = target_angles['avg_knee'] - current_angles['avg_knee']
            
            # Vertical adjustment (more bent = lower knees)
            vertical_adjustment = angle_diff * 2  # Scale factor
            
            # Adjust knee positions
            if 'lk' in current_joints:
                lk = current_joints['lk']
                target_joints['lk'] = (lk[0], int(lk[1] - vertical_adjustment))
            
            if 'rk' in current_joints:
                rk = current_joints['rk']
                target_joints['rk'] = (rk[0], int(rk[1] - vertical_adjustment))
        
        # Copy other joints that don't need adjustment
        for key in ['lh', 'rh', 'la', 'ra', 'ls', 'rs']:
            if key in current_joints:
                target_joints[key] = current_joints[key]
        
        return target_joints
    
    def calculate_angle_differences(self,
                                   current_angles: Dict,
                                   target_angles: Dict) -> Dict:
        """
        Calculate differences between current and target angles
        
        Returns:
            Dict of differences {angle_name: difference}
        """
        differences = {}
        
        for angle_name, target_value in target_angles.items():
            if angle_name == 'tolerance':
                continue
            
            if angle_name in current_angles:
                current_value = current_angles[angle_name]
                diff = target_value - current_value
                differences[angle_name] = diff
        
        return differences
    
    def check_position_match(self,
                            differences: Dict,
                            tolerance: float = 8) -> bool:
        """
        Check if all angles are within tolerance
        
        Returns:
            True if all angles within tolerance
        """
        if not differences:
            return False
        
        return all(abs(diff) <= tolerance for diff in differences.values())
    
    # ========================================================================
    # CORRECTION ARROWS
    # ========================================================================
    
    def draw_correction_arrows(self,
                              frame: np.ndarray,
                              current_joints: Dict,
                              target_joints: Dict,
                              differences: Dict) -> np.ndarray:
        """
        Draw arrows showing how to correct position
        
        Args:
            frame: Video frame
            current_joints: Current joint positions
            target_joints: Target joint positions
            differences: Angle differences
        """
        if not differences:
            return frame
        
        # Find most significant correction needed
        max_diff_name = max(differences.items(), key=lambda x: abs(x[1]))
        angle_name, diff_value = max_diff_name
        
        # Only show if difference is significant
        if abs(diff_value) < self.significant_diff:
            return frame
        
        # Determine which joint to annotate
        joint_to_annotate = self._get_joint_for_angle(angle_name, current_joints)
        
        if joint_to_annotate and joint_to_annotate in target_joints:
            current_pos = current_joints[joint_to_annotate]
            target_pos = target_joints[joint_to_annotate]
            
            # Draw arrow
            overlay = frame.copy()
            cv2.arrowedLine(overlay, current_pos, target_pos,
                          self.arrow_color, 4, cv2.LINE_AA, tipLength=0.3)
            cv2.addWeighted(overlay, self.arrow_alpha, frame, 1 - self.arrow_alpha, 0, frame)
            
            # Draw text annotation
            direction = "LOWER" if diff_value < 0 else "RAISE"
            text = f"{direction} {abs(int(diff_value))}°"
            
            # Position text near arrow midpoint
            text_pos = (
                (current_pos[0] + target_pos[0]) // 2 + 20,
                (current_pos[1] + target_pos[1]) // 2
            )
            
            # Background for text
            (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(frame, 
                         (text_pos[0] - 5, text_pos[1] - text_h - 5),
                         (text_pos[0] + text_w + 5, text_pos[1] + 5),
                         (0, 0, 0), -1)
            
            # Text
            cv2.putText(frame, text, text_pos,
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.arrow_color, 2, cv2.LINE_AA)
        
        return frame
    
    def _get_joint_for_angle(self, angle_name: str, joints: Dict) -> Optional[str]:
        """Helper: Get joint to annotate for given angle"""
        if 'knee' in angle_name.lower():
            return 'lk' if 'lk' in joints else None
        elif 'hip' in angle_name.lower():
            return 'lh' if 'lh' in joints else None
        else:
            return 'lk' if 'lk' in joints else None
    
    # ========================================================================
    # VISUAL FEEDBACK
    # ========================================================================
    
    def draw_perfect_banner(self, frame: np.ndarray) -> np.ndarray:
        """Draw pulsing "PERFECT!" banner"""
        banner_text = "✓ PERFECT!"
        (text_w, text_h), _ = cv2.getTextSize(banner_text, 
                                               cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
        
        # Pulsing effect
        self.pulse_phase = (self.pulse_phase + 0.15) % (2 * np.pi)
        pulse_alpha = 0.7 + 0.3 * np.sin(self.pulse_phase)
        
        # Banner background
        overlay = frame.copy()
        cv2.rectangle(overlay,
                     (frame.shape[1]//2 - text_w//2 - 20, 80),
                     (frame.shape[1]//2 + text_w//2 + 20, 130),
                     (0, 255, 0), -1)
        cv2.addWeighted(overlay, pulse_alpha, frame, 1 - pulse_alpha, 0, frame)
        
        # Text
        cv2.putText(frame, banner_text,
                   (frame.shape[1]//2 - text_w//2, 118),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3, cv2.LINE_AA)
        
        return frame
    
    def draw_form_score_indicator(self, frame: np.ndarray, form_score: float):
        """Draw small form score indicator in corner"""
        # Color based on score
        if form_score >= 85:
            color = (0, 255, 0)      # Green
            status = "EXCELLENT"
        elif form_score >= 70:
            color = (0, 255, 255)    # Yellow
            status = "GOOD"
        else:
            color = (0, 0, 255)      # Red
            status = "WATCH FORM"
        
        # Draw indicator
        cv2.rectangle(frame, (frame.shape[1] - 200, 10), (frame.shape[1] - 10, 60), color, -1)
        cv2.putText(frame, f"{int(form_score)}%",
                   (frame.shape[1] - 190, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, status,
                   (frame.shape[1] - 190, 55),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("AR Overlay V2 - Green/Yellow/Red in both modes")
    print("\nKey features:")
    print("- Practice mode: Form-based skeleton color + target overlay + arrows")
    print("- Counted mode: Form-based skeleton color only")
    print("- Colors: Green (≥85), Yellow (70-84), Red (<70)")
    print("\nReady to integrate with exercises!")