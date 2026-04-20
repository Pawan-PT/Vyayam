"""
Unilateral Exercise Handler
Manages left/right side tracking for single-sided exercises

PROBLEM: 
- Exercises like single-leg squats, lunges, single-leg balance detect BOTH legs
- This causes false rep counting, incorrect angles, unstable tracking

SOLUTION:
- Track ONE side at a time
- Prompt user to position camera for left side first
- Complete all reps on left
- Switch to right side
- Complete all reps on right
- Track each side independently
"""

import cv2
from typing import Tuple, Dict, Optional
from enum import Enum


class Side(Enum):
    """Which side is currently being tracked"""
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"  # For bilateral exercises


class UnilateralExerciseHandler:
    """
    Handles side-specific tracking for unilateral exercises
    
    Usage:
        handler = UnilateralExerciseHandler(
            total_reps=10,
            exercise_name="Single Leg Squats"
        )
        
        # Check which side user should position for
        if handler.needs_side_switch:
            show_switch_prompt()
        
        # Get only the relevant side's data
        angles = handler.filter_angles_for_current_side(all_angles)
        joints = handler.filter_joints_for_current_side(all_joints)
    """
    
    def __init__(self, total_reps: int, exercise_name: str = "Exercise"):
        """
        Args:
            total_reps: Total reps per side
            exercise_name: Name for display
        """
        self.total_reps_per_side = total_reps
        self.exercise_name = exercise_name
        
        # Side tracking
        self.current_side = Side.LEFT  # Always start with left
        self.left_reps_completed = 0
        self.right_reps_completed = 0
        
        # Side switch state
        self.needs_side_switch = False
        self.switch_acknowledged = False
        self.awaiting_position = True  # True until first rep on a side
        
        # Form scores per side
        self.left_form_scores = []
        self.right_form_scores = []
    
    # ========================================================================
    # SIDE MANAGEMENT
    # ========================================================================
    
    def get_current_side_name(self) -> str:
        """Get current side as string"""
        return "LEFT" if self.current_side == Side.LEFT else "RIGHT"
    
    def get_reps_completed_current_side(self) -> int:
        """Get reps completed on current side"""
        if self.current_side == Side.LEFT:
            return self.left_reps_completed
        else:
            return self.right_reps_completed
    
    def increment_rep(self, form_score: float):
        """
        Increment rep counter for current side
        
        Args:
            form_score: Form score for this rep
        """
        if self.current_side == Side.LEFT:
            self.left_reps_completed += 1
            self.left_form_scores.append(form_score)
        else:
            self.right_reps_completed += 1
            self.right_form_scores.append(form_score)
        
        # Check if need to switch sides
        if self.get_reps_completed_current_side() >= self.total_reps_per_side:
            if self.current_side == Side.LEFT:
                # Just finished left side
                self.needs_side_switch = True
                self.switch_acknowledged = False
            # If finished right side, exercise is complete (handled by caller)
    
    def acknowledge_switch(self):
        """User acknowledged the side switch prompt"""
        self.switch_acknowledged = True
        self.awaiting_position = True  # Wait for them to reposition
    
    def switch_to_right_side(self):
        """Switch from left to right side"""
        self.current_side = Side.RIGHT
        self.needs_side_switch = False
        self.switch_acknowledged = False
        self.awaiting_position = True
    
    def confirm_positioning(self):
        """User is positioned correctly for current side"""
        self.awaiting_position = False
    
    # ========================================================================
    # ANGLE & JOINT FILTERING
    # ========================================================================
    
    def filter_angles_for_current_side(self, angles: Dict[str, float]) -> Dict[str, float]:
        """
        Filter angles to only include current side
        
        Args:
            angles: All detected angles {
                'left_knee': 120,
                'right_knee': 145,
                'left_hip': 100,
                'right_hip': 98,
                ...
            }
        
        Returns:
            Filtered angles with generic names {
                'knee': 120,  # Only left knee if current_side == LEFT
                'hip': 100,
                ...
            }
        """
        filtered = {}
        
        if self.current_side == Side.LEFT:
            # Use only left side angles
            for key, value in angles.items():
                if 'left' in key.lower():
                    # Rename to generic (remove 'left_' prefix)
                    generic_key = key.replace('left_', '').replace('Left', '')
                    filtered[generic_key] = value
        
        elif self.current_side == Side.RIGHT:
            # Use only right side angles
            for key, value in angles.items():
                if 'right' in key.lower():
                    # Rename to generic (remove 'right_' prefix)
                    generic_key = key.replace('right_', '').replace('Right', '')
                    filtered[generic_key] = value
        
        # Also copy any bilateral angles (back, torso, etc.)
        for key, value in angles.items():
            if 'left' not in key.lower() and 'right' not in key.lower():
                filtered[key] = value
        
        return filtered
    
    def filter_joints_for_current_side(self, joints: Dict[str, Tuple]) -> Dict[str, Tuple]:
        """
        Filter joint positions to only include current side
        
        Args:
            joints: All joint positions {
                'lk': (x, y),  # left knee
                'rk': (x, y),  # right knee
                'lh': (x, y),  # left hip
                'rh': (x, y),  # right hip
                ...
            }
        
        Returns:
            Filtered joints with generic names {
                'k': (x, y),   # knee (left or right based on current_side)
                'h': (x, y),   # hip
                ...
            }
        """
        filtered = {}
        
        if self.current_side == Side.LEFT:
            # Use only left side joints
            for key, value in joints.items():
                if key.startswith('l') and len(key) == 2:
                    # Generic name (remove 'l' prefix)
                    generic_key = key[1]  # 'lk' → 'k'
                    filtered[generic_key] = value
                    # Also keep original key for compatibility
                    filtered[key] = value
        
        elif self.current_side == Side.RIGHT:
            # Use only right side joints
            for key, value in joints.items():
                if key.startswith('r') and len(key) == 2:
                    # Generic name (remove 'r' prefix)
                    generic_key = key[1]  # 'rk' → 'k'
                    filtered[generic_key] = value
                    # Also keep original key
                    filtered[key] = value
        
        # Copy any central joints (nose, shoulders for reference)
        for key, value in joints.items():
            if len(key) > 2 or (key not in ['lk', 'rk', 'lh', 'rh', 'la', 'ra', 'ls', 'rs']):
                filtered[key] = value
        
        return filtered
    
    # ========================================================================
    # UI HELPERS
    # ========================================================================
    
    def get_switch_prompt_message(self) -> str:
        """Get message to display when switching sides"""
        if self.current_side == Side.LEFT:
            return f"LEFT SIDE COMPLETE! ({self.left_reps_completed}/{self.total_reps_per_side} reps)\n\n" \
                   f"Position camera for RIGHT SIDE\n" \
                   f"Press SPACE when ready"
        else:
            return "Exercise complete! Both sides done."
    
    def get_positioning_prompt_message(self) -> str:
        """Get message to display for initial positioning"""
        return f"Position camera for {self.get_current_side_name()} SIDE\n" \
               f"Make sure {self.get_current_side_name().lower()} leg is visible\n" \
               f"Press SPACE when ready"
    
    def draw_side_indicator(self, frame, x=10, y=60):
        """
        Draw current side indicator on frame
        
        Args:
            frame: Video frame
            x, y: Position for text
        """
        side_name = self.get_current_side_name()
        reps = self.get_reps_completed_current_side()
        
        # Color based on side
        color = (0, 255, 255) if self.current_side == Side.LEFT else (255, 165, 0)  # Cyan for left, orange for right
        
        # Background box
        cv2.rectangle(frame, (x, y - 30), (x + 250, y + 5), (0, 0, 0), -1)
        
        # Text
        text = f"{side_name} SIDE: {reps}/{self.total_reps_per_side}"
        cv2.putText(frame, text, (x + 10, y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    
    def draw_switch_prompt(self, frame):
        """Draw full-screen side switch prompt"""
        h, w = frame.shape[:2]
        
        # Semi-transparent overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Message
        message = self.get_switch_prompt_message()
        lines = message.split('\n')
        
        y = h // 2 - 50
        for line in lines:
            if line.strip():
                (text_w, text_h), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
                x = (w - text_w) // 2
                cv2.putText(frame, line, (x, y),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                y += 50
    
    def draw_positioning_prompt(self, frame):
        """Draw initial positioning prompt"""
        h, w = frame.shape[:2]
        
        # Semi-transparent overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Message
        message = self.get_positioning_prompt_message()
        lines = message.split('\n')
        
        y = h // 2 - 50
        for line in lines:
            if line.strip():
                (text_w, text_h), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
                x = (w - text_w) // 2
                cv2.putText(frame, line, (x, y),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                y += 50
    
    # ========================================================================
    # STATS
    # ========================================================================
    
    def is_complete(self) -> bool:
        """Check if both sides are complete"""
        return (self.left_reps_completed >= self.total_reps_per_side and
                self.right_reps_completed >= self.total_reps_per_side)

    def check_asymmetry_safe(self) -> Tuple[bool, str]:
        """
        Check whether completed reps show a safe bilateral balance.

        Uses Limb Symmetry Index (LSI) thresholds:
          <10%  → safe, no block
          10-20% → mild asymmetry, warn but don't block
          >20%  → significant asymmetry, block next set

        Returns:
            (is_safe: bool, message: str)
        """
        total = self.left_reps_completed + self.right_reps_completed
        if total == 0:
            return True, ''

        diff = abs(self.left_reps_completed - self.right_reps_completed)
        asymmetry_pct = diff / total * 100

        if asymmetry_pct > 20:
            weaker = 'LEFT' if self.left_reps_completed < self.right_reps_completed else 'RIGHT'
            return False, (
                f'Significant asymmetry ({asymmetry_pct:.0f}%) — '
                f'{weaker} side deficit. Add extra set on {weaker} side before progressing.'
            )
        elif asymmetry_pct > 10:
            weaker = 'LEFT' if self.left_reps_completed < self.right_reps_completed else 'RIGHT'
            return True, f'Mild asymmetry ({asymmetry_pct:.0f}%) — prioritise {weaker} side.'
        return True, ''

    def get_stats(self) -> Dict:
        """Get complete statistics"""
        left_avg = (sum(self.left_form_scores) / len(self.left_form_scores) 
                   if self.left_form_scores else 0)
        right_avg = (sum(self.right_form_scores) / len(self.right_form_scores) 
                    if self.right_form_scores else 0)
        
        return {
            'left_reps': self.left_reps_completed,
            'right_reps': self.right_reps_completed,
            'left_avg_form': round(left_avg, 1),
            'right_avg_form': round(right_avg, 1),
            'left_form_scores': self.left_form_scores,
            'right_form_scores': self.right_form_scores,
            'complete': self.is_complete()
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("UNILATERAL EXERCISE HANDLER - Example Usage")
    print("="*70)
    
    # Create handler for single-leg squats (10 reps per side)
    handler = UnilateralExerciseHandler(
        total_reps=10,
        exercise_name="Single Leg Squats"
    )
    
    print("\n1. INITIAL STATE")
    print(f"Current side: {handler.get_current_side_name()}")
    print(f"Awaiting position: {handler.awaiting_position}")
    print(f"Needs switch: {handler.needs_side_switch}")
    
    # Simulate positioning
    print("\n2. USER POSITIONS FOR LEFT SIDE")
    handler.confirm_positioning()
    print(f"Awaiting position: {handler.awaiting_position}")
    
    # Simulate completing 10 reps on left
    print("\n3. COMPLETING LEFT SIDE REPS")
    for i in range(10):
        handler.increment_rep(form_score=85 + i)
        print(f"Left rep {i+1} completed (form: {85+i}%)")
    
    print(f"\nLeft reps: {handler.left_reps_completed}")
    print(f"Needs switch: {handler.needs_side_switch}")
    
    # Switch to right
    print("\n4. SWITCHING TO RIGHT SIDE")
    handler.acknowledge_switch()
    handler.switch_to_right_side()
    print(f"Current side: {handler.get_current_side_name()}")
    print(f"Awaiting position: {handler.awaiting_position}")
    
    # Position and complete right side
    print("\n5. USER POSITIONS FOR RIGHT SIDE")
    handler.confirm_positioning()
    
    print("\n6. COMPLETING RIGHT SIDE REPS")
    for i in range(10):
        handler.increment_rep(form_score=80 + i)
        print(f"Right rep {i+1} completed (form: {80+i}%)")
    
    # Final stats
    print("\n7. FINAL STATS")
    stats = handler.get_stats()
    print(f"Left reps: {stats['left_reps']}")
    print(f"Right reps: {stats['right_reps']}")
    print(f"Left avg form: {stats['left_avg_form']}%")
    print(f"Right avg form: {stats['right_avg_form']}%")
    print(f"Complete: {stats['complete']}")
    
    print("\n" + "="*70)
    print("✅ Handler manages left/right tracking automatically!")
    print("="*70)