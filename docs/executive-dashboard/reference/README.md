# Approved visual reference

`Adams_Dashboard_UI_Proposal.html` is the unchanged attachment, SHA-256
`36ec95831f3f1e82e0709594d5c177938e3b3805ccd763b1e59c13933b2d7f4a`.
It is review material, outside Odoo addon assets; never embed it in the dashboard.

The comparison reference must record these explicit owner adjustments separately:

- UI07: remove comparable-period percentages and unsupported comparison claims, including Revenue movement. Retain source-backed gross/net margins.
- UI08: bank/cash classifications come from standard Bank/Cash journals and their associated accounts. Preserve signs, count each account once, and expose unresolved classification honestly.
- UI20: Procurement money-versus-count decision remains deferred. Match truthful source-backed count labels and worklists, without fabricated monetary measures.
- Company: use the active authorized company's standard Odoo name and logo in both captures. Prototype company profiles are not application configuration.
- Exclude review toolbar and simulated Odoo shell from reference comparison regions. Keep the real Odoo shell and native appearance behavior active in actual captures.

Data substitutions for controlled comparisons must be recorded in both manifests;
they must not change reference geometry or conceal discrepancies. Original bytes
remain unchanged. Implementation captures must never replace this reference.

## Comparison command

Run `python3 scripts/dashboard-visual-compare.py reference.json actual.json new-output-directory`
with Pillow installed. Each private manifest contains `role` and `captures`.
The reference additionally records `html_sha256` and `adjustments`; actual records
`source_sha`, `build`, and `module_versions`.

Each capture has a unique filename-safe `id`, relative `file`, file `sha256`, and
`box: [left, top, right, bottom]` in physical pixels. These fields must match across
pairs: `browser`, `fonts`, `zoom`, `device_scale`, `theme`, `language`, `viewport`,
`content_width`, `company`, `dates`, `controls`, `data`, `state`, `region`.
The command refuses mismatched states, dimensions, masks, changed images, shared
baseline/actual files, duplicate or missing cases, and existing output directories.
It writes separate region captures, 50% overlays, enhanced differences and a
manifest. It never modifies inputs or automatically resizes images.

Exit 0 denotes identical pixels only, not complete functional acceptance. Exit 1
requires visual review and discrepancy resolution. Exit 2 means invalid evidence.
No similarity threshold waives visible defects. Unavoidable rendering variation
requires an explicit explanation linked to that pair. All department/HR states,
required viewports, themes and RTL still require coverage. This tool by itself is
not completed visual qualification. Keep business screenshots/manifests private.
