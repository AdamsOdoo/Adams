# Native source findings and remaining definition decisions

Inspected Community source: `odoo/odoo@82f4b92eaf3f2014eb1667e4845e80c377dbfb4f`.
These findings do not verify the customer's Enterprise build. No extra business
formula is enabled by this document.

| Requirement | Verified native source | Implementation consequence |
|---|---|---|
| Recent orders/quotations | `sale.order`, `sale.action_orders`, `sale.action_quotations`; order date means draft/sent creation date and confirmed-order confirmation date | Implemented paged native records, descending date/id, selected company and period, native access rules, document-currency untaxed values. Expiration is the stored native date, not a custom quote-validity judgment. |
| Remaining delivery quantity | `sale.report.qty_to_deliver` is native ordered minus delivered quantity normalized to product UoM; `qty_delivered` is separately available | Implemented native product/UoM breakdown and scoped native report action using ordered/delivered/to-deliver measures. Do not invent one mixed-unit total, clamp negative native results, or treat quantities as backlog value. Value/return/service treatment requires approved mapping. |
| Draft/sent quotation value | Native Sales Analysis `price_subtotal:sum`, draft/sent states and native order date | Implemented using native currency conversion, with expired quotations explicitly included while still in these states. This is not a bespoke validity-filtered pipeline. |
| Warehouse dimensions | `sale_stock` extends `sale.report` with `warehouse_id` | Optional extension must be detected before exposing warehouse filters. No hardcoded warehouse names. |
| On-time completion | `sale_stock` sets `sale.order.effective_date` to the **first** completed customer delivery; `delivery_status` describes transfer states | First delivery date does not establish final on-time completion. Need an agreed complete-order/line/transfer denominator, partials/backorders/returns policy, missing commitment policy and completion cutoff before implementing the requested on-time rate. |
| Open-late versus completed-late | Native order commitment and transfer completion/status are available; no exact requested combined KPI verified in inspected sources | Keep unavailable. Inspect the installed build's delivery reports before proposing a custom gap implementation; approve definitions separately. |
| Stock forecast/history | `report.stock.quantity` provides forecast/in/out by date/product/warehouse using a rolling window controlled by `stock.report_stock_quantity_period` (default three months) | Do not interpret arbitrary dashboard dates outside this window as real zero stock. Current product quantity adapter remains explicitly current. Broader history/forecast requires verified native action/options and source range disclosure. |
| Procurement delivery timing | `purchase.report.delay_pass` computes planned receipt date minus order date | Must not be relabeled as actual supplier delivery delay or on-time receipt performance. Current adapter exposes confirmed purchase value only. |
| Report return navigation | `@web/search/action_hook.useSetupAction` exports local state; native action service restores it through component props | Keep only filters/selected dimensions/pages/section expansion/scroll in the action stack. Refresh business data and authorize again on return. Actual breadcrumb/browser behavior still needs deployment testing. |

## Primary references

- [Sales model and date semantics](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/sale/models/sale_order.py)
- [Sales native actions](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/sale/views/sale_order_views.xml)
- [Sales Analysis quantities](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/sale/report/sale_report.py)
- [Delivery state and first-delivery date](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/sale_stock/models/sale_order.py)
- [Warehouse report extension](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/sale_stock/report/sale_report.py)
- [Stock forecast range](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/stock/report/report_stock_quantity.py)
- [Purchase report definitions](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/purchase/report/purchase_report.py)
- [Native action state hook](https://github.com/odoo/odoo/blob/82f4b92eaf3f2014eb1667e4845e80c377dbfb4f/addons/web/static/src/search/action_hook.js)

## Installed Odoo 19 inventory and workforce inspection — 20 September

Accessible primary source at installed Community revision
`7bbce824a1897a912441a7f0511ffec505cbe1d5`:
- [Native stock quantities and actions](https://github.com/odoo/odoo/blob/7bbce824a1897a912441a7f0511ffec505cbe1d5/addons/stock/models/product.py)
- [Native valuation service](https://github.com/odoo/odoo/blob/7bbce824a1897a912441a7f0511ffec505cbe1d5/addons/stock_account/models/product.py)
- [Native stock valuation view](https://github.com/odoo/odoo/blob/7bbce824a1897a912441a7f0511ffec505cbe1d5/addons/stock_account/views/product_views.xml)
- [Inventory at Date contract](https://github.com/odoo/odoo/blob/7bbce824a1897a912441a7f0511ffec505cbe1d5/addons/stock/wizard/stock_quantity_history.py)
- [Employee report and action](https://github.com/odoo/odoo/blob/7bbce824a1897a912441a7f0511ffec505cbe1d5/addons/hr/views/hr_employee_views.xml)

Fact: product `qty_available` supports native historical `to_date`. Current
`free_qty` subtracts present reservations, so the historical dashboard omits it.
Odoo 19 `total_value` delegates standard/average/FIFO and lot valuation to native
services and supports `to_date`; the dashboard does not recreate these formulas.
The native report exposes the same field. Current workforce counts are native
employee aggregates, explicitly not historical headcount. Stock aging, company
warehouse/location selectors, full owner-scope fidelity and historical HR definitions
remain open acceptance work; they are not implied by this bounded implementation.
