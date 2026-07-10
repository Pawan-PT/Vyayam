"""Dumbbell Shoulder Press — prescription tier (2026-07 dark camera coach).

Subclasses TricepExtensionsV2 (overhead elbow-extension cycle, H2 green at
97.4) with press-range targets — same phase names so the parent\'s phase
machine and scorer stay coherent. The live rep cycle + asymmetric-press
fault live in the JS coach (PRESS_DB_RX).
"""

from .tricep_extensions_v2 import TricepExtensionsV2


class DbShoulderPressRxV2(TricepExtensionsV2):

    def get_target_poses(self):
        return {
            'bent':      {'avg_elbow': 85,        'tolerance': 15},
            'extending': {'avg_elbow': (85, 168), 'tolerance': 18},
            'straight':  {'avg_elbow': 168,       'tolerance': 12},
            'flexing':   {'avg_elbow': (85, 168), 'tolerance': 18},
        }
