"""
VYAYAM Pre-Match Stretching Protocol
Defines the 12 stretches used in the pre-football stretching session.

Order follows proper physio joint-to-movement progression:
passive mobilisation → isolated activation → integrated movement → full intensity
"""

PRE_MATCH_STRETCHES = [
    {
        'stretch_id': 'hip_flexor_stretch',
        'name': 'Hip Flexor Stretch',
        'duration_seconds': 30,
        'side': 'left',
        'muscle_group': 'Hip Flexors',
        'coaching_cue': 'Kneel on one knee, push hips forward until you feel a stretch in the front of your hip. Keep torso upright.',
        'icon': '🦵',
    },
    {
        'stretch_id': 'hip_flexor_stretch',
        'name': 'Hip Flexor Stretch',
        'duration_seconds': 30,
        'side': 'right',
        'muscle_group': 'Hip Flexors',
        'coaching_cue': 'Switch sides. Same position — push hips forward gently, keep chest tall.',
        'icon': '🦵',
    },
    {
        'stretch_id': 'quadriceps_stretch',
        'name': 'Standing Quadriceps Stretch',
        'duration_seconds': 30,
        'side': 'left',
        'muscle_group': 'Quadriceps',
        'coaching_cue': 'Stand on one leg, grab ankle behind you, pull heel toward glute. Keep knees together.',
        'icon': '🏃',
    },
    {
        'stretch_id': 'quadriceps_stretch',
        'name': 'Standing Quadriceps Stretch',
        'duration_seconds': 30,
        'side': 'right',
        'muscle_group': 'Quadriceps',
        'coaching_cue': 'Switch legs. Pull heel to glute, keep standing leg slightly bent for balance.',
        'icon': '🏃',
    },
    {
        'stretch_id': 'hamstring_stretch',
        'name': 'Standing Hamstring Stretch',
        'duration_seconds': 30,
        'side': 'both',
        'muscle_group': 'Hamstrings',
        'coaching_cue': 'Place one foot forward on a low surface, hinge at hips keeping back flat. Feel stretch behind thigh.',
        'icon': '🧘',
    },
    {
        'stretch_id': 'calf_stretch',
        'name': 'Wall Calf Stretch',
        'duration_seconds': 30,
        'side': 'both',
        'muscle_group': 'Calves',
        'coaching_cue': 'Lean against wall with one leg back, heel pressed to floor. Keep back leg straight.',
        'icon': '🧱',
    },
    {
        'stretch_id': 'hip_circles',
        'name': 'Hip Circles',
        'duration_seconds': 30,
        'side': 'both',
        'muscle_group': 'Hip Rotators',
        'coaching_cue': 'Stand on one leg, lift other knee to hip height and rotate in large circles. 15 seconds each direction.',
        'icon': '🔄',
    },
    {
        'stretch_id': 'knee_circles',
        'name': 'Knee Circles',
        'duration_seconds': 20,
        'side': 'both',
        'muscle_group': 'Knee Joint & Synovial Fluid',
        'coaching_cue': 'Stand with feet together, hands on knees. Circle both knees slowly clockwise for 10 seconds, then counter-clockwise. Lubricates the knee joint.',
        'icon': '🔵',
    },
    {
        'stretch_id': 'butt_kicks',
        'name': 'Butt Kicks',
        'duration_seconds': 30,
        'side': 'both',
        'muscle_group': 'Hamstrings & Knee Flexors',
        'coaching_cue': 'Jog in place kicking heels up toward your glutes. Keep knees pointing down, not forward. Quick rhythm, stay on toes. Mimics the recovery phase of sprinting.',
        'icon': '👟',
    },
    {
        'stretch_id': 'leg_swings',
        'name': 'Dynamic Leg Swings',
        'duration_seconds': 30,
        'side': 'both',
        'muscle_group': 'Hip Flexors & Hamstrings',
        'coaching_cue': 'Hold wall for balance. Swing one leg forward and back in controlled pendulum motion. Keep core tight.',
        'icon': '⚡',
    },
    {
        'stretch_id': 'ankle_rotations',
        'name': 'Ankle Rotations',
        'duration_seconds': 20,
        'side': 'both',
        'muscle_group': 'Ankles',
        'coaching_cue': 'Lift one foot, rotate ankle in slow circles. 10 seconds clockwise, 10 counter-clockwise.',
        'icon': '🦶',
    },
    {
        'stretch_id': 'high_knees',
        'name': 'High Knees (Dynamic Warm-Up)',
        'duration_seconds': 30,
        'side': 'both',
        'muscle_group': 'Full Lower Body',
        'coaching_cue': 'Jog in place driving knees to hip height. Pump arms opposite to legs. Quick light feet.',
        'icon': '🔥',
    },
]

TOTAL_STRETCHES = len(PRE_MATCH_STRETCHES)
TOTAL_PROTOCOL_DURATION = sum(s['duration_seconds'] for s in PRE_MATCH_STRETCHES)
