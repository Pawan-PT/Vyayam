# clinical_audit — STATUS: SCAFFOLDING, NOT COVERAGE (ledger E7, 2026-07)

The generators (and their 1,230 lines of tests) validate CASE GENERATION
only. All three oracles and all three watchers `raise NotImplementedError`;
the invariants files are 4-line stubs. Nothing in this package asserts
engine behavior yet — do not mistake a green run here for clinical
coverage. Real engine assertions live in strength_app/tests/
(test_deep_audit.py, test_exam_2026_07_gaps.py).
