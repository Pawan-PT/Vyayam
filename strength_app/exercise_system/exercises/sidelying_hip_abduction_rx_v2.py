"""Side-lying Hip Abduction — prescription tier (2026-07 dark camera coach).

Subclasses HipAbductionSidelineV2 verbatim (H2 green at 87.3). Distinct key
so the therapist-tier coach (js_type SIDELYING_ABD_RX: top-leg lift reps +
roll-back fault) ships DARK; `hip_abduction_sideline` stays MANUAL.
"""

from .hip_abduction_sideline_v2 import HipAbductionSidelineV2


class SidelyingHipAbductionRxV2(HipAbductionSidelineV2):
    pass
