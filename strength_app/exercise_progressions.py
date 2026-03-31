"""
EXERCISE PROGRESSION CHAINS
============================
Defines ordered progression ladders for each exercise family (movement pattern).

Gate tests walk through each family's chain starting at Level 1.
Patient tries each level. If "Too Easy" → advance to next level.
When "This is My Level" → prescribe at that level.

All exercise_id values must match keys in EXERCISE_METADATA in exercise_registry_v2.py

PROGRESSIVE LOADING DOSAGE (capability_numeric → sets/reps/hold)
-----------------------------------------------------------------
  1 = Unable          → (0, 0, 0)     skip
  2 = Partial/Assisted → (2, 6, 0)   entry level
  3 = Basic/Building   → (2, 10, 0)  building
  4 = Comfortable      → (3, 12, 0)  working
  5 = Advanced/Ready   → advance to next ladder rung
"""

# ── Reusable dosage presets ────────────────────────────────────────────────
# Each is a dict: capability_numeric (int) → (sets, reps, hold_secs)

_STRENGTH_DOS = {1:(0,0,0), 2:(2,6,0),  3:(2,10,0), 4:(3,12,0), 5:(3,15,0)}
_UNILAT_DOS   = {1:(0,0,0), 2:(2,5,0),  3:(2,8,0),  4:(3,10,0), 5:(3,12,0)}
_BALANCE_DOS  = {1:(0,0,0), 2:(2,1,15), 3:(2,1,25), 4:(3,1,35), 5:(3,1,45)}
_CARDIO_DOS   = {1:(0,0,0), 2:(1,1,60), 3:(1,1,90), 4:(2,1,90), 5:(2,1,120)}
_STRETCH_DOS  = {1:(2,1,20),2:(2,1,30), 3:(2,1,40), 4:(3,1,45), 5:(3,1,60)}

# ============================================================================
# PROGRESSION CHAINS (6 movement pattern families)
# ============================================================================

PROGRESSION_CHAINS = {

    # ── SQUAT PATTERN ────────────────────────────────────────────────────────
    'squat_family': {
        'family_id': 'squat_family',
        'name': 'Squat Pattern',
        'icon': '🦵',
        'description': 'Lower body strength via squat movement — quads, glutes, hamstrings',
        'movement_type': 'strength',
        'levels': [
            {
                'level': 1,
                'exercise_id': 'sit_to_stand',
                'name': 'Sit to Stand',
                'label': 'Level 1 — Foundation',
                'description': 'Rise from a chair and sit back down under control. The safest starting point.',
                'instructions': [
                    'Sit at the edge of a sturdy chair with feet shoulder-width apart',
                    'Lean slightly forward, then push through your feet to stand fully upright',
                    'Pause at the top for 1 second',
                    'Slowly lower yourself back to seated — don\'t drop!',
                ],
                'target_reps': 8,
                'hold_duration': 0,
                'category': 'strength',
                'dosage_by_capability': _STRENGTH_DOS,
            },
            {
                'level': 2,
                'exercise_id': 'partial_squats',
                'name': 'Partial Squats',
                'label': 'Level 2',
                'description': 'Bend knees to ~45° — an easy, controlled squat pattern.',
                'instructions': [
                    'Stand with feet shoulder-width apart, toes slightly out',
                    'Bend knees to about 45° (as if starting to sit)',
                    'Keep chest up, back straight, knees tracking over toes',
                    'Push through heels to return to standing',
                ],
                'target_reps': 10,
                'hold_duration': 0,
                'category': 'strength',
                'dosage_by_capability': _STRENGTH_DOS,
            },
            {
                'level': 3,
                'exercise_id': 'mini_squats_with_band',
                'name': 'Mini Squats with Band',
                'label': 'Level 3',
                'description': 'Partial squats with a resistance band above the knees for hip activation.',
                'instructions': [
                    'Place resistance band just above knees',
                    'Push knees outward against band throughout movement',
                    'Squat to 60° knee bend',
                    'Drive knees out on the way back up',
                ],
                'target_reps': 10,
                'hold_duration': 0,
                'category': 'strength',
                'dosage_by_capability': _STRENGTH_DOS,
            },
            {
                'level': 4,
                'exercise_id': 'full_squats',
                'name': 'Full Squats',
                'label': 'Level 4',
                'description': 'Full depth squat — thighs parallel to floor or deeper.',
                'instructions': [
                    'Feet shoulder-width apart, toes 15–30° out',
                    'Descend until thighs are parallel to floor (or deeper)',
                    'Knees track over toes throughout',
                    'Drive through heels to stand — don\'t round back',
                ],
                'target_reps': 12,
                'hold_duration': 0,
                'category': 'strength',
                'dosage_by_capability': _STRENGTH_DOS,
            },
            {
                'level': 5,
                'exercise_id': 'spanish_squat',
                'name': 'Spanish Squat',
                'label': 'Level 5',
                'description': 'Wall-strap squat keeping shins vertical — max quad isolation.',
                'instructions': [
                    'Loop a strap/rope around a fixed pole at waist height',
                    'Hold strap, walk feet forward, lean back',
                    'Squat down keeping shins vertical (don\'t let knees travel forward)',
                    'Sit into it — feel the deep quad burn',
                ],
                'target_reps': 10,
                'hold_duration': 0,
                'category': 'strength',
                'dosage_by_capability': _STRENGTH_DOS,
            },
            {
                'level': 6,
                'exercise_id': 'decline_squats',
                'name': 'Decline Squats',
                'label': 'Level 6',
                'description': 'Squats on a decline board (15–25°) — increased knee tendon load.',
                'instructions': [
                    'Stand on a decline board or wedge (heels elevated)',
                    'Perform full depth squat maintaining heel contact',
                    'More challenging for the patellar tendon and quads',
                    'Control descent, drive back up',
                ],
                'target_reps': 10,
                'hold_duration': 0,
                'category': 'strength',
                'dosage_by_capability': _STRENGTH_DOS,
            },
            {
                'level': 7,
                'exercise_id': 'single_leg_squats',
                'name': 'Single Leg Squats',
                'label': 'Level 7 — Advanced',
                'description': 'Squat on one leg — pistol squat progression.',
                'instructions': [
                    'Stand on one leg near a wall or chair for safety',
                    'Squat down on that one leg as far as comfortable',
                    'Keep standing knee over toes',
                    'Push back to standing',
                ],
                'target_reps': 6,
                'hold_duration': 0,
                'category': 'strength',
                'dosage_by_capability': _UNILAT_DOS,
            },
            {
                'level': 8,
                'exercise_id': 'jump_squats',
                'name': 'Jump Squats',
                'label': 'Level 8 — Elite',
                'description': 'Explosive squat with a jump — maximum power output.',
                'instructions': [
                    'Full squat position',
                    'Explode upward, jumping off the ground',
                    'Land softly, absorb impact with bent knees',
                    'Immediately descend into next squat',
                ],
                'target_reps': 8,
                'hold_duration': 0,
                'category': 'strength',
                'dosage_by_capability': _STRENGTH_DOS,
            },
        ]
    },

    # ── HIP HINGE PATTERN ────────────────────────────────────────────────────
    'hip_hinge_family': {
        'family_id': 'hip_hinge_family',
        'name': 'Hip Hinge Pattern',
        'icon': '🏋️',
        'description': 'Posterior chain strength — glutes, hamstrings, lower back',
        'movement_type': 'strength',
        'levels': [
            {
                'level': 1,
                'exercise_id': 'glute_bridge',
                'name': 'Glute Bridge',
                'label': 'Level 1 — Foundation',
                'description': 'Lying hip thrust — safest glute and hamstring activation.',
                'instructions': [
                    'Lie on your back, knees bent, feet flat on floor hip-width',
                    'Push through feet and squeeze glutes to lift hips',
                    'Form a straight line from knees to shoulders',
                    'Hold 2 seconds at top, then lower slowly',
                ],
                'target_reps': 12,
                'hold_duration': 0,   # 2s at top is a movement cue, not a hold exercise
                'category': 'strength',
            },
            {
                'level': 2,
                'exercise_id': 'single_leg_glute_bridge',
                'name': 'Single Leg Glute Bridge',
                'label': 'Level 2',
                'description': 'One-legged glute bridge — adds balance and single-leg load.',
                'instructions': [
                    'Lie on back, one knee bent foot flat, opposite leg extended straight',
                    'Push through bent leg foot to lift hips',
                    'Keep hips level — don\'t let them rotate',
                    'Complete reps on one side, then switch',
                ],
                'target_reps': 10,
                'hold_duration': 0,   # 2s at top is a movement cue, not a hold exercise
                'category': 'strength',
            },
            {
                'level': 3,
                'exercise_id': 'deadlift_dumbbell',
                'name': 'Dumbbell Deadlift',
                'label': 'Level 3',
                'description': 'Hip hinge with dumbbells — loading the full posterior chain.',
                'instructions': [
                    'Stand holding dumbbells in front of thighs',
                    'Hinge at hips (send hips backward, not bend knees)',
                    'Lower dumbbells along legs to mid-shin level',
                    'Drive hips forward to return to standing',
                ],
                'target_reps': 10,
                'hold_duration': 0,
                'category': 'strength',
            },
            {
                'level': 4,
                'exercise_id': 'single_leg_rdl',
                'name': 'Single Leg RDL',
                'label': 'Level 4 — Advanced',
                'description': 'Single leg Romanian deadlift — balance + posterior chain at once.',
                'instructions': [
                    'Stand on one leg, slight soft bend in knee',
                    'Hinge forward at hip, extending opposite leg behind you',
                    'Lower toward floor while keeping back flat',
                    'Squeeze glute to return to standing',
                ],
                'target_reps': 8,
                'hold_duration': 0,
                'category': 'strength',
            },
        ]
    },

    # ── LUNGE PATTERN ────────────────────────────────────────────────────────
    'lunge_family': {
        'family_id': 'lunge_family',
        'name': 'Lunge Pattern',
        'icon': '🤸',
        'description': 'Single-leg strength and dynamic stability',
        'movement_type': 'strength',
        'levels': [
            {
                'level': 1,
                'exercise_id': 'step_ups',
                'name': 'Step Ups',
                'label': 'Level 1 — Foundation',
                'description': 'Step onto a low platform — controlled and safe.',
                'instructions': [
                    'Stand in front of a step or sturdy box (6–8 inches)',
                    'Step up with one foot, bring other foot up to stand on step',
                    'Step back down one foot at a time',
                    'Alternate leading foot each rep',
                ],
                'target_reps': 10,
                'hold_duration': 0,
                'category': 'strength',
            },
            {
                'level': 2,
                'exercise_id': 'reverse_lunges',
                'name': 'Reverse Lunges',
                'label': 'Level 2',
                'description': 'Step backward into a lunge — safer for knees than forward lunge.',
                'instructions': [
                    'Stand tall, feet together',
                    'Step one foot back and lower back knee toward floor',
                    'Front thigh parallel to floor, front shin vertical',
                    'Push through front foot to return to standing',
                ],
                'target_reps': 10,
                'hold_duration': 0,
                'category': 'strength',
            },
            {
                'level': 3,
                'exercise_id': 'lunges',
                'name': 'Forward Lunges',
                'label': 'Level 3',
                'description': 'Step forward into a lunge — classic dynamic strength.',
                'instructions': [
                    'Stand tall, feet together',
                    'Step one foot forward, lower back knee toward floor',
                    'Front knee stays over ankle (not forward of toes)',
                    'Push back foot through to return to standing',
                ],
                'target_reps': 10,
                'hold_duration': 0,
                'category': 'strength',
            },
            {
                'level': 4,
                'exercise_id': 'lateral_lunges',
                'name': 'Lateral Lunges',
                'label': 'Level 4',
                'description': 'Side-stepping lunge — hip/groin strength and frontal plane movement.',
                'instructions': [
                    'Stand with feet together',
                    'Step wide to one side, sit back into that hip',
                    'Keep the opposite leg straight',
                    'Push through the bent leg to return to center',
                ],
                'target_reps': 10,
                'hold_duration': 0,
                'category': 'strength',
            },
            {
                'level': 5,
                'exercise_id': 'bulgarian_split_squats',
                'name': 'Bulgarian Split Squats',
                'label': 'Level 5 — Advanced',
                'description': 'Rear-foot elevated split squat — maximum single-leg loading.',
                'instructions': [
                    'Stand 2 feet in front of a bench/chair',
                    'Place one foot on bench behind you (shoelaces down)',
                    'Lower back knee toward floor — front thigh parallel',
                    'Drive through front foot to return',
                ],
                'target_reps': 8,
                'hold_duration': 0,
                'category': 'strength',
            },
        ]
    },

    # ── PUSH PATTERN ─────────────────────────────────────────────────────────
    'push_family': {
        'family_id': 'push_family',
        'name': 'Push & Core',
        'icon': '💪',
        'description': 'Upper body pushing strength and core stability',
        'movement_type': 'strength',
        'levels': [
            {
                'level': 1,
                'exercise_id': 'tricep_extensions',
                'name': 'Tricep Extensions',
                'label': 'Level 1 — Foundation',
                'description': 'Overhead tricep press — gentle upper body starting point.',
                'instructions': [
                    'Hold a light dumbbell overhead with both hands',
                    'Bend elbows, lowering weight behind your head',
                    'Extend arms back to fully straight overhead',
                    'Keep upper arms still throughout',
                ],
                'target_reps': 12,
                'hold_duration': 0,
                'category': 'strength',
            },
            {
                'level': 2,
                'exercise_id': 'push_ups',
                'name': 'Push Ups',
                'label': 'Level 2',
                'description': 'Standard push-up (use knees if needed). Classic push pattern.',
                'instructions': [
                    'Plank position — hands under shoulders, body straight',
                    'Lower chest to floor, elbows at ~45° from body',
                    'Push back to start — full arm extension',
                    '(Knee push-ups are perfectly acceptable here)',
                ],
                'target_reps': 10,
                'hold_duration': 0,
                'category': 'strength',
            },
            {
                'level': 3,
                'exercise_id': 'planks',
                'name': 'Plank Hold',
                'label': 'Level 3 — Advanced',
                'description': 'Static plank for core and shoulder endurance.',
                'instructions': [
                    'Forearm plank or full straight-arm plank',
                    'Keep body in one straight line — no sagging hips, no raised hips',
                    'Brace your core, squeeze glutes',
                    'Hold for as long as possible with perfect form',
                ],
                'target_reps': 1,
                'hold_duration': 30,
                'category': 'strength',
            },
        ]
    },

    # ── BALANCE & STABILITY ───────────────────────────────────────────────────
    'balance_family': {
        'family_id': 'balance_family',
        'name': 'Balance & Stability',
        'icon': '⚖️',
        'description': 'Proprioception and neuromuscular control — crucial for injury prevention',
        'movement_type': 'balance',
        'levels': [
            {
                'level': 1,
                'exercise_id': 'double_leg_balance',
                'name': 'Double Leg Balance',
                'label': 'Level 1 — Foundation',
                'description': 'Balance on two feet — the starting point for stability work.',
                'instructions': [
                    'Stand with feet hip-width apart on a firm surface',
                    'Slight soft bend in knees',
                    'Hold completely still — minimize swaying',
                    'Try eyes open first; try eyes closed for more challenge',
                ],
                'target_reps': 1,
                'hold_duration': 30,
                'category': 'balance',
            },
            {
                'level': 2,
                'exercise_id': 'single_leg_balance',
                'name': 'Single Leg Balance',
                'label': 'Level 2',
                'description': 'Balance on one foot — fundamental proprioception test.',
                'instructions': [
                    'Stand on one foot, slight bend in standing knee',
                    'Hold arms out to sides for balance if needed',
                    'Hold as still as possible',
                    'Aim for 20+ seconds each side',
                ],
                'target_reps': 1,
                'hold_duration': 20,
                'category': 'balance',
            },
            {
                'level': 3,
                'exercise_id': 'lateral_gait_training',
                'name': 'Lateral Gait Training',
                'label': 'Level 3',
                'description': 'Sidestepping in a controlled manner — dynamic stability.',
                'instructions': [
                    'Stand with feet hip-width apart',
                    'Step sideways 2–3 metres and back',
                    'Keep hips level throughout',
                    'Don\'t cross your feet',
                ],
                'target_reps': 10,
                'hold_duration': 0,
                'category': 'balance',
                'dosage_by_capability': _UNILAT_DOS,  # dynamic reps, not static hold
            },
            {
                'level': 4,
                'exercise_id': 'clock_reaches',
                'name': 'Clock Reaches',
                'label': 'Level 4',
                'description': 'Balance on one leg and reach to clock positions — advanced stability.',
                'instructions': [
                    'Stand on one leg',
                    'Imagine a clock face on the floor around your foot',
                    'Reach free leg to 12, 3, 6, and 9 o\'clock positions',
                    'Touch floor lightly, return to start — that\'s 1 rep',
                ],
                'target_reps': 5,
                'hold_duration': 0,
                'category': 'balance',
                'dosage_by_capability': _UNILAT_DOS,  # dynamic reps, not static hold
            },
            {
                'level': 5,
                'exercise_id': 'tandem_walking',
                'name': 'Tandem Walking',
                'label': 'Level 5 — Advanced',
                'description': 'Heel-to-toe walking in a straight line — highest stability challenge.',
                'instructions': [
                    'Place one foot directly in front of the other (heel to toe)',
                    'Walk in a perfectly straight line',
                    'Keep arms out for balance',
                    '10 steps forward and back = 1 rep',
                ],
                'target_reps': 3,
                'hold_duration': 0,
                'category': 'balance',
                'dosage_by_capability': _UNILAT_DOS,  # dynamic reps, not static hold
            },
        ]
    },

    # ── CARDIO PATTERN ────────────────────────────────────────────────────────
    'cardio_family': {
        'family_id': 'cardio_family',
        'name': 'Cardio Endurance',
        'icon': '🏃',
        'description': 'Aerobic capacity and cardiovascular fitness',
        'movement_type': 'cardio',
        'levels': [
            {
                'level': 1,
                'exercise_id': 'marching_on_spot',
                'name': 'Marching on Spot',
                'label': 'Level 1 — Foundation',
                'description': 'March in place — the gentlest cardio starting point.',
                'instructions': [
                    'March in place at a comfortable pace',
                    'Lift knees to a comfortable height (no need to go high)',
                    'Swing arms naturally',
                    'Do this for 1–2 minutes continuously',
                ],
                'target_reps': 1,
                'hold_duration': 90,
                'category': 'cardio',
            },
            {
                'level': 2,
                'exercise_id': 'high_knees',
                'name': 'High Knees',
                'label': 'Level 2',
                'description': 'March with knees driving up to hip height — elevated intensity.',
                'instructions': [
                    'March/jog in place, driving knees up to hip height',
                    'Pump arms for momentum',
                    'Increase pace as comfortable',
                    'Do for 1 minute continuously',
                ],
                'target_reps': 1,
                'hold_duration': 60,
                'category': 'cardio',
            },
            {
                'level': 3,
                'exercise_id': 'jumping_jacks',
                'name': 'Jumping Jacks',
                'label': 'Level 3',
                'description': 'Classic jumping jacks — coordinated full-body cardio.',
                'instructions': [
                    'Start standing, feet together, arms at sides',
                    'Jump feet apart while raising arms overhead',
                    'Jump back to start position',
                    'Maintain rhythm for 1 minute',
                ],
                'target_reps': 30,
                'hold_duration': 0,
                'category': 'cardio',
            },
            {
                'level': 4,
                'exercise_id': 'butt_kicks',
                'name': 'Butt Kicks',
                'label': 'Level 4',
                'description': 'Running in place, kicking heels to glutes — higher intensity.',
                'instructions': [
                    'Jog in place',
                    'Kick your heels up toward your glutes with each step',
                    'Keep upper body tall',
                    'Maintain for 1 minute',
                ],
                'target_reps': 1,
                'hold_duration': 60,
                'category': 'cardio',
            },
            {
                'level': 5,
                'exercise_id': 'mountain_climbers',
                'name': 'Mountain Climbers',
                'label': 'Level 5 — Advanced',
                'description': 'High-intensity full-body cardio from plank position.',
                'instructions': [
                    'Start in full plank position',
                    'Drive one knee toward chest quickly',
                    'Switch legs rapidly — like running in place in plank',
                    'Maintain 30–60 seconds with controlled breathing',
                ],
                'target_reps': 20,
                'hold_duration': 0,
                'category': 'cardio',
            },
        ]
    },
}

# All families in the order we gate test them
DEFAULT_GATE_TEST_FAMILIES = [
    'squat_family',
    'hip_hinge_family',
    'lunge_family',
    'push_family',
    'balance_family',
    'cardio_family',
]


# ============================================================================
# MAP: exercise_id → which family it belongs to
# ============================================================================

EXERCISE_TO_FAMILY = {}
for _family_id, _chain in PROGRESSION_CHAINS.items():
    for _lvl in _chain['levels']:
        EXERCISE_TO_FAMILY[_lvl['exercise_id']] = _family_id
        # Backfill dosage_by_capability for levels that don't have it yet
        if 'dosage_by_capability' not in _lvl:
            cat = _chain.get('movement_type', 'strength')
            if cat == 'balance':
                _lvl['dosage_by_capability'] = _BALANCE_DOS
            elif cat == 'cardio':
                _lvl['dosage_by_capability'] = _CARDIO_DOS
            else:
                # Check if unilateral (single leg)
                _is_unilateral = any(word in _lvl['exercise_id']
                                     for word in ('single_leg', 'unilateral', 'bulgarian', 'rdl'))
                _lvl['dosage_by_capability'] = _UNILAT_DOS if _is_unilateral else _STRENGTH_DOS


# ============================================================================
# SCORING HELPERS
# ============================================================================

# Map capability string → numeric
CAPABILITY_STRING_TO_NUMERIC = {
    'cannot_do': 1,
    'struggling': 2,
    'manageable': 3,
    'easy': 4,
}

CAPABILITY_NUMERIC_TO_STRING = {v: k for k, v in CAPABILITY_STRING_TO_NUMERIC.items()}
CAPABILITY_NUMERIC_TO_STRING[5] = 'easy'   # 5 = "ready to advance" (still "easy" label)


def classify_performance(reps_completed, target_reps, difficulty, pain, level_data=None):
    """
    Given performance at a level, return (capability_str, sets, reps, label).

    capability_str one of: 'cannot_do', 'struggling', 'manageable', 'easy'

    If level_data is provided, sets/reps are read from the dosage table so they
    always agree with what the prescription engine will calculate later.
    The hardcoded fallbacks (2,7 / 3,10 / 3,12) remain for backwards-compat when
    level_data is not passed.
    """
    # Pain override — always regress
    if pain >= 6:
        return 'cannot_do', 0, 0, 'Cannot Do — Pain Too High'

    # Zero reps = can't do it
    if reps_completed == 0:
        return 'cannot_do', 0, 0, 'Cannot Do'

    completion = reps_completed / max(target_reps, 1)

    # Determine capability bucket
    if completion < 0.4 or difficulty >= 8:
        cap_str, cap_num, label = 'struggling', 2, 'Struggling'
    elif completion < 0.8 or difficulty >= 5:
        cap_str, cap_num, label = 'manageable', 3, 'Manageable'
    else:
        cap_str, cap_num, label = 'easy', 4, 'Easy'

    # Look up dosage from table if level_data available (matches prescription engine)
    if level_data:
        dosage_table = level_data.get('dosage_by_capability', _STRENGTH_DOS)
        s, r, h = dosage_table.get(cap_num, dosage_table.get(3, (2, 10, 0)))
        if level_data.get('hold_duration', 0) > 0 and h == 0:
            h = level_data['hold_duration']; r = 1
        return cap_str, s, r, label

    # Hardcoded fallbacks (backwards-compat, no level_data)
    if cap_str == 'struggling':
        return 'struggling', 2, 7, 'Struggling'
    if cap_str == 'manageable':
        return 'manageable', 3, 10, 'Manageable'
    return 'easy', 3, 12, 'Easy'


def classify_performance_numeric(reps_completed, target_reps, difficulty, pain):
    """
    Returns capability_numeric (1-5) instead of string.
    Also returns (sets, reps) directly from the dosage table.
    """
    cap_str, sets, reps, label = classify_performance(
        reps_completed, target_reps, difficulty, pain
    )
    numeric = CAPABILITY_STRING_TO_NUMERIC.get(cap_str, 3)
    return numeric, cap_str, sets, reps, label


def get_dosage_for_level(level_data, capability_numeric):
    """
    Looks up the correct (sets, reps, hold) for a level at a given capability.

    Args:
        level_data       : one entry from a family's 'levels' list
        capability_numeric: int 1-5

    Returns:
        (sets, reps, hold_seconds)
    """
    dosage_table = level_data.get('dosage_by_capability', _STRENGTH_DOS)
    sets, reps, hold = dosage_table.get(capability_numeric, dosage_table.get(3, (2, 10, 0)))

    # Honour hold_duration from level definition if set
    if level_data.get('hold_duration', 0) > 0 and hold == 0:
        hold = level_data['hold_duration']
        reps = 1

    return sets, reps, hold


def get_prescription_sets_reps(capability, level_data):
    """
    Return (sets, reps) for a given capability level and exercise level data.
    LEGACY — kept for backward compatibility.
    """
    hold = level_data.get('hold_duration', 0)

    if capability == 'cannot_do':
        return 0, 0
    if capability == 'struggling':
        return 2, (1 if hold else 7)
    if capability == 'manageable':
        return 3, (1 if hold else 10)
    # easy
    return 3, (1 if hold else 12)