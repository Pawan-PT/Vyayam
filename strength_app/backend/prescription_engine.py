"""
PRESCRIPTION ENGINE
Handles both AI auto-prescription and therapist manual prescription
"""

from .database_schema import (
    PatientProfile, GateTestSession, ExerciseData, ExerciseCategory,
    PrescriptionMode, TherapistPrescription, CapabilityLevel
)
from typing import List, Dict, Tuple
from datetime import datetime


class PrescriptionEngine:
    """
    Main prescription engine
    Two modes: AI_AUTO and THERAPIST_MANUAL
    """
    
    def __init__(self):
        # Exercise progression ladders (from easiest to hardest)
        self.exercise_progressions = {
            'squat': [
                'wall_sit',           # Phase 0
                'chair_squat',        # Phase 0
                'partial_squat',      # Phase 1 low
                'normal_squat',       # Phase 1 standard
                'spanish_squat',      # Phase 1 high / Phase 2 low
                'decline_squat',      # Phase 2
                'bulgarian_split_squat',  # Phase 2 high / Phase 3 low
                'single_leg_squat',   # Phase 3
                'jumping_squat'       # Phase 3 high / advanced
            ],
            'deadlift': [
                'hip_hinge_practice',     # Phase 0
                'romanian_deadlift_light', # Phase 1 low
                'conventional_deadlift',  # Phase 1 standard
                'deficit_deadlift',       # Phase 2
                'single_leg_deadlift',    # Phase 3
                'power_clean'             # Advanced
            ],
            'rowing': [
                'assisted_row',           # Phase 0
                'bent_over_row_light',    # Phase 1 low
                'bent_over_row',          # Phase 1 standard
                'single_arm_row',         # Phase 2
                'renegade_row',           # Phase 3
                'weighted_pullup'         # Advanced
            ],
            'lunge': [
                'static_lunge',           # Phase 1 low
                'walking_lunge',          # Phase 1 standard
                'reverse_lunge',          # Phase 2
                'lateral_lunge',          # Phase 2
                'jumping_lunge',          # Phase 3
                'curtsy_lunge'            # Advanced
            ]
        }
        
        # Accessory exercises added based on fitness level
        self.accessories = {
            'beginner': ['bicep_curl_light', 'tricep_extension_light'],
            'intermediate': ['bicep_curl', 'tricep_extension', 'rotational_swing_light'],
            'advanced': ['bicep_curl_heavy', 'tricep_extension_heavy', 'rotational_swing', 'oblique_rotation']
        }
        
        # Stretching exercises (always included)
        self.stretching_exercises = [
            'hamstring_stretch',
            'quad_stretch',
            'hip_flexor_stretch',
            'shoulder_stretch',
            'lower_back_stretch'
        ]
        
        # Cardio options based on capability
        self.cardio_options = {
            CapabilityLevel.CANNOT_DO: ['walking_slow', 'seated_cycling'],
            CapabilityLevel.STRUGGLING: ['walking_moderate', 'cycling_light'],
            CapabilityLevel.MANAGEABLE: ['jogging_light', 'cycling_moderate', 'rowing_cardio'],
            CapabilityLevel.EASY: ['running', 'cycling_intense', 'HIIT_light']
        }
    
    
    def get_starting_exercise_from_phase(
        self,
        exercise_type: str,
        phase: str
    ) -> str:
        """
        Get the starting exercise based on gate test phase
        """
        progression = self.exercise_progressions.get(exercise_type, [])
        
        phase_map = {
            'phase_0': 0,              # Wall sit / chair squat
            'phase_1_low': 2,          # Partial squat
            'phase_1_standard': 3,     # Normal squat
            'phase_1_high': 4          # Spanish squat (start high)
        }
        
        index = phase_map.get(phase, 3)  # Default to standard
        
        if index < len(progression):
            return progression[index]
        else:
            return progression[-1]
    
    
    def get_next_exercise_level(
        self,
        exercise_type: str,
        current_exercise: str
    ) -> Tuple[str, bool]:
        """
        Get next exercise in progression ladder
        Returns: (next_exercise, is_at_max)
        """
        progression = self.exercise_progressions.get(exercise_type, [])
        
        try:
            current_index = progression.index(current_exercise)
            if current_index < len(progression) - 1:
                return progression[current_index + 1], False
            else:
                return current_exercise, True  # Already at max
        except ValueError:
            # Exercise not in progression, return as is
            return current_exercise, True
    
    
    def get_previous_exercise_level(
        self,
        exercise_type: str,
        current_exercise: str
    ) -> Tuple[str, bool]:
        """
        Go back one level in progression ladder
        Returns: (previous_exercise, is_at_min)
        """
        progression = self.exercise_progressions.get(exercise_type, [])
        
        try:
            current_index = progression.index(current_exercise)
            if current_index > 0:
                return progression[current_index - 1], False
            else:
                return current_exercise, True  # Already at minimum
        except ValueError:
            return current_exercise, True
    
    
    def prescribe_ai_auto(
        self,
        patient: PatientProfile,
        gate_session: GateTestSession,
        week_number: int = 1
    ) -> Dict[str, List[Dict]]:
        """
        AI AUTO MODE: Prescribe exercises based on gate test results
        
        Returns structured prescription:
        {
            'stretching': [list of exercises],
            'strength': [list of exercises],
            'cardio': [list of exercises]
        }
        """
        
        prescription = {
            'stretching': [],
            'strength': [],
            'cardio': []
        }
        
        # 1. STRETCHING (always the same, 5 exercises)
        for stretch in self.stretching_exercises:
            prescription['stretching'].append({
                'exercise_id': stretch,
                'exercise_name': stretch.replace('_', ' ').title(),
                'sets': 2,
                'reps': 1,  # Hold-based
                'hold_duration': 30,  # seconds
                'rest': 30,
                'category': ExerciseCategory.STRETCHING
            })
        
        # 2. STRENGTH (based on gate test results)
        for test_result in gate_session.tests_completed:
            if test_result.category == ExerciseCategory.CARDIO:
                continue  # Handle cardio separately
            
            # Determine exercise type
            exercise_type_map = {
                ExerciseCategory.LOWER_BODY: 'squat',
                ExerciseCategory.POSTERIOR_CHAIN: 'deadlift',
                ExerciseCategory.UPPER_BODY: 'rowing'
            }
            exercise_type = exercise_type_map.get(test_result.category)
            
            if not exercise_type:
                continue
            
            # Get starting exercise
            starting_exercise = self.get_starting_exercise_from_phase(
                exercise_type,
                test_result.starting_phase
            )
            
            # Add to prescription
            prescription['strength'].append({
                'exercise_id': starting_exercise,
                'exercise_name': starting_exercise.replace('_', ' ').title(),
                'sets': test_result.starting_sets,
                'reps': test_result.starting_reps,
                'hold_duration': 0,
                'rest': 60,
                'category': test_result.category,
                'progression_type': exercise_type  # Track which ladder this belongs to
            })
        
        # 3. Add ACCESSORIES based on overall fitness
        overall_fitness = gate_session.overall_fitness_level
        accessories = self.accessories.get(overall_fitness, [])
        
        for accessory in accessories[:2]:  # Limit to 2 accessories
            prescription['strength'].append({
                'exercise_id': accessory,
                'exercise_name': accessory.replace('_', ' ').title(),
                'sets': 2,
                'reps': 12,
                'hold_duration': 0,
                'rest': 45,
                'category': ExerciseCategory.UPPER_BODY,  # Most accessories are upper body
                'progression_type': 'accessory'
            })
        
        # 4. CARDIO (based on cardio gate test if available)
        cardio_capability = CapabilityLevel.MANAGEABLE  # Default
        
        for test_result in gate_session.tests_completed:
            if test_result.category == ExerciseCategory.CARDIO:
                cardio_capability = test_result.capability_level
                break
        
        # Select cardio exercises
        cardio_exercises = self.cardio_options.get(cardio_capability, ['walking_moderate'])
        
        for cardio in cardio_exercises[:2]:  # Max 2 cardio exercises
            prescription['cardio'].append({
                'exercise_id': cardio,
                'exercise_name': cardio.replace('_', ' ').title(),
                'sets': 1,
                'reps': 1,  # Duration-based
                'hold_duration': 600,  # 10 minutes default
                'rest': 0,
                'category': ExerciseCategory.CARDIO
            })
        
        return prescription
    
    
    def prescribe_therapist_manual(
        self,
        therapist_prescription: TherapistPrescription
    ) -> Dict[str, List[Dict]]:
        """
        THERAPIST MANUAL MODE: Use therapist's exact prescription
        
        Therapist provides:
        - Exercise IDs
        - Sets, reps, hold duration, rest
        
        System just organizes them into stretching/strength/cardio
        """
        
        prescription = {
            'stretching': [],
            'strength': [],
            'cardio': []
        }
        
        for exercise in therapist_prescription.exercises:
            # Determine category (therapist should specify, or we infer)
            category = exercise.get('category', ExerciseCategory.LOWER_BODY)
            
            exercise_data = {
                'exercise_id': exercise['exercise_id'],
                'exercise_name': exercise.get('exercise_name', exercise['exercise_id'].replace('_', ' ').title()),
                'sets': exercise['sets'],
                'reps': exercise['reps'],
                'hold_duration': exercise.get('hold', 0),
                'rest': exercise.get('rest', 60),
                'category': category
            }
            
            # Categorize
            if category == ExerciseCategory.STRETCHING:
                prescription['stretching'].append(exercise_data)
            elif category == ExerciseCategory.CARDIO:
                prescription['cardio'].append(exercise_data)
            else:
                prescription['strength'].append(exercise_data)
        
        return prescription
    
    
    def adjust_prescription_for_regression(
        self,
        current_prescription: Dict[str, List[Dict]],
        exercise_to_regress: str
    ) -> Dict[str, List[Dict]]:
        """
        Patient not comfortable → go back 1 level
        
        Find the exercise and replace with previous level
        """
        
        for section in ['strength', 'cardio']:
            for i, ex in enumerate(current_prescription[section]):
                if ex['exercise_id'] == exercise_to_regress:
                    # Find progression type
                    progression_type = ex.get('progression_type')
                    
                    if progression_type and progression_type in self.exercise_progressions:
                        # Go back one level
                        prev_exercise, is_at_min = self.get_previous_exercise_level(
                            progression_type,
                            ex['exercise_id']
                        )
                        
                        if not is_at_min:
                            # Replace with previous exercise
                            current_prescription[section][i]['exercise_id'] = prev_exercise
                            current_prescription[section][i]['exercise_name'] = prev_exercise.replace('_', ' ').title()
                            
                            # Increase volume (easier exercise → more reps)
                            current_prescription[section][i]['reps'] = 15
                            current_prescription[section][i]['sets'] = 3
        
        return current_prescription
    
    
    def adjust_prescription_for_advancement(
        self,
        current_prescription: Dict[str, List[Dict]],
        exercise_to_advance: str
    ) -> Dict[str, List[Dict]]:
        """
        Patient ready to advance → go to next level
        
        Week N: Exercise X at 15×3 (threshold met)
        Week N+1: Exercise X+1 at 8×2 (new level, lower volume)
        """
        
        for section in ['strength', 'cardio']:
            for i, ex in enumerate(current_prescription[section]):
                if ex['exercise_id'] == exercise_to_advance:
                    progression_type = ex.get('progression_type')
                    
                    if progression_type and progression_type in self.exercise_progressions:
                        # Advance to next level
                        next_exercise, is_at_max = self.get_next_exercise_level(
                            progression_type,
                            ex['exercise_id']
                        )
                        
                        if not is_at_max:
                            # Replace with next exercise
                            current_prescription[section][i]['exercise_id'] = next_exercise
                            current_prescription[section][i]['exercise_name'] = next_exercise.replace('_', ' ').title()
                            
                            # Reduce volume (harder exercise → fewer reps)
                            current_prescription[section][i]['reps'] = 8
                            current_prescription[section][i]['sets'] = 2
        
        return current_prescription


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    from gate_test_system import GateTestEngine, GateTestCoordinator
    
    print("=" * 70)
    print("PRESCRIPTION ENGINE - DEMO")
    print("=" * 70)
    
    # Setup
    engine = PrescriptionEngine()
    gate_engine = GateTestEngine()
    coordinator = GateTestCoordinator()
    
    # Create mock patient
    patient = PatientProfile(
        patient_id="P001",
        name="Rahul Sharma",
        phone="+91-9876543210",
        password_hash="hashed",
        age=35,
        goals="Build functional strength",
        goal_type="functional",
        lifestyle="sedentary",
        prescription_mode=PrescriptionMode.AI_AUTO
    )
    
    # Mock gate test results
    squat_test = gate_engine.conduct_gate_test(
        patient_id="P001",
        category=ExerciseCategory.LOWER_BODY,
        test_exercise="partial_squat",
        reps_completed=8,
        depth_achieved=55.0,
        difficulty_reported=3,
        pain_during=2
    )
    
    deadlift_test = gate_engine.conduct_gate_test(
        patient_id="P001",
        category=ExerciseCategory.POSTERIOR_CHAIN,
        test_exercise="hip_hinge",
        reps_completed=6,
        difficulty_reported=4,
        pain_during=1
    )
    
    row_test = gate_engine.conduct_gate_test(
        patient_id="P001",
        category=ExerciseCategory.UPPER_BODY,
        test_exercise="bent_over_row",
        reps_completed=10,
        difficulty_reported=3,
        pain_during=1
    )
    
    cardio_test = gate_engine.conduct_gate_test(
        patient_id="P001",
        category=ExerciseCategory.CARDIO,
        test_exercise="walking",
        reps_completed=10,  # 10 minutes
        difficulty_reported=2,
        pain_during=0
    )
    
    # Create gate session
    gate_session = coordinator.create_gate_test_session(
        patient_id="P001",
        test_results=[squat_test, deadlift_test, row_test, cardio_test]
    )
    
    print(f"\n📊 GATE TEST RESULTS:")
    print(f"Overall Fitness: {gate_session.overall_fitness_level.upper()}")
    for test in gate_session.tests_completed:
        print(f"  • {test.category.value}: {test.capability_level.value} → {test.starting_sets}×{test.starting_reps}")
    
    # AI AUTO PRESCRIPTION
    print(f"\n\n🤖 AI AUTO-PRESCRIPTION (Week 1):")
    print("-" * 70)
    
    prescription = engine.prescribe_ai_auto(patient, gate_session, week_number=1)
    
    print("\n1. STRETCHING:")
    for ex in prescription['stretching']:
        print(f"   • {ex['exercise_name']}: {ex['sets']} sets, hold {ex['hold_duration']}s")
    
    print("\n2. STRENGTH:")
    for ex in prescription['strength']:
        print(f"   • {ex['exercise_name']}: {ex['sets']} sets × {ex['reps']} reps")
    
    print("\n3. CARDIO:")
    for ex in prescription['cardio']:
        print(f"   • {ex['exercise_name']}: {ex['hold_duration']}s duration")
    
    # THERAPIST MANUAL MODE
    print(f"\n\n👨‍⚕️ THERAPIST MANUAL PRESCRIPTION:")
    print("-" * 70)
    
    therapist_rx = TherapistPrescription(
        prescription_id="RX001",
        patient_id="P001",
        therapist_id="T001",
        exercises=[
            {'exercise_id': 'normal_squat', 'sets': 3, 'reps': 12, 'hold': 0, 'rest': 60, 'category': ExerciseCategory.LOWER_BODY},
            {'exercise_id': 'conventional_deadlift', 'sets': 2, 'reps': 8, 'hold': 0, 'rest': 90, 'category': ExerciseCategory.POSTERIOR_CHAIN},
            {'exercise_id': 'bicep_curl', 'sets': 2, 'reps': 15, 'hold': 0, 'rest': 45, 'category': ExerciseCategory.UPPER_BODY}
        ],
        clinical_reasoning="Patient needs balanced strength development with focus on lower body"
    )
    
    therapist_prescription = engine.prescribe_therapist_manual(therapist_rx)
    
    print("\nSTRENGTH:")
    for ex in therapist_prescription['strength']:
        print(f"   • {ex['exercise_name']}: {ex['sets']} sets × {ex['reps']} reps")
    
    print("\n✅ Prescription Engine Ready!")
