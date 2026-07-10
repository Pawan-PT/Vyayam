"""Straight Leg Raise — prescription tier (2026-07 dark camera coach).

Subclasses StraightLegRaisesV2 verbatim. Distinct key so the therapist-tier
coach (js_type SLR_RX: supine hip-flexion rep cycle + knee-bend fault cue)
ships DARK; the existing `straight_leg_raises` stays MANUAL for self-serve.
"""

from .straight_leg_raises_v2 import StraightLegRaisesV2


class StraightLegRaiseRxV2(StraightLegRaisesV2):
    pass
