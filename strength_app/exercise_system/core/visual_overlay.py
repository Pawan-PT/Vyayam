"""
Visual feedback overlay - UPDATED with AR support methods
EXACT COPY from working code + NEW helper methods for AR
"""

import cv2
import numpy as np
from .data_models import FormStatus


class JointHighlighter:
    """
    EXACT COPY from your working code + NEW AR helper methods
    """
    def __init__(self):
        self.colors = {
            FormStatus.CORRECT: (0, 255, 0),
            FormStatus.NEEDS_ADJUSTMENT: (0, 255, 255),
            FormStatus.INCORRECT: (0, 0, 255)
        }
        self.pulse = 0
    
    def _get_color(self, status):
        if isinstance(status, FormStatus):
            return self.colors.get(status, (128, 128, 128))
        return (128, 128, 128)
    
    def draw_joint(self, frame, pos, status, pulse=False):
        """Original method - preserved"""
        color = self._get_color(status)
        if pulse and status == FormStatus.INCORRECT:
            self.pulse = (self.pulse + 0.3) % (2 * np.pi)
            radius = int(11 + 5 * np.sin(self.pulse))
        else:
            radius = 10
        cv2.circle(frame, pos, radius, color, -1)
        cv2.circle(frame, pos + 2, (255, 255, 255), 2)
    
    def draw_line(self, frame, p1, p2, status):
        """Original method - preserved"""
        color = self._get_color(status)
        cv2.line(frame, p1, p2, color, 2)
    
    def draw_feedback(self, frame, feedback, warnings):
        """Original method - preserved"""
        y = 30
        
        critical = [f for f in feedback.values() if f.status == FormStatus.INCORRECT]
        if critical:
            cv2.rectangle(frame, (5, 5), (250, 50), (0, 0, 255), -1)
            cv2.putText(frame, "⚠️ FIX FORM", (15, 35), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            y = 60
        
        for warning in warnings[:3]:
            (w, h), _ = cv2.getTextSize(warning, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            bg = (0, 0, 200) if critical else (50, 50, 50)
            cv2.rectangle(frame, (5, y-h-5), (min(w+15, frame.shape[1]-5), y+5), bg, -1)
            cv2.putText(frame, warning, (10, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            y += 25
    
    # ========================================================================
    # NEW METHODS FOR AR SUPPORT
    # ========================================================================
    
    def draw_transparent_joint(self, frame, pos, color, alpha=0.5, radius=12):
        """
        Draw semi-transparent joint for AR overlay
        
        Args:
            frame: Video frame to draw on
            pos: Joint position (x, y)
            color: Joint color (B, G, R)
            alpha: Transparency (0.0 = invisible, 1.0 = opaque)
            radius: Joint circle radius
        """
        overlay = frame.copy()
        cv2.circle(overlay, pos, radius, color, -1)
        cv2.circle(overlay, pos, radius + 2, (255, 255, 255), 2)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    
    def draw_transparent_line(self, frame, p1, p2, color, alpha=0.5, thickness=3):
        """
        Draw semi-transparent line for AR skeleton
        
        Args:
            frame: Video frame to draw on
            p1: Start point (x, y)
            p2: End point (x, y)
            color: Line color (B, G, R)
            alpha: Transparency (0.0 = invisible, 1.0 = opaque)
            thickness: Line thickness
        """
        overlay = frame.copy()
        cv2.line(overlay, p1, p2, color, thickness, cv2.LINE_AA)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    
    def draw_arrow_with_text(self, frame, start, end, text, color=(255, 165, 0), alpha=0.8):
        """
        Draw arrow with annotation text for corrections
        
        Args:
            frame: Video frame to draw on
            start: Arrow start position (x, y)
            end: Arrow end position (x, y)
            text: Annotation text (e.g., "LOWER 10°")
            color: Arrow color (B, G, R)
            alpha: Transparency
        """
        # Draw arrow
        overlay = frame.copy()
        cv2.arrowedLine(overlay, start, end, color, 4, cv2.LINE_AA, tipLength=0.3)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        
        # Calculate text position (near arrow midpoint)
        mid_point = ((start[0] + end[0]) // 2 + 20, (start[1] + end[1]) // 2)
        
        # Draw text background
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(frame, 
                     (mid_point[0] - 5, mid_point[1] - text_h - 5),
                     (mid_point[0] + text_w + 5, mid_point[1] + 5),
                     (0, 0, 0), -1)
        
        # Draw text
        cv2.putText(frame, text, mid_point,
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
    
    def draw_pulsing_circle(self, frame, pos, base_radius=15, color=(0, 255, 0), phase=0):
        """
        Draw pulsing circle for highlighting matched position
        
        Args:
            frame: Video frame to draw on
            pos: Circle center (x, y)
            base_radius: Base circle radius
            color: Circle color (B, G, R)
            phase: Animation phase (0 to 2π)
        """
        # Calculate pulsing radius
        radius = int(base_radius + 5 * np.sin(phase))
        alpha = 0.7 + 0.3 * np.sin(phase)
        
        # Draw pulsing circle
        overlay = frame.copy()
        cv2.circle(overlay, pos, radius, color, -1)
        cv2.circle(overlay, pos, radius + 2, (255, 255, 255), 2)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    
    def draw_banner(self, frame, text, color=(0, 255, 0), position='top'):
        """
        Draw banner with text (for announcements like "PERFECT POSITION!")
        
        Args:
            frame: Video frame to draw on
            text: Banner text
            color: Banner background color (B, G, R)
            position: 'top' or 'bottom'
        """
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 3)
        
        # Calculate position
        center_x = frame.shape[1] // 2
        if position == 'top':
            y_pos = 80
        else:
            y_pos = frame.shape[0] - 80
        
        # Draw background
        overlay = frame.copy()
        cv2.rectangle(overlay,
                     (center_x - text_w//2 - 20, y_pos - text_h - 10),
                     (center_x + text_w//2 + 20, y_pos + 10),
                     color, -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        # Draw text
        cv2.putText(frame, text,
                   (center_x - text_w//2, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3, cv2.LINE_AA)
    
    def draw_angle_arc(self, frame, center, start_angle, end_angle, radius=50, color=(255, 255, 0)):
        """
        Draw angle arc to visualize angle measurements
        
        Args:
            frame: Video frame to draw on
            center: Arc center point (x, y)
            start_angle: Start angle in degrees
            end_angle: End angle in degrees
            radius: Arc radius
            color: Arc color (B, G, R)
        """
        overlay = frame.copy()
        
        # Convert angles to OpenCV format (starts from positive x-axis, counterclockwise)
        cv2.ellipse(overlay, center, (radius, radius), 0, 
                   -start_angle, -end_angle, color, 2, cv2.LINE_AA)
        
        # Draw angle value
        mid_angle = (start_angle + end_angle) / 2
        text = f"{int(abs(end_angle - start_angle))}°"
        text_pos = (
            int(center[0] + (radius + 15) * np.cos(np.radians(mid_angle))),
            int(center[1] - (radius + 15) * np.sin(np.radians(mid_angle)))
        )
        
        cv2.putText(overlay, text, text_pos,
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
        
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)