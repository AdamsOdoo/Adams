# Independent review — dashboard visual polish, 21 September 2026

## Final engineering and staging handoff review — 22 September 2026

The separate reviewer finds no remaining Critical or High engineering or staging
defect in the evidence for owner UAT. The recovered checkout is the remote feature
commit `948a006a241603ba8364449cd9dfdaf81b1bb3e4`, tree
`7fb2118d46b3730453eb6627ffec9333aaa8d439`; its dashboard addon trees are exactly
`1aaf301bf57fbf5f479d1d013d4c40a625ee3fbc` and
`7df8ae98326751406f665a75ed9e938b70156862`. The staging deployment is recorded as
`9af98d4248090f2be3ceefb5d59bca36258b7c3a`, tree
`2f33a66be48f77bc18f02eff780359a02483bc59`, build38419464, with the same qualified
addon trees. The staging commit's five changed paths are confined to those addons.

The reviewer inspected the final desktop staging captures for the overview in
English Light and Arabic Light/Dark, Finance cards and liquidity, Sales, Inventory,
and the actual Profit and Loss source report. They show coherent native-theme and
RTL rendering, visible accounting warnings, populated operational data and the
expected report-first return path. These desktop captures supplement, and do not
replace, the independently reviewed 240-image responsive development matrix.

The retained final 21-value list is structurally identical after JSON parsing to
the before-change 21-value list. The retained cash evidence is likewise exactly
equal, including all 21 account rows and the opening/net-movement/closing bridge.
This verifies preservation at the explicitly recorded 2026-09-01–2026-09-21 scope;
it does not certify the financial meaning or completeness of those values. The
staging interaction account in [the UAT handoff](uat-handoff-20260922.md) accurately
distinguishes directly exercised paths, automated error/retry coverage and unclaimed
printer/concurrency work. The English/Arabic CSV difference is limited to the
translated Count unit (`Count` / `العدد`); numerical values, sources and scope retain
parity. English (US)/Dark and the default saved view are recorded as restored after
testing. HR remains disabled.

One handoff-publication gate remained open at the time of this review: the five
updated historical/status documents and the new UAT handoff were still uncommitted,
and PR #214's live draft description still named `c17dd27e`/`daf1280`, described
staging as unchanged and called qualification blocked. Publish the reviewed docs
and replace that stale summary with the exact final identities and owner-UAT
boundaries before presenting the handoff. This is not an application defect and
does not require another build, but the stale PR text must not be used for UAT.
Keep the PR draft; owner financial and visual acceptance remains pending.

## Final rendered-development disposition — 22 September 2026

Separate reviewer `/root/independent_dashboard_review` approves the exact candidate
`948a006a241603ba8364449cd9dfdaf81b1bb3e4`, tree
`7fb2118d46b3730453eb6627ffec9333aaa8d439`, build38418408, for development rendering.
All 40 contact sheets and selected Arabic full-resolution overview/stock originals
at 320/390/768/1024 in both themes were inspected. Both Medium issues are closed:
stock names/references remain visible, and the Arabic 390px balance-cutoff date
remains intact. No Critical, High or Medium rendered-development finding remains.
All 240 manifest sizes/hashes, ZIP integrity and archive checksum were independently
verified. Code review found no calculation/source/mapping/ACL/business-data changes.
See [exact identities and staging evidence](uat-handoff-20260922.md).

This is separate from owner financial/visual acceptance. Historical provisional
findings below are retained for provenance and do not reopen the closed defects.

## Historical checkpoint — superseded by the final disposition above

## Status

**Final independent approval is pending.** No Critical/High engineering finding
has been identified in the reviewed changes. One Medium visual finding requires
corrected rendered evidence before closure. Owner UAT and production authorization
remain separate; this review does not authorize either release or deployment to
production. PR #214 must remain draft pending owner acceptance.

The reviewer operated separately from the implementation agents, made no application
changes, and did not control the shared Cloud Browser. Visual conclusions below
come from actual retained Odoo screenshots; code and test results alone were not
treated as visual acceptance.

## Scope and source identities

Baseline: `d7f159f51316085cb7cb17c38b563c9921ebba14` on
`feature/executive-dashboard-report-first`, [PR #214](https://github.com/AdamsOdoo/Adams/pull/214).
Read the application instructions, harness onboarding, current enhancement/visual
contracts, and the pinned external verification/delivery skills. The harness pin
remained `10ec1d059b5ddc5d422875f68e0726cc500487ce`.

Reviewed shared SCSS typography, controls, tables, spacing, responsive/RTL/theme
rules; OWL XML conditions and retry handlers; Arabic strings; ranking units;
native source-dialog labeling/focus mechanism; and native screenshot instrumentation.
No changes to report models, calculations, financial definitions, mappings,
production configuration or permissions were introduced by the UI corrections.
Additional sales/stock permissions and stock records exist only in the disposable
rollback-isolated browser fixture. The separate negative-role test is unchanged.

| Candidate | Reviewed result |
|---|---|
| `90f4f6df8bf03b89509522eacec6746efa9e1985`, tree `682ee08ae42e17ba7fd156a831639f3060f37487` | No Critical/High code finding. Independently inspected 20 sheets covering 120 retained screenshots and three full-resolution Arabic originals; verified all 120 manifest hashes. Native build 38413084 recorded 65 tests, zero failures/errors. Requested populated stock/table/pager evidence and noted ISO-date wrapping. |
| `9134d6ac575253aceb2c84ffdef0afddc885c0b3`, tree `f8a0a55249174378efb5a85c732f337fffbcdf69` | Date spans preserve original date semantics. Added 27 bilingual stock products and native pagination assertions in the isolated fixture. Build 38413845 failed the new capture selector; not qualified. |
| `045921307c0e07c13c4586e426dcafdf1dfb34dc` | Corrected direct-child stock-action selector. Build 38414070 reported 65 tests, zero failures/errors, but temporary screenshots were removed by the platform. This run does not provide retained visual acceptance. |
| `793059d472608ecf4ef88db7b14e68ae7931d20a`, tree `2d3e44ecb1b938d288fbaa33f2fe7df5f65ba17b` | Reviewed evidence retention: exact capture-prefix coverage, exclusion of existing files, PNG/header and copied-byte hash verification, private permissions, unique run paths and atomic promotion. Original browser assertions remain intact. Build 38414698 reported 65 tests, zero failures/errors, 202.09 seconds and 67,319 queries. Independently inspected all 40 sheets covering 240 actual captures plus full-resolution Arabic inventory originals. Medium clipping finding below remains open. |
| `c17dd27e4eb982eee995f547d93e5e44de19b6a1`, tree `d74f08108ad3e7a2da1a4b16dc6e906ce2975f7d` | Reviewed removal of the shared stable scrollbar gutter, inventory column minima and new geometry/scroll regression assertions. No new Critical/High code finding. Corrected native visual evidence and staging verification are pending. First build 38415574 reported a platform error; this is not an application test pass. |

## Visual findings

### Open Medium — Arabic inventory identity clipping

The `793059d4` full-resolution stock-table captures at 390px and 768px visibly
clip the right edge of Product names/references. Mixed-script product names lose
trailing glyphs at the scrollport edge. The original narrow product column also
creates tall multi-line rows at compact widths.

Evidence includes `polish_inventory_table_ar_001_dark_390_*` and
`polish_inventory_table_ar_001_light_768_*` in the retained 240-image run.
The parent retained the run archive and source/build manifest; the reviewer
inspected its extracted originals and all 40 contact sheets. The screenshots
show actual disposable Odoo fixtures, not customer business data.

Candidate `c17dd27e` addresses the suspected shared gutter cause and gives the
stock Product/Location columns readable minimum widths. Added assertions test
the leading cell edge against client bounds, text containment within its cell,
horizontal access to the final Source data column, and absence of page overflow.
They restore the original horizontal position before screenshots. This code
correction is appropriate, but the finding is **not closed** until a successful
candidate-bound run and visual inspection confirm the result in both languages,
themes and representative compact widths, followed by staging verification.

### Resolved observation — dates split inside ISO values

Earlier narrow cards wrapped a date before its final day digits. The date-span
correction retains complete individual dates while allowing the range to wrap.
The `793059d4` captures confirm complete date strings at compact widths.

### Other inspected surfaces

Shared typography, theme surfaces, mirrored navigation, local stock filters,
numbered pagination, product/customer rankings and lower Sales panels are coherent
in the inspected states. No other Critical/High visual issue was identified.
Empty order rankings, CRM and procurement states reflect the fixture; they do not
prove populated customer scenarios. Page-two captures align the pager at the top
and do not themselves show the two remaining rows above it; the native assertions
verify those rows separately. Header-only mobile Finance captures do not constitute
full visual inspection of all Finance content.

## Remaining final gate

1. Obtain successful native results and retained screenshots for `c17dd27e` or an
   explicitly recorded successor; distinguish platform failures from test results.
2. Independently inspect corrected RTL stock identity edges and horizontal access;
   close the Medium finding only after observed rendering supports closure.
3. Verify authorized staging identity, successful module upgrade, unchanged
   critical values, populated operational surfaces and important interactions.
4. Review actual staging screenshots, restoration of user language/theme, final
   evidence retention and exact source/build handoff.
5. Record final independent result, remaining limitations and owner-UAT status.

Staging was last reported unchanged at `65ccfa9c`; post-upgrade acceptance is not
claimed here. Cloud Browser transport was reported disconnected while recovery
was being attempted. No final approval is inferred from this checkpoint.
