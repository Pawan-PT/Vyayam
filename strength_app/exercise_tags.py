"""
VYAYAM EXERCISE TAGS & PROGRESSIVE LOADING SYSTEM
===================================================

Central tagging registry for all 68 exercises.

Each exercise tag contains:
  - category       : broad movement category
  - family_id      : which progression chain it belongs to
  - ladder_position: step in the family's ladder (1 = easiest)
  - gate_test_relevant: whether gate testing uses this exercise
  - contraindications: rough list (full diagnosis system = future)
  - dosage_table   : sets × reps at each capability level (1-5)

CAPABILITY LEVELS (5-level system)
------------------------------------
  1 = Unable          → Skip / prescribe previous level
  2 = Partial/Assisted → 5-7 reps × 2 sets
  3 = Basic/Building   → 10 reps × 2 sets
  4 = Comfortable      → 12-15 reps × 3 sets
  5 = Advanced/Ready   → Advance to next exercise in ladder

AGE MODIFIERS
--------------
  < 30 : +1 sets bonus on strength (if goal is athletic)
  30-50: no change
  50-65: -1 rep per set on strength (conservative)
  65+  : -2 reps per set, max 2 sets on strength

LIFESTYLE MODIFIERS
--------------------
  sedentary     : start at lower end of reps, shorter holds
  moderately_active: baseline
  active        : +1 set on strength
  very_active   : +2 reps, +1 set on strength (if goal is athletic)

GOAL MODIFIERS
---------------
  rehabilitation: conservative — never exceed 3 sets or manageable capability
  functional    : standard progression
  athletic      : aggressive — push to top of range, add load notes
"""

# ============================================================================
# DOSAGE TABLES
# Each key = capability level (1-5)
# Value = (sets, reps, hold_seconds)
# For hold-based exercises: reps=1, hold_seconds > 0
# ============================================================================

# Standard strength dosage (reps-based)
STRENGTH_DOSAGE = {
    1: (0, 0, 0),         # Unable — do not prescribe
    2: (2, 6, 0),         # Partial capability
    3: (2, 10, 0),        # Basic capability
    4: (3, 12, 0),        # Comfortable
    5: (3, 15, 0),        # Advanced → ready for next exercise
}

# Unilateral (single leg/arm) — fewer reps per side
UNILATERAL_DOSAGE = {
    1: (0, 0, 0),
    2: (2, 5, 0),
    3: (2, 8, 0),
    4: (3, 10, 0),
    5: (3, 12, 0),
}

# Balance / hold-based
BALANCE_DOSAGE = {
    1: (0, 0, 0),
    2: (2, 1, 15),        # 2 sets, hold 15 sec
    3: (2, 1, 25),
    4: (3, 1, 35),
    5: (3, 1, 45),
}

# Cardio / timed
CARDIO_DOSAGE = {
    1: (0, 0, 0),
    2: (1, 1, 60),        # 1 round, 60 seconds
    3: (1, 1, 90),
    4: (2, 1, 90),
    5: (2, 1, 120),
}

# Stretching / mobility — always prescribed, adjusted by mobility capability
STRETCH_DOSAGE = {
    1: (2, 1, 20),
    2: (2, 1, 30),
    3: (2, 1, 40),
    4: (3, 1, 45),
    5: (3, 1, 60),
}


# ============================================================================
# AGE × LIFESTYLE × GOAL ADJUSTMENT
# Returns a modifier dict: {sets_mod, reps_mod, hold_mod}
# Positive = add, Negative = subtract
# ============================================================================

def get_patient_modifier(age, lifestyle, goal_type):
    """
    Returns dict: {'sets': Δsets, 'reps': Δreps, 'hold': Δhold_secs}
    Applied on top of the capability-level dosage.
    """
    sets_mod = 0
    reps_mod = 0
    hold_mod = 0

    # ── Age modifier ──────────────────────────────────────────────────────────
    if age >= 65:
        reps_mod -= 2
        sets_mod -= 1      # max 2 sets
        hold_mod -= 10
    elif age >= 50:
        reps_mod -= 1
        hold_mod -= 5
    elif age < 30:
        # Young adults handle more volume
        reps_mod += 1

    # ── Lifestyle modifier ────────────────────────────────────────────────────
    if lifestyle == 'sedentary':
        reps_mod -= 1
        sets_mod -= 1
    elif lifestyle == 'active':
        sets_mod += 1
    elif lifestyle == 'very_active':
        sets_mod += 1
        reps_mod += 2

    # ── Goal modifier ─────────────────────────────────────────────────────────
    if goal_type == 'rehabilitation':
        # Conservative — do not let modifiers push above base
        reps_mod = min(reps_mod, 0)    # rehabilitation never adds reps
        sets_mod = min(sets_mod, 0)
        hold_mod = min(hold_mod, 0)
    elif goal_type == 'athletic':
        reps_mod += 1
        sets_mod += 1

    return {'sets': sets_mod, 'reps': reps_mod, 'hold': hold_mod}


def apply_modifier(base_dosage, modifier, age=None, is_hold=False):
    """
    Apply age/lifestyle/goal modifier to a (sets, reps, hold) tuple.
    Clamps to sensible minimums.
    """
    sets, reps, hold = base_dosage
    if sets == 0:
        return (0, 0, 0)   # Cannot do — don't modify

    sets = max(1, sets + modifier['sets'])
    if age and age >= 65:
        sets = min(sets, 2)   # Hard cap 2 sets for 65+

    if is_hold:
        hold = max(10, hold + modifier['hold'])
    else:
        reps = max(3, reps + modifier['reps'])

    return (sets, reps, hold)


# ============================================================================
# CAPABILITY STRING → NUMERIC (1-5)
# ============================================================================

CAPABILITY_TO_NUMERIC = {
    'cannot_do': 1,
    'struggling': 2,
    'manageable': 3,
    'easy': 4,
    # 5 = "ready to advance" — set programmatically after time + comfort criteria
}


def capability_str_to_numeric(capability_str):
    return CAPABILITY_TO_NUMERIC.get(capability_str, 3)


def numeric_to_capability_str(numeric):
    mapping = {1: 'cannot_do', 2: 'struggling', 3: 'manageable', 4: 'easy', 5: 'easy'}
    return mapping.get(numeric, 'manageable')


# ============================================================================
# DOSAGE LOOKUP — main public function
# ============================================================================

def get_exercise_dosage(exercise_id, capability_numeric, age, lifestyle, goal_type):
    """
    Get final (sets, reps, hold_seconds) for a given exercise + patient profile.

    Args:
        exercise_id     : e.g. 'partial_squats', 'single_leg_balance'
        capability_numeric: 1-5
        age             : patient age
        lifestyle       : 'sedentary' | 'moderately_active' | 'active' | 'very_active'
        goal_type       : 'rehabilitation' | 'functional' | 'athletic'

    Returns:
        dict: {sets, reps, hold_duration, dosage_label}
    """
    tag = EXERCISE_TAGS.get(exercise_id)
    if not tag:
        # Unknown exercise — use safe default
        tag = {'dosage_table': STRENGTH_DOSAGE, 'is_hold': False}

    dosage_table = tag['dosage_table']
    is_hold = tag.get('is_hold', False)

    base = dosage_table.get(capability_numeric, dosage_table.get(3))

    modifier = get_patient_modifier(age, lifestyle, goal_type)
    sets, reps, hold = apply_modifier(base, modifier, age=age, is_hold=is_hold)

    labels = {1: 'Unable', 2: 'Partial', 3: 'Basic', 4: 'Comfortable', 5: 'Advanced'}

    return {
        'sets': sets,
        'reps': reps,
        'hold_duration': hold,
        'dosage_label': labels.get(capability_numeric, 'Basic'),
        'is_hold': is_hold,
    }


# ============================================================================
# PRESCRIPTION PRIORITY — which families matter for which goals
# ============================================================================

GOAL_PRIORITY_FAMILIES = {
    'rehabilitation': ['squat_family', 'hip_hinge_family', 'balance_family', 'lunge_family'],
    'functional':    ['squat_family', 'hip_hinge_family', 'lunge_family', 'balance_family', 'push_family', 'cardio_family'],
    'athletic':      ['squat_family', 'lunge_family', 'hip_hinge_family', 'push_family', 'cardio_family', 'balance_family'],
}

# V1: Goal → Pattern priorities (ordered by importance)
GOAL_PRIORITY_PATTERNS = {
    'general_strength':   ['squat', 'hinge', 'push', 'pull', 'lunge', 'rotate', 'carry'],
    'hypertrophy':        ['squat', 'hinge', 'push', 'pull', 'lunge', 'rotate', 'carry'],
    'endurance':          ['squat', 'hinge', 'lunge', 'push', 'pull', 'carry', 'rotate'],
    'strength_endurance': ['squat', 'hinge', 'push', 'pull', 'lunge', 'rotate', 'carry'],
    'calisthenics':       ['push', 'pull', 'squat', 'lunge', 'rotate', 'hinge', 'carry'],
    'fat_loss':           ['squat', 'hinge', 'lunge', 'push', 'pull', 'rotate', 'carry'],
    'female_physique':    ['hinge', 'lunge', 'rotate', 'squat', 'push', 'pull', 'carry'],
    'athletic':           ['squat', 'hinge', 'lunge', 'rotate', 'push', 'pull', 'carry'],
    'rehabilitation':     ['squat', 'hinge', 'lunge', 'rotate', 'push', 'pull', 'carry'],
    'mobility':           ['rotate', 'hinge', 'squat', 'lunge', 'push', 'pull', 'carry'],
    'posture':            ['pull', 'rotate', 'hinge', 'push', 'squat', 'lunge', 'carry'],
    'healthy_ageing':     ['squat', 'hinge', 'lunge', 'carry', 'push', 'pull', 'rotate'],
}

# Maximum capability to prescribe per age group (safety guardrail)
AGE_CAPABILITY_CAP = {
    # (age_min, age_max): max_capability_to_prescribe
    (0,  29):  5,
    (30, 49):  5,
    (50, 64):  4,
    (65, 200): 3,
}


def get_age_capability_cap(age):
    for (lo, hi), cap in AGE_CAPABILITY_CAP.items():
        if lo <= age <= hi:
            return cap
    return 3


def get_lifestyle_start_capability(lifestyle, gate_capability):
    """
    For patients who haven't been gate tested, infer a starting capability
    from their lifestyle. Never exceeds actual gate test result.
    """
    lifestyle_defaults = {
        'sedentary':          2,
        'moderately_active':  3,
        'active':             3,
        'very_active':        4,
    }
    default = lifestyle_defaults.get(lifestyle, 2)
    return min(default, gate_capability) if gate_capability else default


# ============================================================================
# EXERCISE TAGS REGISTRY
# All 68 exercises tagged with category, family, dosage table, contraindications
# ============================================================================

EXERCISE_TAGS = {

    # ══════════════════════════════════════════════════════════════════════════
    # SQUAT FAMILY  (8-rung ladder)
    # ══════════════════════════════════════════════════════════════════════════

    'sit_to_stand': {
        'category': 'strength_lower',
        'family_id': 'squat_family',
        'ladder_position': 1,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': True,
        'contraindications': ['acute_knee_injury'],
        'notes': 'Safest entry point. Always prescribe for 65+ as floor-level squat.',
    },
    'partial_squats': {
        'category': 'strength_lower',
        'family_id': 'squat_family',
        'ladder_position': 2,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': True,
        'contraindications': ['acute_knee_injury'],
        'notes': 'Primary gate test exercise for squat family.',
    },
    'mini_squats_with_band': {
        'category': 'strength_lower',
        'family_id': 'squat_family',
        'ladder_position': 3,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'patellofemoral_pain'],
        'notes': 'Resistance band adds hip activation. Good for valgus correction.',
    },
    'full_squats': {
        'category': 'strength_lower',
        'family_id': 'squat_family',
        'ladder_position': 4,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'severe_arthritis'],
        'notes': 'Full depth. Requires good ankle dorsiflexion.',
    },
    'spanish_squat': {
        'category': 'strength_lower',
        'family_id': 'squat_family',
        'ladder_position': 5,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['patellar_tendinopathy_acute'],
        'notes': 'Max quad isolation. Used in patellar tendon rehab (chronic stage).',
    },
    'decline_squats': {
        'category': 'strength_lower',
        'family_id': 'squat_family',
        'ladder_position': 6,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['patellar_tendinopathy_acute', 'severe_arthritis'],
        'notes': 'Increased patellar tendon load. Advanced rehab only.',
    },
    'single_leg_squats': {
        'category': 'strength_lower',
        'family_id': 'squat_family',
        'ladder_position': 7,
        'dosage_table': UNILATERAL_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'acute_ankle_sprain'],
        'notes': 'Pistol progression. Requires strong hip abductors.',
    },
    'jump_squats': {
        'category': 'strength_lower',
        'family_id': 'squat_family',
        'ladder_position': 8,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'severe_arthritis', 'cardiac_condition', 'age_65_plus'],
        'notes': 'Plyometric. Athletic goal only. Not for 60+ or rehab patients.',
    },

    # ══════════════════════════════════════════════════════════════════════════
    # HIP HINGE FAMILY  (4-rung ladder)
    # ══════════════════════════════════════════════════════════════════════════

    'glute_bridge': {
        'category': 'strength_posterior',
        'family_id': 'hip_hinge_family',
        'ladder_position': 1,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': True,
        'contraindications': ['lumbar_disc_herniation_acute'],
        'notes': 'Supine — zero spinal compression. Excellent for all ages.',
    },
    'single_leg_glute_bridge': {
        'category': 'strength_posterior',
        'family_id': 'hip_hinge_family',
        'ladder_position': 2,
        'dosage_table': UNILATERAL_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['lumbar_disc_herniation_acute'],
        'notes': 'Adds hip stabiliser demand.',
    },
    'deadlift_dumbbell': {
        'category': 'strength_posterior',
        'family_id': 'hip_hinge_family',
        'ladder_position': 3,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['lumbar_disc_herniation_acute', 'osteoporosis_severe'],
        'notes': 'Classic hip hinge. Teach neutral spine first.',
    },
    'single_leg_rdl': {
        'category': 'strength_posterior',
        'family_id': 'hip_hinge_family',
        'ladder_position': 4,
        'dosage_table': UNILATERAL_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['lumbar_disc_herniation_acute', 'acute_ankle_sprain'],
        'notes': 'Highest posterior chain + balance demand.',
    },

    # ══════════════════════════════════════════════════════════════════════════
    # LUNGE FAMILY  (5-rung ladder)
    # ══════════════════════════════════════════════════════════════════════════

    'step_ups': {
        'category': 'strength_lower',
        'family_id': 'lunge_family',
        'ladder_position': 1,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': True,
        'contraindications': ['acute_knee_injury'],
        'notes': 'Functional — mimics stair climbing. Great for older adults.',
    },
    'step_downs': {
        'category': 'strength_lower',
        'family_id': 'lunge_family',
        'ladder_position': 1,   # Same level as step_ups
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury'],
        'notes': 'Eccentric variant of step-ups. Paired with step_ups.',
    },
    'side_step_ups': {
        'category': 'strength_lower',
        'family_id': 'lunge_family',
        'ladder_position': 1,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury'],
        'notes': 'Lateral step-up adds hip abductor demand.',
    },
    'side_step_downs': {
        'category': 'strength_lower',
        'family_id': 'lunge_family',
        'ladder_position': 1,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury'],
        'notes': 'Eccentric lateral variant.',
    },
    'reverse_lunges': {
        'category': 'strength_lower',
        'family_id': 'lunge_family',
        'ladder_position': 2,
        'dosage_table': UNILATERAL_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury'],
        'notes': 'Easier on knee than forward lunge — posterior knee stress less.',
    },
    'lunges': {
        'category': 'strength_lower',
        'family_id': 'lunge_family',
        'ladder_position': 3,
        'dosage_table': UNILATERAL_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'severe_patellofemoral_pain'],
        'notes': 'Classic lunge. Monitor anterior knee tracking.',
    },
    'lateral_lunges': {
        'category': 'strength_lower',
        'family_id': 'lunge_family',
        'ladder_position': 4,
        'dosage_table': UNILATERAL_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_groin_strain', 'acute_knee_injury'],
        'notes': 'Frontal plane strength — hip adductor/abductor balance.',
    },
    'bulgarian_split_squats': {
        'category': 'strength_lower',
        'family_id': 'lunge_family',
        'ladder_position': 5,
        'dosage_table': UNILATERAL_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'hip_flexor_strain'],
        'notes': 'Highest single-leg load. Athletic/advanced only.',
    },

    # ══════════════════════════════════════════════════════════════════════════
    # HIP ISOLATION  (accessory — not a progression family)
    # ══════════════════════════════════════════════════════════════════════════

    'clamshells': {
        'category': 'strength_hip',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': [],
        'notes': 'Hip abductor isolation. Prescribed for all rehab patients.',
    },
    'hip_abduction_standing': {
        'category': 'strength_hip',
        'family_id': None,
        'ladder_position': 2,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': [],
        'notes': 'Standing hip abductor. More functional than clamshells.',
    },
    'hip_abduction_sideline': {
        'category': 'strength_hip',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': [],
        'notes': 'Side-lying variant. Easier starting point.',
    },
    'lateral_band_walks': {
        'category': 'strength_hip',
        'family_id': None,
        'ladder_position': 2,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': [],
        'notes': 'Dynamic hip abductor + glute activation.',
    },
    'straight_leg_raises': {
        'category': 'strength_quad',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['lumbar_disc_herniation_acute'],
        'notes': 'VMO and hip flexor activation. Safe post-surgery.',
    },
    'terminal_knee_extension': {
        'category': 'strength_quad',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': [],
        'notes': 'VMO specific. ACL rehab staple.',
    },
    'knee_extension_sitting': {
        'category': 'strength_quad',
        'family_id': None,
        'ladder_position': 2,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['patellar_tendinopathy_acute'],
        'notes': 'Isolated quad strengthening. Monitor for anterior knee pain.',
    },
    'hamstring_curls_standing': {
        'category': 'strength_posterior',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': UNILATERAL_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['hamstring_tear_acute'],
        'notes': 'Standing hamstring curl. Can use band for resistance.',
    },

    # ══════════════════════════════════════════════════════════════════════════
    # PUSH / UPPER BODY FAMILY  (3-rung ladder)
    # ══════════════════════════════════════════════════════════════════════════

    'bicep_curls': {
        'category': 'strength_upper',
        'family_id': 'push_family',
        'ladder_position': 1,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['elbow_injury_acute'],
        'notes': 'Basic upper arm strength. Low barrier entry.',
    },
    'tricep_extensions': {
        'category': 'strength_upper',
        'family_id': 'push_family',
        'ladder_position': 1,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': True,
        'contraindications': ['elbow_injury_acute', 'shoulder_impingement_acute'],
        'notes': 'Gate test start for push family.',
    },
    'push_ups': {
        'category': 'strength_upper',
        'family_id': 'push_family',
        'ladder_position': 2,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['shoulder_impingement_acute', 'wrist_injury'],
        'notes': 'Knee push-ups acceptable as regression.',
    },
    'dumbbell_rowing': {
        'category': 'strength_upper',
        'family_id': 'push_family',
        'ladder_position': 2,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['lumbar_disc_herniation_acute'],
        'notes': 'Pulling pattern — counterbalances pushing exercises.',
    },
    'planks': {
        'category': 'strength_core',
        'family_id': 'push_family',
        'ladder_position': 3,
        'dosage_table': BALANCE_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['lumbar_disc_herniation_acute', 'shoulder_injury'],
        'notes': 'Core endurance. Prerequisite for advanced exercises.',
    },
    'rotational_swings': {
        'category': 'strength_core',
        'family_id': None,
        'ladder_position': 2,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['lumbar_disc_herniation_acute'],
        'notes': 'Rotational core power. Sport-specific.',
    },
    'mountain_climbers': {
        'category': 'strength_core',
        'family_id': None,
        'ladder_position': 3,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['shoulder_injury', 'lumbar_disc_herniation_acute', 'cardiac_condition'],
        'notes': 'High intensity. Athletic/cardio goal. Not for rehab.',
    },

    # ══════════════════════════════════════════════════════════════════════════
    # BALANCE FAMILY  (5-rung ladder)
    # ══════════════════════════════════════════════════════════════════════════

    'double_leg_balance': {
        'category': 'balance',
        'family_id': 'balance_family',
        'ladder_position': 1,
        'dosage_table': BALANCE_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': True,
        'contraindications': [],
        'notes': 'Entry point. Prescribed for all 65+ as standard.',
    },
    'single_leg_balance': {
        'category': 'balance',
        'family_id': 'balance_family',
        'ladder_position': 2,
        'dosage_table': BALANCE_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': True,
        'contraindications': ['acute_ankle_sprain'],
        'notes': 'Key fall prevention metric. Gate test exercise.',
    },
    'lateral_gait_training': {
        'category': 'balance',
        'family_id': 'balance_family',
        'ladder_position': 3,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': [],
        'notes': 'Dynamic lateral stability.',
    },
    'clock_reaches': {
        'category': 'balance',
        'family_id': 'balance_family',
        'ladder_position': 4,
        'dosage_table': UNILATERAL_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_ankle_sprain', 'severe_vestibular_disorder'],
        'notes': 'Star excursion balance test variant. Advanced proprioception.',
    },
    'tandem_walking': {
        'category': 'balance',
        'family_id': 'balance_family',
        'ladder_position': 5,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['severe_vestibular_disorder'],
        'notes': 'Highest balance challenge. Fall prevention advanced.',
    },
    'sideways_walking': {
        'category': 'balance',
        'family_id': 'balance_family',
        'ladder_position': 3,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': [],
        'notes': 'Dynamic lateral gait. Pairs with lateral_gait_training.',
    },
    'backward_walking': {
        'category': 'balance',
        'family_id': 'balance_family',
        'ladder_position': 3,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': [],
        'notes': 'Proprioceptive challenge. Pairs with lateral gait.',
    },

    # ══════════════════════════════════════════════════════════════════════════
    # CARDIO FAMILY  (5-rung ladder)
    # ══════════════════════════════════════════════════════════════════════════

    'marching_on_spot': {
        'category': 'cardio',
        'family_id': 'cardio_family',
        'ladder_position': 1,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': True,
        'contraindications': [],
        'notes': 'Safest cardio entry. Prescribe for all sedentary patients.',
    },
    'high_knees': {
        'category': 'cardio',
        'family_id': 'cardio_family',
        'ladder_position': 2,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'cardiac_condition_uncontrolled'],
        'notes': 'Elevated cardiovascular demand.',
    },
    'jumping_jacks': {
        'category': 'cardio',
        'family_id': 'cardio_family',
        'ladder_position': 3,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'acute_ankle_sprain'],
        'notes': 'Impact exercise. Not for rehab.',
    },
    'butt_kicks': {
        'category': 'cardio',
        'family_id': 'cardio_family',
        'ladder_position': 4,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['hamstring_injury', 'cardiac_condition_uncontrolled'],
        'notes': 'Hamstring activation + cardio.',
    },
    'mountain_climbers_cardio': {  # alias for cardio context
        'category': 'cardio',
        'family_id': 'cardio_family',
        'ladder_position': 5,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['shoulder_injury', 'lumbar_disc_herniation_acute', 'cardiac_condition'],
        'notes': 'Maximum intensity cardio + core. Athletic only.',
    },
    'side_to_side_hops': {
        'category': 'cardio',
        'family_id': 'cardio_family',
        'ladder_position': 4,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'acute_ankle_sprain'],
        'notes': 'Lateral plyometric. Athletic/active patients only.',
    },
    'skaters': {
        'category': 'cardio',
        'family_id': 'cardio_family',
        'ladder_position': 4,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'acute_ankle_sprain'],
        'notes': 'Lateral power + cardio. Functional for sport.',
    },
    'sprint_in_place': {
        'category': 'cardio',
        'family_id': 'cardio_family',
        'ladder_position': 5,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['cardiac_condition_uncontrolled', 'age_65_plus'],
        'notes': 'Maximum heart rate effort. Athletic only.',
    },
    'lateral_hops': {
        'category': 'cardio',
        'family_id': 'cardio_family',
        'ladder_position': 5,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'acute_ankle_sprain'],
        'notes': 'Plyometric lateral power.',
    },
    'box_jumps': {
        'category': 'cardio',
        'family_id': 'cardio_family',
        'ladder_position': 5,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'acute_ankle_sprain', 'cardiac_condition', 'age_65_plus'],
        'notes': 'Maximum plyometric demand. Elite athletic goal only.',
    },
    'burpees': {
        'category': 'cardio',
        'family_id': 'cardio_family',
        'ladder_position': 5,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'shoulder_injury', 'cardiac_condition', 'age_65_plus'],
        'notes': 'Full body HIIT. Athletic only.',
    },
    'tuck_jumps': {
        'category': 'cardio',
        'family_id': 'cardio_family',
        'ladder_position': 5,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury', 'lumbar_condition', 'cardiac_condition', 'age_65_plus'],
        'notes': 'Plyometric power. Athletic only.',
    },

    # ══════════════════════════════════════════════════════════════════════════
    # STRETCHING / MOBILITY  (always prescribed — capability determines hold)
    # ══════════════════════════════════════════════════════════════════════════

    'hamstring_stretch': {
        'category': 'mobility_lower',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRETCH_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['hamstring_tear_acute'],
        'notes': 'Core warm-up stretch. Prescribe for all patients.',
    },
    'hip_flexor_stretch': {
        'category': 'mobility_lower',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRETCH_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['acute_groin_strain'],
        'notes': 'Critical for sedentary patients with desk jobs.',
    },
    'quadriceps_stretch': {
        'category': 'mobility_lower',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRETCH_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury'],
        'notes': 'Standard warm-up. Pairs with squat exercises.',
    },
    'calf_stretch': {
        'category': 'mobility_lower',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRETCH_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['achilles_tear_acute'],
        'notes': 'Ankle dorsiflexion. Improves squat depth.',
    },
    'groin_stretch_butterfly': {
        'category': 'mobility_lower',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRETCH_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['acute_groin_strain'],
        'notes': 'Hip adductor flexibility.',
    },
    'it_band_stretch_standing': {
        'category': 'mobility_lower',
        'family_id': None,
        'ladder_position': 2,
        'dosage_table': STRETCH_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': [],
        'notes': 'IT band / TFL mobility. PFPS and running injuries.',
    },
    'static_quadriceps': {
        'category': 'mobility_lower',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRETCH_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['acute_knee_injury'],
        'notes': 'Quad stretch variant. Post-exercise cooldown.',
    },
    'static_glutei': {
        'category': 'mobility_lower',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRETCH_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['hip_replacement_recent'],
        'notes': 'Glute / piriformis flexibility.',
    },
    'static_hip_adductors': {
        'category': 'mobility_lower',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRETCH_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['acute_groin_strain'],
        'notes': 'Hip adductor range of motion.',
    },
    'heel_slides': {
        'category': 'mobility_lower',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': False,
        'contraindications': [],
        'notes': 'Supine knee ROM exercise. Post-surgical standard.',
    },
    'shoulder_stretch_overhead': {
        'category': 'mobility_upper',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRETCH_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['shoulder_dislocation_recent'],
        'notes': 'Shoulder capsule / overhead mobility.',
    },
    'chest_stretch_doorway': {
        'category': 'mobility_upper',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRETCH_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['shoulder_dislocation_recent'],
        'notes': 'Pectoral / anterior shoulder stretch. Good for desk workers.',
    },
    'wrist_forearm_stretch': {
        'category': 'mobility_upper',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRETCH_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['carpal_tunnel_acute'],
        'notes': 'Wrist / forearm flexibility. Typist / computer users.',
    },
    'trunk_rotation_stretch': {
        'category': 'mobility_spine',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRETCH_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['lumbar_disc_herniation_acute'],
        'notes': 'Spinal rotational mobility.',
    },
    'foam_rolling': {
        'category': 'mobility_lower',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': CARDIO_DOSAGE,
        'is_hold': True,
        'gate_test_relevant': False,
        'contraindications': ['blood_clot_risk', 'open_wound'],
        'notes': 'Self-myofascial release. Can be done every session.',
    },
    'sit_to_stand_gate': {  # sit-to-stand used as gate test functional marker
        'category': 'functional',
        'family_id': None,
        'ladder_position': 1,
        'dosage_table': STRENGTH_DOSAGE,
        'is_hold': False,
        'gate_test_relevant': True,
        'contraindications': [],
        'notes': 'ADL functional assessment. Also used as squat foundation.',
    },
}


# ============================================================================
# FAMILY → DEFAULT STRETCHES  (always appended to prescription warm-up)
# ============================================================================

FAMILY_WARMUP_STRETCHES = {
    'squat_family':     ['quadriceps_stretch', 'hamstring_stretch', 'hip_flexor_stretch', 'calf_stretch'],
    'hip_hinge_family': ['hamstring_stretch', 'hip_flexor_stretch', 'static_glutei'],
    'lunge_family':     ['hip_flexor_stretch', 'quadriceps_stretch', 'hamstring_stretch'],
    'push_family':      ['chest_stretch_doorway', 'shoulder_stretch_overhead', 'wrist_forearm_stretch'],
    'balance_family':   ['calf_stretch', 'hip_flexor_stretch'],
    'cardio_family':    ['hamstring_stretch', 'calf_stretch', 'hip_flexor_stretch'],
}


# ============================================================================
# LIFESTYLE → CARDIO ADJUSTMENT
# Sedentary patients should not jump to high-intensity cardio
# ============================================================================

LIFESTYLE_MAX_CARDIO_LEVEL = {
    'sedentary':          2,   # Max ladder position for cardio
    'moderately_active':  3,
    'active':             4,
    'very_active':        5,
}


def get_max_cardio_level(lifestyle):
    return LIFESTYLE_MAX_CARDIO_LEVEL.get(lifestyle, 3)