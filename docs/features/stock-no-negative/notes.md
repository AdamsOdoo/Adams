# Stock no negative

Status: in review (PR into `staging`) · Size: M · Branch: `feature/stock-no-negative` (from `origin/staging`) · Module (version): `adams_stock_no_negative` (19.0.1.0.0), depends on `stock` only

## What it does
A stock operation that would take a storable product below zero in an internal or transit location is refused on the server, with the product named in the message: "Not enough stock of <product>. This operation would make the on-hand quantity negative." It covers Validate on deliveries, internal transfers, returns to suppliers, scrap, inventory counts, Produce on manufacturing orders, Point of Sale pickings, and edits of done operations. A quantity typed above the stock on hand is refused as soon as the line is saved, so a transfer never shows *Ready* for stock that isn't there. The refusal rolls back the whole operation: no stock or accounting effect.

The check is per product, location, lot/serial number, package and owner. Stock already below zero (from before the install) can be raised by a receipt or a count but not lowered further. When two users validate the same stock at the same time, the second one waits and is then refused.

Not checked: consumables; supplier, customer, inventory-loss, production and other virtual locations (negative by design); the shared inter-company transit location (no company); the subcontracting locations (decision below).

This is a port of the negative-stock module built for another Odoo 19 project, renamed (`adams_` prefix), with the same behaviour plus the subcontracting rule below.

## Settings
Inventory > Configuration > Settings > Operations, per company, both off by default, changed only by Settings administrators (writing them needs `res.company` write access; no new group):
- **Bypass negative consumption prevention** (`res.company.adams_allow_negative_stock`): allows negative stock for every operation of the company.
- **Bypass negative consumption for Point of Sale** (`res.company.adams_pos_allow_negative_stock`, shown only where Point of Sale is installed): allows it for Point of Sale orders only. Shown ticked and read-only while the first bypass is on, which already includes Point of Sale; the company's own choice comes back when the first bypass is turned off.

The bypass is read from the company the stock location belongs to (else the line's company), not from the company the user is working in.

Point of Sale is detected at runtime (no dependency): a line is a PoS line when its operation type is a PoS configuration's or a warehouse's PoS type, or its move belongs to a PoS order (ship later). Standard Point of Sale validates its picking inside a savepoint: with the PoS bypass off, a sale of an out-of-stock product still completes and the session still closes, but its picking stays open (*Ready*, the session shows failed pickings) for the stock team; stock is unchanged.

## Subcontracting decision
Shira Pharma manufactures our products as a subcontractor. In standard Odoo a subcontracted receipt creates a subcontracting manufacturing order whose components are consumed at the company's *Subcontracting* location, or at the subcontractor's own location when the partner has one (`property_stock_subcontractor`, always a child of the company's subcontracting location). That location goes negative by standard design when the subcontractor uses components they hold themselves.

Rule: **the company's subcontracting location and every location under it are not checked.** The source module skipped only the company's location itself, so a subcontractor with its own location would have had its receipt refused (proved: `test_a14_subcontractor_own_location` errors with the original rule). Our own stock stays checked: components sent to the subcontractor (resupply transfers from WH/Stock) can't take our stock below zero.

## Acceptance criteria and tests
Tests in `addons/adams_stock_no_negative/tests/`.
- A1 Delivery beyond stock refused, nothing changes; exact quantity delivered → `TestNoNegativeStock.test_a1_*`
- A2 Stock of another serial, location, owner or package doesn't allow the move → `test_a2_*`
- A3 Internal transfer, scrap, count below zero, edit of a done line, line added to a done transfer refused → `test_a3_*` (5 tests)
- A4 Receipts, returns, replenishing negative stock, lot made up from untracked stock work → `test_a4_*`
- A5 Consumables, partner/virtual locations, inter-company transit not checked → `test_a5_*`
- A6 Company bypass allows negative stock for that company only → `test_a6_company_bypass`
- A7 Only Settings administrators change the bypasses → `test_a7_*`
- A8 Message names the product, not the location → `test_a8_*`
- A9 PoS pickings refused by default, allowed by the PoS bypass, which opens nothing else → `TestNoNegativeStockPos.test_a9_*`
- A10 Manufacturing consumption beyond stock refused → `TestNoNegativeStockMrp.test_a10_*`
- A11 Settings in English and Arabic (right to left) → screenshots `screens/{en_US,ar_001}/`
- A12 Quantity entered above stock refused on save; bypass allows it; components of one MO counted together → `test_a12_*` (5 tests)
- A13 PoS checkbox ticked and read-only under the company bypass → `test_a13_*`
- A14 Subcontracted receipt not refused (company subcontracting location and a subcontractor's own location); recorded components not refused; resupply from our stock checked → `TestNoNegativeStockSubcontracting.test_a14_*` (4 tests)
- A15 Negative stock topped up by a count (also to a higher negative figure); a lower count, delivery, scrap and entry from it refused → `test_a15_negative_stock_topped_up_by_count` (receipt top-up: `test_a4_receipts_and_returns_work`)
- A16 Real PoS orders: session closes with the PoS bypass (picking done, stock negative); without it the session closes and the picking stays open; same in "at session closing" stock mode → `TestNoNegativeStockPosSession.test_a16_*` (3 tests)
- A17 The bypass follows the company of the stock, not the user's current company → `test_a17_check_follows_the_company_of_the_stock`

## Test results
RESULTS_PLACEHOLDER

## Before installing on production
- **Correct the negative stock first.** On production two products are below zero today: **Bulk - FP00011 at −22,228 g** and **RM00043 at −0.52 kg**. Existing negative stock stays as it is after the install and only further decreases are refused, so any delivery, MO or PoS sale of these would be refused (PoS: the picking stays open). Correct them by a receipt or an inventory count (Inventory > Physical Inventory) before installing, and list any others with Inventory > Reporting > Stock, filter *Negative Stock*.
- Nothing to configure: the block is on after install. Decide whether the PoS bypass should be on for the shops (with it off, PoS sales of out-of-stock products leave open pickings to resolve).

## Post-merge test plan on staging
Install **Adams Stock No Negative** (Apps), then with each bypass off and then on:
1. A delivery of more than the stock on hand: typing the quantity is refused; with the company bypass on it is accepted and validated.
2. A manufacturing order with a missing component: Produce is refused; with the bypass on it is produced and the component goes negative.
3. A Shira Pharma subcontracted receipt (components not sent): validated in both cases; the components go negative at the subcontracting location; a resupply transfer of more than our stock is refused.
4. A PoS sale of an out-of-stock item, then close the session: without the PoS bypass the session closes and the delivery stays open (failed pickings); with it the delivery is done and stock goes negative. Other transfers stay refused with only the PoS bypass on.

## Roll back
Uninstall *Adams Stock No Negative* (Apps). It adds two boolean fields on the company and a settings view, and changes no stored stock data: uninstalling removes the block and the two settings and leaves stock as it is.

## Open items and assumptions
- Concurrent validation by two users is handled by a waiting lock (`FOR NO KEY UPDATE` where a key falls below zero) but has no automated test.
- Code that writes quants directly without a stock operation (no standard flow does) isn't checked.
- Package grain is strict (loose stock doesn't cover a line that takes from a package), as standard reservation does.
- License LGPL-3 and author "Adams", as the other Adams modules (the source was proprietary to its project).
- Standard Odoo 19 recomputes untracked subcontract components from the produced quantity when the receipt is validated; the test checks that recording more is accepted, not the consumed figure.
