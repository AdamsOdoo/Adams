# Intentional deviations from the approved HTML

The approved HTML (SHA-256 `36ec95831f3f1e82e0709594d5c177938e3b3805ccd763b1e59c13933b2d7f4a`) remains
the visual target. The rows below are the only intended differences in the candidate. Items marked
*existing* were accepted earlier and are unchanged in this pass. Mandatory data and security
differences (native statuses, signed values, restricted and not-installed states) follow the
reference precedence in the execution task: owner decisions, truthful native data and security first.

| ID | Where | Approved HTML | Candidate | Why (user benefit) | Status |
| --- | --- | --- | --- | --- | --- |
| D01 | Rail company identity | Stacked layout above 26 characters | Stacked above 18 characters; the stacked name uses the full width | A 26-character name no longer wraps to four lines beside the logo | New |
| D02 | Company selectors | Fixed-width select | `dir="auto"`, ellipsis, whole row on phones | Long or mixed-script names keep their beginning visible in English and Arabic | New |
| D03 | Chart without its three approved series | Always a chart | Names the blocking state; Retry only when a reload can help | No button that cannot work; no server error without the finance addon | New |
| D04 | HR missing apps | Not shown by the prototype | "Attendances / Time Off / Planning is not installed" | Required by the HR addendum; the owner can see which app is missing | New |
| D05 | URL | Static prototype | `/odoo/executive-dashboard` with department, HR tab and non-default dates | Reload, Back and shared links reopen the same view | New |
| D06 | More menu | Pointer menu | Outside press, Escape with focus return, Arrow/Home/End | Keyboard and pointer dismissal (UI04) | New |
| D07 | App icon | Not part of the prototype | Four-square mark on the brand purple, from the approved app bar | The app is recognisable on the home menu and phone menu | New |
| D08 | Delivery status table | One unit in the column header | Unit on every row | Rows can use different units (Units, Hours); quantities in different units are never added | Existing |
| D09 | Status chips (Sales, Procurement, HR) | Prototype labels ("To deliver", "To receive") | Native Odoo labels (delivery status, receipt status, order and leave states) | Matches the linked standard reports; no recolouring of a state the record does not have | Existing |
| D10 | HR Time off | No leave-hours card | "Approved leave hours (signed)" card on Time off only | Accepted capability kept where it belongs; native sign convention (requests are negative) is stated | Existing (placement new) |
| D11 | Page footer | Sample-data footer | "Last updated … Source completeness has not been assessed." and Data & trust | Real provenance instead of prototype text | Existing |
| D12 | Procurement | Overview only | Late-receipts worklist panel below the overview | Accepted current-item worklist (UI20), now in the approved panel style | Existing (style new) |
| D13 | HR "Apply period" | Always enabled | Enabled only after a date changes | Prevents a no-op reload | Existing |
| D14 | Department names | Short names | Odoo's full hierarchical department name | Native business data is shown as recorded, not rewritten | Existing |
| D15 | HR Department filter | Selector as wide as its longest option | At most 220 px with an ellipsis on desktop; Department and Status share a row on phones | Long department paths no longer squeeze the search field; full names stay in the list | New |
| D16 | Inventory support panels | "Open a row to see stock for that exact product, location and date"; "hidden quantities" | States that current quantities use native stock records and historical on-hand uses the stock date; "quantity filters" | The prototype did not distinguish current and historical stock; the text now matches what the table shows | Existing |
| D17 | HR Team by department | Four fixed departments | All departments (up to 25) in a scroll area that shows a shadow while more rows are above or below | Companies with more departments see every team without the panel growing; a cut-off row no longer looks like the end | New |
| D18 | Rail labels | One line, overflowing the 160 px rail at 901–1100 px | Labels wrap inside the rail at 1100 px and below and in Arabic; English above 1100 px keeps the approved single line | No text runs into the dashboard content at tablet widths or with longer translations | New |

Not a deviation but an evidence caveat: Community Odoo 19 has no dark scheme. Its `web.assets_web_dark`
bundle keeps the light variables, because only Enterprise's `web_enterprise` sets
`$o-webclient-color-scheme` to dark. The local dark captures therefore append the dashboard's own
stylesheets compiled with the dark value to the served CSS. This approximates Enterprise dark mode for the
dashboard content only, in English. Odoo's shell stays light, and Arabic dark was not rendered locally.
Enterprise dark mode on Odoo.sh remains the acceptance surface.
