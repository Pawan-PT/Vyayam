"""Single-Leg Balance — prescription tier (2026-07 dark camera coach).

Subclasses SingleLegBalanceV2 verbatim (parent already carries targets:
stance_knee/lifted_knee/sway). Distinct key so the therapist-tier coach
(js_type BALANCE_RX: hold clock pauses on foot-down, hip-drop cue) ships
DARK without touching the live self-serve `single_leg_balance` (BALANCE).
"""

from .single_leg_balance_v2 import SingleLegBalanceV2


class SingleLegBalanceRxV2(SingleLegBalanceV2):
    pass
