"""
GATE TEST SYSTEM
Determines patient capability level and starting prescription
"""

from .database_schema import (
    GateTestResult, GateTestSession, CapabilityLevel,
    ExerciseCategory, PatientProfile
)
from datetime import datetime
from typing import Tuple, Dict


class GateTestEngine:
    """
    Handles gate testing logic for each exercise category
    Determines: CANNOT_DO / STRUGGLING / MANAGEABLE / EASY
    """
    
    def __init__(self):
        # Thresholds for capability classification
        self.capability_thresholds = {
            'squat': {
                'depth_min': 30,  # degrees
                'depth_struggling': 45,
                'depth_manageable': 60,
                'depth_easy': 90,
                'reps_struggling': 5,
                'reps_manageable': 10,
                'reps_easy': 10,
                'difficulty_max_easy': 2,  # 1-10 scale
                'difficulty_max_manageable': 4,
                'difficulty_max_struggling': 6
            },
            'deadlift': {
                'reps_struggling': 4,
                'reps_manageable': 8,
                'reps_easy': 8,
                'difficulty_max_easy': 2,
                'difficulty_max_manageable': 4,
                'difficulty_max_struggling': 6
            },
            'rowing': {
                'reps_struggling': 5,
                'reps_manageable': 10,
                'reps_easy': 10,
                'difficulty_max_easy': 2,
                'difficulty_max_manageable': 4,
                'difficulty_max_struggling': 6
            },
            'cardio': {
                'duration_struggling': 5,  # minutes
                'duration_manageable': 10,
                'duration_easy': 15,
                'difficulty_max_easy': 2,
                'difficulty_max_manageable': 4,
                'difficulty_max_struggling': 6
            }
        }
        
        # Prescription based on capability level
        self.prescription_map = {
            CapabilityLevel.CANNOT_DO: {
                'phase': 'phase_0',
                'sets': 0,
                'reps': 0,
                'description': 'Build foundation first - no loading exercises yet'
            },
            CapabilityLevel.STRUGGLING: {
                'phase': 'phase_1_low',
                'sets': 2,
                'reps': 6,
                'description': 'Low volume, focus on form and building tolerance'
            },
            CapabilityLevel.MANAGEABLE: {
                'phase': 'phase_1_standard',
                'sets': 3,
                'reps': 10,
                'description': 'Standard progression, balanced volume'
            },
            CapabilityLevel.EASY: {
                'phase': 'phase_1_high',
                'sets': 3,
                'reps': 15,
                'description': 'High volume, fast-track progression'
            }
        }
    
    
    def classify_capability(
        self,
        exercise_type: str,
        reps_completed: int,
        depth_achieved: float,
        difficulty_reported: int,
        pain_during: int
    ) -> CapabilityLevel:
        """
        Classify capability level based on test performance
        
        Logic:
        - CANNOT_DO: Can't do it, or pain ≥6, or <1 rep
        - STRUGGLING: Can do but difficult (depth <45°, or difficulty ≥4, or <5 reps)
        - MANAGEABLE: Can do with moderate effort (depth <60°, or difficulty ≥2, or <10 reps)
        - EASY: Can do easily (depth ≥60°, and difficulty <2, and ≥10 reps)
        """
        
        thresholds = self.capability_thresholds.get(exercise_type, {})
        
        # CANNOT_DO conditions
        if pain_during >= 6:
            return CapabilityLevel.CANNOT_DO
        
        if reps_completed < 1:
            return CapabilityLevel.CANNOT_DO
        
        if exercise_type == 'squat' and depth_achieved < thresholds['depth_min']:
            return CapabilityLevel.CANNOT_DO
        
        # STRUGGLING conditions
        if reps_completed < thresholds.get('reps_struggling', 5):
            return CapabilityLevel.STRUGGLING
        
        if difficulty_reported >= thresholds.get('difficulty_max_struggling', 6):
            return CapabilityLevel.STRUGGLING
        
        if exercise_type == 'squat' and depth_achieved < thresholds['depth_struggling']:
            return CapabilityLevel.STRUGGLING
        
        # EASY conditions (all must be true)
        easy_conditions = [
            reps_completed >= thresholds.get('reps_easy', 10),
            difficulty_reported <= thresholds.get('difficulty_max_easy', 2),
            pain_during <= 1
        ]
        
        if exercise_type == 'squat':
            easy_conditions.append(depth_achieved >= thresholds['depth_easy'])
        
        if all(easy_conditions):
            return CapabilityLevel.EASY
        
        # Default: MANAGEABLE
        return CapabilityLevel.MANAGEABLE
    
    
    def determine_prescription(
        self,
        capability_level: CapabilityLevel
    ) -> Tuple[int, int, str]:
        """
        Return (sets, reps, phase) based on capability
        """
        prescription = self.prescription_map[capability_level]
        return (
            prescription['sets'],
            prescription['reps'],
            prescription['phase']
        )
    
    
    def conduct_gate_test(
        self,
        patient_id: str,
        category: ExerciseCategory,
        test_exercise: str,
        reps_completed: int,
        depth_achieved: float = 0.0,
        difficulty_reported: int = 5,
        pain_during: int = 0,
        went_to_practice: bool = False,
        notes: str = ""
    ) -> GateTestResult:
        """
        Conduct a single gate test and return results
        """
        
        # Determine exercise type for threshold lookup
        exercise_type_map = {
            ExerciseCategory.LOWER_BODY: 'squat',
            ExerciseCategory.POSTERIOR_CHAIN: 'deadlift',
            ExerciseCategory.UPPER_BODY: 'rowing',
            ExerciseCategory.CARDIO: 'cardio'
        }
        exercise_type = exercise_type_map.get(category, 'squat')
        
        # Classify capability
        capability = self.classify_capability(
            exercise_type=exercise_type,
            reps_completed=reps_completed,
            depth_achieved=depth_achieved,
            difficulty_reported=difficulty_reported,
            pain_during=pain_during
        )
        
        # Determine prescription
        sets, reps, phase = self.determine_prescription(capability)
        
        # Create result
        result = GateTestResult(
            patient_id=patient_id,
            category=category,
            test_exercise=test_exercise,
            test_date=datetime.now(),
            reps_completed=reps_completed,
            depth_achieved=depth_achieved,
            difficulty_reported=difficulty_reported,
            pain_during=pain_during,
            capability_level=capability,
            starting_sets=sets,
            starting_reps=reps,
            starting_phase=phase,
            notes=notes,
            went_to_practice_mode=went_to_practice
        )
        
        return result
    
    
    def handle_too_easy_flow(
        self,
        patient_id: str,
        category: ExerciseCategory,
        exercise_progression: list,  # Ordered list of exercises from easy to hard
        current_index: int = 0
    ) -> Dict:
        """
        Handle the "too easy" advancement flow during gate testing
        
        Patient starts at exercise_progression[0] (easiest)
        If says "too easy", advance to next level
        Continue until they say "this takes effort"
        Then go back 1 level and prescribe at max volume (15×3)
        
        Returns: {
            'starting_exercise': str,
            'starting_level': int,
            'prescription': dict
        }
        """
        
        print(f"\n🎯 GATE TEST - {category.value.upper()}")
        print(f"Starting with: {exercise_progression[current_index]}\n")
        
        # This would be interactive in real app
        # For now, simulating the logic
        
        results = {
            'exercise_levels_tested': [],
            'final_starting_exercise': '',
            'final_starting_level': 0,
            'prescription': {}
        }
        
        # In real implementation, this would be driven by patient clicks
        # Example flow:
        # 1. Test partial squat → "Too easy"
        # 2. Test normal squat → "Too easy"  
        # 3. Test spanish squat → "This takes effort"
        # 4. Go back to normal squat, prescribe 15×3
        
        return results


class GateTestCoordinator:
    """
    Coordinates gate testing across all exercise categories
    Determines overall fitness level
    """
    
    def __init__(self):
        self.engine = GateTestEngine()
        self.required_categories = [
            ExerciseCategory.LOWER_BODY,
            ExerciseCategory.POSTERIOR_CHAIN,
            ExerciseCategory.UPPER_BODY,
            ExerciseCategory.CARDIO
        ]
    
    
    def create_gate_test_session(
        self,
        patient_id: str,
        test_results: list  # List of GateTestResult objects
    ) -> GateTestSession:
        """
        Create a complete gate test session from individual test results
        """
        
        session = GateTestSession(
            patient_id=patient_id,
            session_date=datetime.now(),
            tests_completed=test_results
        )
        
        # Determine overall fitness level
        capability_counts = {
            CapabilityLevel.CANNOT_DO: 0,
            CapabilityLevel.STRUGGLING: 0,
            CapabilityLevel.MANAGEABLE: 0,
            CapabilityLevel.EASY: 0
        }
        
        for result in test_results:
            capability_counts[result.capability_level] += 1
        
        # Overall fitness determination logic
        total_tests = len(test_results)
        
        if capability_counts[CapabilityLevel.EASY] >= total_tests * 0.75:
            session.overall_fitness_level = "advanced"
        elif capability_counts[CapabilityLevel.EASY] >= total_tests * 0.5:
            session.overall_fitness_level = "intermediate"
        elif capability_counts[CapabilityLevel.STRUGGLING] >= total_tests * 0.5:
            session.overall_fitness_level = "beginner"
        else:
            session.overall_fitness_level = "intermediate"
        
        # Ready for prescription if all categories tested
        categories_tested = {r.category for r in test_results}
        session.ready_for_prescription = len(categories_tested) >= 3  # At least 3/4 categories
        
        return session
    
    
    def update_patient_fitness_levels(
        self,
        patient: PatientProfile,
        gate_session: GateTestSession
    ) -> PatientProfile:
        """
        Update patient's fitness levels based on gate test results
        This fills Parameter #2 (Fitness Level) of the 8 clusteral dimensions
        """
        
        for result in gate_session.tests_completed:
            # Map category to fitness level
            category_key = result.category.value
            patient.fitness_level[category_key] = result.capability_level
        
        # Update compliance - they completed the gate test!
        patient.compliance_proven = True
        
        # Update difficulty tolerance (Parameter #5)
        # Take average difficulty reported across all tests
        avg_difficulty = sum(r.difficulty_reported for r in gate_session.tests_completed) / len(gate_session.tests_completed)
        patient.difficulty_tolerance = int(avg_difficulty)
        
        return patient


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("GATE TEST SYSTEM - DEMO")
    print("=" * 70)
    
    # Create test engine
    engine = GateTestEngine()
    coordinator = GateTestCoordinator()
    
    # Example 1: Young athlete
    print("\n📋 EXAMPLE 1: Young Athlete (22 years old)")
    print("-" * 70)
    
    athlete_squat = engine.conduct_gate_test(
        patient_id="P001",
        category=ExerciseCategory.LOWER_BODY,
        test_exercise="partial_squat",
        reps_completed=12,
        depth_achieved=85.0,
        difficulty_reported=2,
        pain_during=1
    )
    
    print(f"Test Exercise: {athlete_squat.test_exercise}")
    print(f"Reps Completed: {athlete_squat.reps_completed}")
    print(f"Depth: {athlete_squat.depth_achieved}°")
    print(f"Difficulty: {athlete_squat.difficulty_reported}/10")
    print(f"Pain: {athlete_squat.pain_during}/10")
    print(f"\n✅ Capability Level: {athlete_squat.capability_level.value.upper()}")
    print(f"📋 Prescription: {athlete_squat.starting_sets} sets × {athlete_squat.starting_reps} reps")
    print(f"🎯 Starting Phase: {athlete_squat.starting_phase}")
    
    # Example 2: Desk worker
    print("\n\n📋 EXAMPLE 2: Desk Worker (35 years old, sedentary)")
    print("-" * 70)
    
    worker_squat = engine.conduct_gate_test(
        patient_id="P002",
        category=ExerciseCategory.LOWER_BODY,
        test_exercise="partial_squat",
        reps_completed=4,
        depth_achieved=40.0,
        difficulty_reported=5,
        pain_during=4
    )
    
    print(f"Test Exercise: {worker_squat.test_exercise}")
    print(f"Reps Completed: {worker_squat.reps_completed}")
    print(f"Depth: {worker_squat.depth_achieved}°")
    print(f"Difficulty: {worker_squat.difficulty_reported}/10")
    print(f"Pain: {worker_squat.pain_during}/10")
    print(f"\n✅ Capability Level: {worker_squat.capability_level.value.upper()}")
    print(f"📋 Prescription: {worker_squat.starting_sets} sets × {worker_squat.starting_reps} reps")
    print(f"🎯 Starting Phase: {worker_squat.starting_phase}")
    
    # Example 3: Elderly patient
    print("\n\n📋 EXAMPLE 3: Elderly Patient (68 years old)")
    print("-" * 70)
    
    elderly_squat = engine.conduct_gate_test(
        patient_id="P003",
        category=ExerciseCategory.LOWER_BODY,
        test_exercise="partial_squat",
        reps_completed=0,
        depth_achieved=20.0,
        difficulty_reported=8,
        pain_during=7,
        went_to_practice=True,
        notes="Could not perform partial squat safely, needs Phase 0 foundation work"
    )
    
    print(f"Test Exercise: {elderly_squat.test_exercise}")
    print(f"Reps Completed: {elderly_squat.reps_completed}")
    print(f"Depth: {elderly_squat.depth_achieved}°")
    print(f"Difficulty: {elderly_squat.difficulty_reported}/10")
    print(f"Pain: {elderly_squat.pain_during}/10")
    print(f"\n✅ Capability Level: {elderly_squat.capability_level.value.upper()}")
    print(f"📋 Prescription: {elderly_squat.starting_phase} (no squats yet)")
    print(f"📝 Notes: {elderly_squat.notes}")
    
    print("\n" + "=" * 70)
    print("✅ Gate Test System Ready!")
    print("=" * 70)
