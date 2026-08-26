# V1 finding disposition

The row-by-row authoritative disposition is [`finding-disposition.md`](finding-disposition.md). It covers every Fable identifier in the independent report and binds it to work package, owner, regression/migration, backend/browser scenario, commit, and final gate.

Current implementation disposition before exact-head qualification:

- Implemented, qualification pending: A-1, A-2, O-1–O-5, PR-1–PR-6, PR-8, I-1–I-5, I-8, U-1–U-4, U-6–U-10, U-18, S-1, S-2, W-2–W-6, W-8, W-10, P-1–P-4 and P-6.
- Already fixed and regression-bound on the implementation baseline: O-4 and the safe missing-product behavior underlying PR-5.
- Accepted residual with explicit disclosure: S-5 plaintext-at-rest credential storage.
- Deferred outside v1: I-7 warehouse tree moves, S-4 Reviewer removal, and the P3 groups listed in `post-v1-backlog.md`.
- Conditional performance items P-5 and P-7–P-10 remain outside the release delta unless exact-head supported-load qualification proves them material.

No implementation-pending row becomes `Closed` until its automated, CI, Odoo.sh, live backend, browser, and where applicable two-run UAT gate is attached to one immutable candidate. No P0/P1 may remain for a `RELEASE READY` verdict.
