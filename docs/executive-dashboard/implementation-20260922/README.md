# Executive dashboard — final staged-testing handover

**STAGING IS AVAILABLE FOR OWNER HANDS-ON TESTING; FORMAL OWNER UAT IS NOT YET READY FOR SIGN-OFF.** The approved HTML, audit corrections, HR workspace and standard-company branding are implemented on the exact staged candidate. The native/backend/browser technical qualification is documented below. UI07/UI08/UI20 source-definition decisions and owner visual/financial acceptance remain open; historical evidence remains tied to its older source.

- [B01–B13 closure ledger](closure-ledger.md) ([CSV](closure-ledger.csv)).
- [UI01–UI38 parity matrix](ui-parity-matrix.md) ([CSV](ui-parity-matrix.csv)).
- [Qualification checkpoint](qualification-checkpoint.md).
- [Final staged-testing handover and owner entry](final-handover.md).

## Source identity and boundaries

Audited baseline `3efeab142865a95053e4ea21e77a253763cdce6c` remains historical. Final published feature `b9461b76f3b1a1e1085fda87d55f6ef66ecca9b9` / build **38514095** passed **120/120 native tests**, 65 frontend checks and 28 native bilingual/theme/viewport cases (532 retained PNGs, four PDFs). Staging `28b37d90d77571383b37e70212681e9730d5cf40` / build **38326320** has the same addon trees and both installed versions **19.0.1.5.0** after a backed-up dashboard-only upgrade. Prior backend-identical 34 independent staged probes passed; final staged browser and RPC evidence is source-bound separately. **Staging is available for owner hands-on testing; formal owner UAT readiness awaits UI07/UI08/UI20 source-definition decisions and acceptance.**

Selected HTML SHA-256: `36ec95831f3f1e82e0709594d5c177938e3b3805ccd763b1e59c13933b2d7f4a` (verified from attached bytes and HANDOVER_MANIFEST.json). This is the HR and reusable-company-branding edition. Original handover and raw customer/Enterprise evidence remain private. The corrected private qualification archive (`Adams_Dashboard_Private_Qualification_20260923.zip`, SHA-256 `59f86fa3908688b1bec4b2e305d495f7bf2cb915f81b9ad0daf09f2a790b4b75`) includes the 15 paired HTML/Odoo screenshots and private probe/export indexes. The full 532 native screenshots remain in development build artifacts; the compact archive indexes their manifest and retains six selected PNGs.

The approved reference targets dashboard-owned content. Native Odoo navigation/profile/company controls remain the host interface; prototype fixtures, simulated destinations and review controls are excluded. Real data and optional-app capability states differ from prototype fixtures. UI07/UI08/UI20 source-dependent differences require explicit owner disposition, not silent parity acceptance.

Development and authorized staging only. PR #214 remains draft, unmerged. Main and production are prohibited. Owner acceptance and production approval remain separate.

## Remaining formal-acceptance gates

1. Owner reviews the 15 paired screenshots and staged workflows at the [dashboard entry](https://adamsmen-staging-38326320.dev.odoo.com/odoo/action-1004), including reports, source actions, exports, Arabic/RTL, appearance, scrolling, print and representative signed figures.
2. Owner decides UI07 comparable-period meaning, UI08 bank-versus-cash classification and UI20 prototype-money versus source-backed order-count disposition, or explicitly accepts the truthful unavailable/combined/count presentations.
3. Record owner observations and formal acceptance separately. Staging has one authorized company and no optional Attendance, Time Off or Planning apps; native fixtures cover those pathways without claiming live testing there. Keep PR #214 draft and main/production untouched.
