"""
FORM TRACKING SYSTEM
Real-time exercise form analysis with rep counting
Green/Yellow/Red classification
"""

from .database_schema import RepData, SetData, FormQuality
from typing import Tuple, List
import random  # Simulating AI vision, replace with real CV later


class FormAnalyzer:
    """
    Analyzes exercise form in real-time
    
    Form Score = (angle_accuracy * 0.5) + (stability * 0.3) + (tempo_control * 0.2)
    
    Classification:
    - GREEN (counted): Form score ≥ 75%
    - YELLOW (not counted): Form score 50-74%
    - RED (stop set): Form score < 50%
    """
    
    def __init__(self):
        # Form thresholds
        self.green_threshold = 0.75  # 75%
        self.yellow_threshold = 0.50  # 50%
        
        # Feedback messages for common form issues
        self.feedback_library = {
            'angle_low': "Lower your hips more",
            'angle_high': "Don't go too deep, maintain control",
            'angle_asymmetric': "Keep your hips level",
            'stability_poor': "Engage your core, reduce wobbling",
            'stability_knee_valgus': "Push your knees outward",
            'tempo_too_fast': "Slow down, control the movement",
            'tempo_too_slow': "Move with more confidence",
            'back_rounding': "Keep your back straight",
            'heels_lifting': "Keep your heels on the ground"
        }
    
    
    def analyze_rep_form(
        self,
        exercise_id: str,
        rep_number: int,
        frame_data: dict = None  # Would come from CV system
    ) -> RepData:
        """
        Analyze a single repetition
        
        In real implementation, frame_data would contain:
        - Joint angles from pose estimation
        - Movement velocity
        - Center of mass tracking
        - etc.
        
        For now, simulating random form scores
        """
        
        # SIMULATION (replace with real CV analysis)
        # In real system: analyze frame_data and compute these metrics
        angle_accuracy = random.uniform(0.6, 1.0)  # How close to ideal angles
        stability = random.uniform(0.5, 1.0)       # Wobbling/balance
        tempo_control = random.uniform(0.7, 1.0)   # Speed consistency
        
        # Calculate form score
        form_score = (
            angle_accuracy * 0.5 +
            stability * 0.3 +
            tempo_control * 0.2
        )
        
        # Classify quality
        if form_score >= self.green_threshold:
            quality = FormQuality.GREEN
        elif form_score >= self.yellow_threshold:
            quality = FormQuality.YELLOW
        else:
            quality = FormQuality.RED
        
        # Generate feedback
        feedback = self._generate_feedback(
            angle_accuracy,
            stability,
            tempo_control,
            quality
        )
        
        rep_data = RepData(
            rep_number=rep_number,
            form_score=form_score * 100,  # Convert to percentage
            form_quality=quality,
            angle_accuracy=angle_accuracy,
            stability=stability,
            tempo_control=tempo_control,
            feedback_given=feedback
        )
        
        return rep_data
    
    
    def _generate_feedback(
        self,
        angle_accuracy: float,
        stability: float,
        tempo_control: float,
        quality: FormQuality
    ) -> List[str]:
        """
        Generate voice/text feedback based on form issues
        """
        feedback = []
        
        # Only give feedback for yellow/red reps
        if quality == FormQuality.GREEN:
            return ["Great form!"]
        
        # Prioritize most critical issue
        issues = [
            (angle_accuracy, 'angle'),
            (stability, 'stability'),
            (tempo_control, 'tempo')
        ]
        issues.sort(key=lambda x: x[0])  # Lowest score first
        
        worst_metric, metric_name = issues[0]
        
        if metric_name == 'angle' and worst_metric < 0.7:
            feedback.append(self.feedback_library['angle_low'])
        elif metric_name == 'stability' and worst_metric < 0.6:
            feedback.append(self.feedback_library['stability_poor'])
        elif metric_name == 'tempo' and worst_metric < 0.7:
            feedback.append(self.feedback_library['tempo_too_fast'])
        else:
            feedback.append("Focus on controlled movement")
        
        return feedback
    
    
    def analyze_set(
        self,
        exercise_id: str,
        set_number: int,
        prescribed_reps: int,
        max_attempts: int = None
    ) -> SetData:
        """
        Analyze a complete set
        
        Tracks reps until:
        - Prescribed reps completed (green reps only), OR
        - Max attempts reached, OR
        - RED rep occurs (stop for safety)
        """
        
        if max_attempts is None:
            max_attempts = prescribed_reps * 2  # Allow up to 2x attempts
        
        set_data = SetData(
            set_number=set_number,
            prescribed_reps=prescribed_reps,
            reps_attempted=0,
            reps_completed_green=0,
            reps_yellow=0,
            reps_red=0,
            rep_data=[]
        )
        
        # Simulate set execution
        rep_number = 1
        
        while set_data.reps_completed_green < prescribed_reps and set_data.reps_attempted < max_attempts:
            # Analyze this rep
            rep_data = self.analyze_rep_form(exercise_id, rep_number)
            
            set_data.rep_data.append(rep_data)
            set_data.reps_attempted += 1
            
            # Count by quality
            if rep_data.form_quality == FormQuality.GREEN:
                set_data.reps_completed_green += 1
            elif rep_data.form_quality == FormQuality.YELLOW:
                set_data.reps_yellow += 1
            elif rep_data.form_quality == FormQuality.RED:
                set_data.reps_red += 1
                # RED rep = stop set immediately
                set_data.stopped_reason = "form_failure"
                break
            
            rep_number += 1
        
        # Calculate set-level metrics
        if set_data.rep_data:
            set_data.average_form_score = sum(r.form_score for r in set_data.rep_data) / len(set_data.rep_data)
        
        set_data.set_completed = (set_data.reps_completed_green >= prescribed_reps)
        
        # If didn't complete and no red rep, assume fatigue
        if not set_data.set_completed and not set_data.stopped_reason:
            set_data.stopped_reason = "fatigue"
        
        return set_data
    
    
    def check_if_practice_mode_needed(
        self,
        set_data: SetData
    ) -> bool:
        """
        Determine if patient needs practice mode
        
        Trigger if:
        - Zero green reps, OR
        - >50% red reps
        """
        
        if set_data.reps_completed_green == 0:
            return True
        
        if set_data.reps_attempted > 0:
            red_percentage = set_data.reps_red / set_data.reps_attempted
            if red_percentage > 0.5:
                return True
        
        return False


class PracticeModeCoordinator:
    """
    Handles practice mode when patient can't do exercise with good form
    """
    
    def __init__(self):
        self.form_analyzer = FormAnalyzer()
    
    
    def conduct_practice_session(
        self,
        exercise_id: str,
        max_practice_reps: int = 5
    ) -> Tuple[bool, int]:
        """
        Run practice mode
        
        Steps:
        1. Show demo video
        2. Patient attempts to copy
        3. After each rep, ask: "Can you do this?" 
        4. If "No" → go back one level
        5. If "Yes" and form improves → continue
        
        Returns: (can_do_exercise, practice_reps_completed)
        """
        
        print(f"\n🎬 PRACTICE MODE: {exercise_id}")
        print("=" * 50)
        print("Watch the demo video carefully...")
        print("Try to copy the movement. We'll give you feedback.")
        print()
        
        practice_reps_completed = 0
        can_do = False
        
        for rep in range(1, max_practice_reps + 1):
            print(f"\n📹 Practice Rep {rep}/{max_practice_reps}")
            
            # Analyze practice rep
            rep_data = self.form_analyzer.analyze_rep_form(exercise_id, rep)
            
            print(f"   Form Score: {rep_data.form_score:.1f}%")
            print(f"   Quality: {rep_data.form_quality.value.upper()}")
            print(f"   Feedback: {rep_data.feedback_given[0]}")
            
            practice_reps_completed += 1
            
            # If form is good enough, they can do it
            if rep_data.form_quality == FormQuality.GREEN:
                print("\n   ✅ Great! You've got it. Ready to continue.")
                can_do = True
                break
            
            # Ask patient if they can do this
            # In real app: button press
            # For simulation: check if form improved
            if rep > 1 and rep_data.form_score > 60:
                print("\n   📊 Your form is improving!")
                print("   ❓ Can you do this exercise?")
                print("      [1] Yes, I can")
                print("      [2] No, too difficult")
                
                # Simulate patient response
                if rep_data.form_score >= 70:
                    print("   → Patient: Yes, I can")
                    can_do = True
                    break
                else:
                    print("   → Patient: No, too difficult")
                    print("\n   ⬅️  Going back one level...")
                    break
        
        return can_do, practice_reps_completed


# ============================================================================
# VOICE GUIDANCE SYSTEM
# ============================================================================

class VoiceGuidance:
    """
    Provides real-time voice feedback during exercises
    """
    
    def __init__(self):
        self.form_analyzer = FormAnalyzer()
    
    
    def provide_guidance(
        self,
        rep_data: RepData
    ) -> None:
        """
        Speak feedback to patient in real-time
        
        In real system: Convert text to speech
        For now: Print to console
        """
        
        if rep_data.form_quality == FormQuality.GREEN:
            print(f"🟢 Rep {rep_data.rep_number} ✓")
        elif rep_data.form_quality == FormQuality.YELLOW:
            print(f"🟡 Rep {rep_data.rep_number} - {rep_data.feedback_given[0]}")
        else:  # RED
            print(f"🔴 Rep {rep_data.rep_number} - STOP! {rep_data.feedback_given[0]}")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("FORM TRACKING SYSTEM - DEMO")
    print("=" * 70)
    
    analyzer = FormAnalyzer()
    practice_mode = PracticeModeCoordinator()
    voice = VoiceGuidance()
    
    # EXAMPLE 1: Good form set
    print("\n📋 EXAMPLE 1: Patient with Good Form")
    print("-" * 70)
    print("Exercise: Normal Squat | Prescribed: 10 reps")
    print()
    
    set_data = analyzer.analyze_set(
        exercise_id="normal_squat",
        set_number=1,
        prescribed_reps=10
    )
    
    for rep in set_data.rep_data:
        voice.provide_guidance(rep)
    
    print(f"\n📊 SET SUMMARY:")
    print(f"   Attempted: {set_data.reps_attempted} reps")
    print(f"   🟢 Green (counted): {set_data.reps_completed_green}")
    print(f"   🟡 Yellow (not counted): {set_data.reps_yellow}")
    print(f"   🔴 Red (stop): {set_data.reps_red}")
    print(f"   Average Form: {set_data.average_form_score:.1f}%")
    print(f"   ✅ Set Completed: {set_data.set_completed}")
    
    # EXAMPLE 2: Poor form → Practice mode
    print("\n\n📋 EXAMPLE 2: Patient Needs Practice Mode")
    print("-" * 70)
    
    # Simulate a set with no green reps
    bad_set = SetData(
        set_number=1,
        prescribed_reps=10,
        reps_attempted=3,
        reps_completed_green=0,
        reps_yellow=2,
        reps_red=1
    )
    
    needs_practice = analyzer.check_if_practice_mode_needed(bad_set)
    
    if needs_practice:
        print("\n⚠️  No green reps detected. Entering PRACTICE MODE...")
        
        can_do, practice_reps = practice_mode.conduct_practice_session(
            exercise_id="spanish_squat",
            max_practice_reps=5
        )
        
        if can_do:
            print(f"\n✅ Patient can do exercise after {practice_reps} practice reps")
            print("   Returning to normal set...")
        else:
            print(f"\n⬅️  Patient unable to perform exercise safely")
            print("   Recommendation: Go back one level")
    
    print("\n" + "=" * 70)
    print("✅ Form Tracking System Ready!")
    print("=" * 70)
