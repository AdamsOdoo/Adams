"""Rendered visual and accessibility evidence for the U2 and U3 surfaces.

WHAT THIS IS FOR. The design system makes five things acceptance criteria
rather than aspirations (§12-§14): a recorded contrast table, a keyboard and
visible-focus walkthrough, a reduced-motion check, responsive behaviour at the
named widths, and an RTL smoke check. Wave 5 shipped with all five implemented
*structurally* -- semantic token pairs, logical properties, every transition
behind `prefers-reduced-motion: no-preference` -- and none of them MEASURED.
Reading a stylesheet is not the same as rendering it, and the difference is
exactly where these defects hide.

So this file renders. It drives the real surfaces in a real Chromium through
the DevTools protocol and produces artifacts a reader can check:

  * full-page screenshots at 1366 / 768 / 390 CSS px;
  * the same surfaces under `prefers-reduced-motion: reduce`, with the
    resulting COMPUTED transition and animation durations read back;
  * the same surfaces in a real RTL locale, with the computed `direction` read
    back and the horizontal-overflow check re-run;
  * every actionable control focused, with `:focus-visible` FORCED through
    `CSS.forcePseudoState` so the indicator the stylesheet defines is the one
    measured;
  * a contrast table computed from rendered colours -- resolving transparent
    backgrounds up the ancestor chain and compositing alpha -- against the
    WCAG 2.2 thresholds.

WHY CDP AND NOT A TOUR. A tour asserts DOM structure. It cannot set a
viewport, cannot emulate a media feature, cannot force a pseudo-class, and
cannot take a picture. `:focus-visible` in particular cannot be asserted from a
tour at all: in headless Chromium a script-focused `<button>` never matches it,
because the pseudo-class tracks the last real input modality and a tour has
none. `CSS.forcePseudoState` removes the heuristic from the question entirely.

WHERE THE ARTIFACTS GO, AND WHY NOT INTO THE REPOSITORY BY DEFAULT.
`SC_EVIDENCE_DIR` chooses the output directory; without it, artifacts go to a
temporary directory and are discarded. That default is deliberate and load
bearing: the canonical runner records `connector_worktree_dirty`, and a test
that rewrote committed PNGs on every run would dirty the worktree and destroy
the exact-SHA property of the definitive run. Evidence is captured in a
dedicated run with `SC_EVIDENCE_DIR` pointed at
`docs/05-qa/evidence/wave-5-u2-u3-2026-07-27/`, committed, and thereafter this
test proves the same properties on every run without touching them.

THE ASSERTIONS RUN EITHER WAY. Contrast, reduced motion, focus visibility and
horizontal overflow are asserted whether or not artifacts are being written, so
this is a real test and not a capture script wearing a test's clothes.

NO SHOPIFY. No credential, no request, no mutation. The fixtures are Odoo rows.
"""

import base64
import contextlib
import json
import logging
import os
import pathlib
import tempfile
import time

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import HttpCase, new_test_user
from odoo.tests.common import ChromeBrowser

_logger = logging.getLogger(__name__)

#: The widths the design system names (§10, §14) plus the phone width the
#: correction packet requires.
WIDTHS = {'desktop': 1366, 'tablet': 768, 'mobile': 390}

#: How many cached Shopify locations the fixture seeds. The search page is 50
#: (`SETUP_LOCATION_SEARCH_PAGE`), so this is the smallest set that renders a
#: full page, offers `Load more`, and is then exhausted by one more press.
LOCATION_FIXTURE_ROWS = 60

#: 200% browser zoom, expressed the way a browser expresses it: the CSS
#: viewport halves and every CSS pixel is drawn twice as large. Emulating it
#: with `deviceScaleFactor` alone changes nothing about layout, which is the
#: only thing WCAG 2.2 SC 1.4.4 is about -- text has to remain readable and
#: reachable without a second scroll axis when the page is enlarged, and that
#: is a LAYOUT consequence of the narrower CSS viewport.
ZOOM_FACTOR = 2

#: WCAG 2.2 SC 1.4.10 specifies reflow at 320 CSS px. Halving 390 gives 195,
#: a width no criterion requires and no browser lays out for, so the mobile
#: row is measured at the floor instead of at a number chosen by arithmetic.
REFLOW_FLOOR_PX = 320

#: How far a keyboard user is asked to Tab before the traversal is called
#: unreachable. The longest Batch 1 surface is the location step with a full
#: 50-row page plus the search, select and map controls, and every row there
#: is static text and contributes no tab stop -- so this is generous by a wide
#: margin and a surface that exceeds it has a real focus-order defect rather
#: than a long list.
MAX_TAB_PRESSES = 200

#: The surfaces the Batch 1 correction changed. Named, not derived: a surface
#: joins this campaign because someone decided it should, and a future change
#: that adds one and forgets this tuple should be a visible omission rather
#: than a quietly smaller matrix.
BATCH1_CHANGED_SURFACES = (
    's1-setup-credential-dev-dashboard',
    's1-setup-credential-offline-token',
    's1-setup-location-mapping',
    's1-setup-location-search-results',
    's1-setup-location-loaded-more',
    's1-setup-location-no-result',
    'u2-first-push-form-awaiting-confirmation',
    'u2-first-push-withdraw-dialog',
    'u2-location-mapping-form',
    'u2-location-withdraw-all-dialog',
)

#: The surfaces Batch 2 P0 merchant reachability created. Same rule as above:
#: named, not derived, so adding one and forgetting this tuple is a visible
#: omission rather than a quietly smaller matrix. Every one of them is a
#: surface that DID NOT EXIST before this batch -- which is exactly the
#: category the previous campaign could not have covered.
BATCH2_CHANGED_SURFACES = (
    'b2-store-settings-canonical',
    # ONE store form, and it carries BOTH control groups. They are rendered
    # side by side on the same record, so capturing two stores to photograph
    # them separately would produce two rows measuring the same layout -- and,
    # measured, a second store also breaks the guided-setup captures, because
    # the setup surface auto-selects a store only while there is exactly one.
    'b2-store-form-controls',
    'b2-tax-decision-dialog',
    'b2-product-match-decision-pending',
    'b2-product-match-decision-dialog',
    'b2-product-match-decision-resolved',
)

# NOT in the tuple above, and measured rather than assumed: the Match
# Decisions LIST. The enlargement and keyboard matrices measure a
# CONNECTOR-OWNED surface region and its final actionable control, and a bare
# Odoo list view has neither -- the instrument reports `no connector surface on
# screen` for it, exactly as it does for every other list in the capture set.
# The list is still captured, and is still measured for responsive layout,
# RTL, reduced motion and contrast in the ordinary surface set below; it is
# excluded from these two matrices because they do not apply to it, not
# because it failed them.

#: Every surface the enlargement, keyboard-traversal and live-region campaigns
#: cover. Batch 2 joins Batch 1 rather than replacing it: a surface does not
#: stop needing to reflow because a later batch shipped.
CHANGED_SURFACES = BATCH1_CHANGED_SURFACES + BATCH2_CHANGED_SURFACES

# --- Batch 2 evidence closure (2026-07-31) -----------------------------------
#
# The independent review found the Batch 2 half of this campaign covered on
# paper and hollow in three places, and all three are here rather than in a
# comment: the surfaces that produced no connector-owned clipping measurement
# at all, the surfaces whose RTL row was satisfied by a signal measured
# somewhere else in the run, and the bands whose ARIA role claimed a live
# region that could never change.

#: The connector-owned MARKER each Batch 2 surface must produce a measurement
#: for. Matched against the `markers` the overflow instrument reports for each
#: measured root, not against `cls`: Odoo puts its own class first, so four
#: different screens all report `o_form_sheet_bg` and a matrix keyed on that
#: cannot say which surface a row is about. Named per surface, not derived, so
#: a surface that stops rendering its marker is a failing row rather than a
#: quietly missing one.
BATCH2_SURFACE_ROOTS = {
    'b2-store-settings-canonical': ('o_sc_store_settings',),
    'b2-store-form-controls': ('o_sc_store_form',),
    'b2-tax-decision-dialog': ('o_sc_tax_decision',),
    'b2-product-match-decision-pending': ('o_sc_match_decision',),
    'b2-product-match-decision-dialog': ('o_sc_match_decision_wizard',),
    'b2-product-match-decision-resolved': ('o_sc_match_decision',),
}

#: The selector that proves the INTENDED surface is the one on screen, used
#: while it is visible rather than aggregated over the run. `.o_form_view`
#: is true of every form in the product and proves nothing about which one.
BATCH2_SURFACE_SELECTORS = {
    'b2-store-settings-canonical': '.o_form_view .o_sc_store_settings',
    'b2-store-form-controls': '.o_form_view .o_sc_store_form',
    'b2-tax-decision-dialog':
        '.modal:not(.o_inactive_modal) .o_sc_tax_decision',
    'b2-product-match-decision-pending': '.o_form_view .o_sc_match_decision',
    'b2-product-match-decision-dialog':
        '.modal:not(.o_inactive_modal) .o_sc_match_decision_wizard',
    'b2-product-match-decision-resolved': '.o_form_view .o_sc_match_decision',
}

#: The root the RENDERED region inventory is taken inside, per surface. It is
#: not always the identity selector above: on the two dialogs the marker is
#: declared ON a band (adding a wrapper box would change what the overflow
#: instrument measures -- see `OVERFLOW_JS`), and a band cannot be the scope
#: for an inventory that has to include that band's siblings. `:has()` keeps
#: the scope surface-specific rather than "whatever dialog is open".
BATCH2_LIVE_REGION_ROOTS = {
    'b2-store-settings-canonical': '.o_sc_store_settings',
    'b2-store-form-controls': '.o_sc_store_form',
    'b2-tax-decision-dialog':
        '.modal:not(.o_inactive_modal) .o_form_view:has(.o_sc_tax_decision)',
    'b2-product-match-decision-pending': '.o_sc_match_decision',
    'b2-product-match-decision-dialog':
        '.modal:not(.o_inactive_modal) '
        '.o_form_view:has(.o_sc_match_decision_wizard)',
    'b2-product-match-decision-resolved': '.o_sc_match_decision',
}

#: WAI-ARIA 1.2 §5.3.2: the live-region roles, in full. `note` is deliberately
#: not among them, which is the whole of the semantic ruling below.
ARIA_LIVE_REGION_ROLES = ('alert', 'log', 'marquee', 'status', 'timer')

#: The view whose arch each Batch 2 surface is rendered from, as
#: (model, xmlid). The rendered inventory can only see what the fixture put on
#: screen -- an inactive notebook page, or a band whose `invisible` is false
#: for this record, is simply not in the DOM. The ARCH is the complete
#: declaration, inherited views included, so it is read as well and the two
#: halves are asserted against each other.
BATCH2_SURFACE_VIEWS = {
    'b2-store-settings-canonical': (
        'shopify.connector.store.settings',
        'shopify_connector_core.'
        'view_shopify_connector_store_settings_canonical_form',
    ),
    'b2-store-form-controls': (
        'shopify.connector.store',
        'shopify_connector_core.view_shopify_connector_store_form',
    ),
    'b2-tax-decision-dialog': (
        'shopify.connector.tax.decision.wizard',
        'shopify_connector_sale.view_shopify_connector_tax_decision_wizard_form',
    ),
    'b2-product-match-decision-pending': (
        'shopify.connector.product.match.decision',
        'shopify_connector_product.'
        'view_shopify_connector_product_match_decision_form',
    ),
    'b2-product-match-decision-dialog': (
        'shopify.connector.product.match.decision.wizard',
        'shopify_connector_product.'
        'view_shopify_connector_product_match_decision_wizard_form',
    ),
    'b2-product-match-decision-resolved': (
        'shopify.connector.product.match.decision',
        'shopify_connector_product.'
        'view_shopify_connector_product_match_decision_form',
    ),
}

#: THE FOUR BANDS THIS CORRECTION RE-RULED, pinned by a fragment of the
#: sentence each one actually says. Each was `role="status"` -- a polite live
#: region -- on content that is already on screen when the dialog or the record
#: surface receives focus and that no interaction with that surface can change.
#: Pinning the text as well as the role means a future edit that keeps the role
#: and rewrites the band, or keeps the band and restores the role, fails here.
BATCH2_STATIC_NOTE_BANDS = (
    ('b2-tax-decision-dialog',
     'This order stopped because Shopify charged a tax'),
    ('b2-product-match-decision-dialog',
     'This import stopped because more than one Odoo'),
    ('b2-product-match-decision-pending',
     'This import is waiting for a decision.'),
    ('b2-product-match-decision-pending',
     'Superseded.'),
)

#: Live regions RETAINED on a Batch 2 surface, adjudicated one by one. Each
#: entry is (surface, role, a fragment of what it says, why it is a live
#: region). The list is asserted for EQUALITY against what the arch declares,
#: so a band that gains `role="status"` in any of these views fails until
#: somebody rules on it -- and an entry that stops matching anything fails too,
#: so this cannot rot into a list of things that used to be true.
#:
#: It is empty, and that IS the ruling: no connector-owned band on any of the
#: six Batch 2 surfaces announces a change, because none of them has a change
#: to announce. Refusals on these surfaces are announced by Odoo's own
#: notification, which is `role="alert" aria-live="assertive"` and names the
#: field it refused -- measured by `test_batch2_live_regions_are_truthful`
#: rather than assumed.
BATCH2_RETAINED_LIVE_REGIONS = ()

#: Live regions on a Batch 2 surface that are declared by a module OUTSIDE
#: this correction's allowed files, adjudicated and left exactly as they are.
#: They are recorded here so the equality assertion above stays honest about
#: what is on these surfaces without this session editing another batch's
#: production view.
BATCH2_FOREIGN_LIVE_REGIONS = (
    ('b2-store-form-controls', 'alert',
     "This store's API health is degraded.",
     'S25 (shopify_connector_product_export) standing-condition banner. It is '
     'not an instruction: it is rendered only while `api_health_state` is '
     '`degraded`, it names a live system condition, and `alert` is the role '
     'its own view records as deliberate. It is NOT rendered in this '
     "campaign's fixture, which holds a healthy connected store, and the "
     'rendered half asserts that. Out of this correction\'s allowed files; '
     'adjudicated, not edited.'),
    ('b2-store-form-controls', 'alert',
     'This store is not connected.',
     'S25 (shopify_connector_product_export) standing-condition banner, same '
     'ruling as above; rendered only while the store is not `connected`, and '
     'not rendered in this fixture.'),
)

#: WCAG 2.2 thresholds. SC 1.4.3 for text, SC 1.4.11 for components.
CONTRAST_TEXT = 4.5
CONTRAST_LARGE_TEXT = 3.0
CONTRAST_NON_TEXT = 3.0

# --- In-page instruments -----------------------------------------------------
# Colour maths runs in the page because that is the only place the RENDERED
# values exist. Everything below returns JSON to Python, which does the
# asserting.

CONTRAST_JS = r"""
(() => {
  const parse = (c) => {
    const m = c && c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[,\s/]+/).filter(Boolean).map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  // Composite a possibly-transparent colour over its ancestors, then over
  // white -- the page's own base. A ratio computed against `rgba(0,0,0,0)`
  // is meaningless, and that is the usual way a contrast table lies.
  const effectiveBg = (el) => {
    let node = el, acc = null;
    while (node && node.nodeType === 1) {
      const c = parse(getComputedStyle(node).backgroundColor);
      if (c && c.a > 0) {
        acc = acc === null ? c : over(acc, c);
        if (acc.a >= 0.999) return acc;
      }
      node = node.parentElement;
    }
    const white = { r: 255, g: 255, b: 255, a: 1 };
    return acc === null ? white : over(acc, white);
  };
  const over = (fg, bg) => ({
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
    a: 1,
  });
  const lum = (c) => {
    const ch = [c.r, c.g, c.b].map((v) => {
      const s = v / 255;
      return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
  };
  const ratio = (a, b) => {
    const l1 = lum(a), l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  };
  const fmt = (c) =>
    "#" + [c.r, c.g, c.b].map((v) =>
      Math.round(v).toString(16).padStart(2, "0")).join("");

  const visible = (el) => {
    const s = getComputedStyle(el);
    if (s.visibility === "hidden" || s.display === "none" || s.opacity === "0")
      return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };

  const results = [];
  const seen = new Set();
  // Only the connector's own surfaces. Measuring the whole Odoo chrome would
  // report defects this repository neither owns nor can fix.
  const roots = document.querySelectorAll(
    ".o_sc_dashboard, .o_sc_export_diff, .o_sc_setup, .o_form_view, .o_list_view, .modal-content"
  );
  for (const root of roots) {
    for (const el of root.querySelectorAll("*")) {
      if (!visible(el)) continue;
      const text = Array.from(el.childNodes)
        .filter((n) => n.nodeType === 3)
        .map((n) => n.textContent.trim())
        .join(" ")
        .trim();
      if (!text) continue;
      const s = getComputedStyle(el);
      const fg = parse(s.color);
      if (!fg) continue;
      const bg = effectiveBg(el);
      const px = parseFloat(s.fontSize);
      const bold = parseInt(s.fontWeight, 10) >= 700;
      // SC 1.4.3 "large text": >= 18.66px bold, or >= 24px.
      const large = px >= 24 || (bold && px >= 18.66);
      const key = [el.className, s.color, fmt(bg), px, large].join("|");
      if (seen.has(key)) continue;
      seen.add(key);
      results.push({
        kind: "text",
        selector: el.tagName.toLowerCase() +
          (typeof el.className === "string" && el.className
            ? "." + el.className.trim().split(/\s+/).slice(0, 3).join(".")
            : ""),
        sample: text.slice(0, 60),
        foreground: fmt(over(fg, bg)),
        background: fmt(bg),
        font_px: Math.round(px * 100) / 100,
        bold,
        large,
        required: large ? 3.0 : 4.5,
        ratio: Math.round(ratio(over(fg, bg), bg) * 100) / 100,
      });
    }
    // SC 1.4.11: the BOUNDARY of an actionable control against what is
    // behind it. A control whose edge cannot be seen is not perceivable.
    for (const el of root.querySelectorAll(
      "button, .btn, input, select, textarea, a.o_form_uri"
    )) {
      if (!visible(el)) continue;
      const s = getComputedStyle(el);
      const width = parseFloat(s.borderTopWidth) || 0;
      const own = parse(s.backgroundColor);
      const behind = effectiveBg(el.parentElement || el);
      let fgColor, what;
      if (width > 0) {
        fgColor = over(parse(s.borderTopColor), behind);
        what = "border";
      } else if (own && own.a > 0.05) {
        fgColor = over(own, behind);
        what = "fill";
      } else {
        continue;  // no boundary drawn: nothing to measure
      }
      const key = ["nt", el.className, what].join("|");
      if (seen.has(key)) continue;
      seen.add(key);
      results.push({
        kind: "non_text",
        selector: el.tagName.toLowerCase() +
          (typeof el.className === "string" && el.className
            ? "." + el.className.trim().split(/\s+/).slice(0, 3).join(".")
            : ""),
        sample: what,
        foreground: fmt(fgColor),
        background: fmt(behind),
        font_px: null,
        bold: false,
        large: false,
        required: 3.0,
        ratio: Math.round(ratio(fgColor, behind) * 100) / 100,
      });
    }
  }
  return JSON.stringify(results);
})()
"""

MOTION_JS = r"""
(() => {
  const out = [];
  const roots = document.querySelectorAll(
    ".o_sc_dashboard, .o_sc_export_diff, .o_sc_setup, .o_form_view, .o_list_view"
  );
  for (const root of roots) {
    for (const el of [root, ...root.querySelectorAll("*")]) {
      const s = getComputedStyle(el);
      const dur = (v) => (v || "0s").split(",")
        .map((x) => parseFloat(x) * (x.includes("ms") ? 0.001 : 1))
        .reduce((a, b) => Math.max(a, b || 0), 0);
      const t = dur(s.transitionDuration), a = dur(s.animationDuration);
      // NOT `> 0`. The conventional reduced-motion override -- Odoo's own
      // included -- is `0.001ms !important` rather than `0s`, so that
      // `transitionend` still fires and JS waiting on it does not hang.
      // That computes to 1e-6s, which is not motion by any definition; the
      // threshold is 10ms, an order of magnitude below the design system's
      // shortest sanctioned duration (100ms).
      if (t > 0.01 || a > 0.01) {
        out.push({
          selector: el.tagName.toLowerCase() +
            (typeof el.className === "string" && el.className
              ? "." + el.className.trim().split(/\s+/).slice(0, 3).join(".")
              : ""),
          transition_s: t,
          animation_s: a,
        });
      }
    }
  }
  return JSON.stringify({
    reduced_motion_matches:
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    moving: out,
  });
})()
"""

#: The S7 Owl diff is a client action opened by the preview form's
#: "Review Export" button. `:contains()` is a hoot-dom extension and not valid
#: CSS, so the button is found by its text the ordinary way.
REVIEW_EXPORT_JS = r"""
(() => {
  const btn = Array.from(document.querySelectorAll(".o_form_view button"))
    .find((b) => b.textContent.trim().includes("Review Export"));
  if (!btn) {
    throw new Error("no 'Review Export' control on the preview form");
  }
  btn.click();
  return true;
})()
"""

# --- Batch 1 UI completion: driving the surfaces the correction changed ------
#
# Four of the surfaces this campaign must measure do not exist until an
# operator DOES something: a location search result set, a set with a second
# page loaded, a search that matched nothing, and each of the two withdrawal
# dialogs. Photographing the step they live on and calling that coverage is
# the same mistake the tour made -- it measures the screen before the thing
# under test is on it.
#
# These run as the surface's post-open action. Each waits for its own
# completion rather than for a fixed delay, and each FAILS LOUDLY if what it
# was driving is not there, because a post-open action that silently did
# nothing leaves the previous screen to be photographed under the new name.

#: Shared preamble: a real `input` event so Owl's `t-model` sees the value
#: (assigning `.value` alone does not), and a condition waiter.
_DRIVE_PRELUDE = r"""
  const type = (selector, value) => {
    const el = document.querySelector(selector);
    if (!el) { throw new Error("no element matched " + selector); }
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype, "value").set;
    setter.call(el, value);
    el.dispatchEvent(new Event("input", {bubbles: true}));
    return el;
  };
  const press = (selector) => {
    const el = document.querySelector(selector);
    if (!el) { throw new Error("no control matched " + selector); }
    if (el.disabled) { throw new Error(selector + " is disabled"); }
    el.click();
    return el;
  };
  const waitFor = async (label, predicate, ms = 30000) => {
    const deadline = Date.now() + ms;
    while (Date.now() < deadline) {
      if (predicate()) {
        await new Promise((r) => requestAnimationFrame(
          () => requestAnimationFrame(r)));
        return true;
      }
      await new Promise((r) => setTimeout(r, 50));
    }
    throw new Error("timed out waiting for " + label);
  };
  const rows = () => document.querySelectorAll(".sc_setup__location").length;
"""

#: A search with results on screen: the Clear control appears only once a
#: search has actually been run, so it is the honest completion signal.
LOCATION_SEARCH_JS = r"""
(async () => {
%s
  type(".sc_setup_search_shopify", "warehouse 1");
  press(".sc_setup_search_shopify_go");
  await waitFor("a search result set",
                () => document.querySelector(".sc_setup_search_shopify_clear")
                      && rows() > 0);
  return true;
})()
""" % _DRIVE_PRELUDE

#: A full first page plus a second one, which is the state the accumulated-page
#: rework exists for and the only one where the counter, the Load more control
#: and a long list are all on screen together.
LOCATION_LOAD_MORE_JS = r"""
(async () => {
%s
  type(".sc_setup_search_shopify", "");
  press(".sc_setup_search_shopify_go");
  // BOTH controls, and the pair is the point: `Clear` appears only once a
  // search has resolved and `Load more` only when the SERVER says another
  // page exists. Counting rows instead raced the response -- the unsearched
  // list already renders every seeded row, so a count taken before the first
  // page landed was HIGHER than the page that replaced it and "more rows than
  // before" could never become true.
  await waitFor("a resolved first page with another page behind it",
                () => document.querySelector(".sc_setup_search_shopify_clear")
                      && document.querySelector(".sc_setup_more_shopify"));
  const first = rows();
  press(".sc_setup_more_shopify");
  await waitFor("a second page", () => rows() > first);
  return true;
})()
""" % _DRIVE_PRELUDE

#: The zero-result state, which used to hide the search row, the Clear button
#: and the Map control together -- so the screen that has to keep its way out
#: is exactly the screen worth photographing.
LOCATION_NO_RESULT_JS = r"""
(async () => {
%s
  type(".sc_setup_search_shopify", "zzzz-no-location-matches-this-zzzz");
  press(".sc_setup_search_shopify_go");
  await waitFor("the empty-result band",
                () => document.querySelector(".sc_setup__empty--shopify")
                      && rows() === 0);
  return true;
})()
""" % _DRIVE_PRELUDE

#: The credential step with the offline path selected, so BOTH paths of the
#: chooser are measured rather than only the default one.
CREDENTIAL_OFFLINE_JS = r"""
(async () => {
%s
  const radio = document.querySelector(
    ".sc_setup__modes input[value='offline_access_token']");
  if (!radio) { throw new Error("no offline path on the credential chooser"); }
  radio.click();
  await waitFor("the offline credential field",
                () => document.querySelector(".sc_setup_token"));
  return true;
})()
""" % _DRIVE_PRELUDE


#: The LAST actionable control inside the connector surface on screen, and
#: whether it can actually be got to. "Reachable" is asserted after scrolling
#: it into view, because content below the fold is fine and content that
#: cannot be scrolled to is not -- and the two look identical from a
#: bounding rectangle alone.
LAST_CONTROL_JS = r"""
(() => {
  // PRIORITY ORDER, not a comma list. `document.querySelector("a, b")`
  // returns the first match in DOCUMENT ORDER of either selector, so with a
  // dialog open it returned the form BEHIND the modal -- and the "last
  // actionable control" was then an inert control the modal had made
  // unreachable, which no amount of tabbing could ever land on.
  const surfaceRoot = () => {
    for (const selector of [
      // `.modal-content`, not `.modal-body`: a dialog's FINAL actionable
      // controls are its footer buttons, and the body excludes them, so a
      // body-scoped search called the consequence checkbox the last control
      // and never measured whether Confirm and Cancel could be reached.
      ".modal:not(.o_inactive_modal) .modal-content",
      ".o_sc_setup", ".o_sc_dashboard", ".o_sc_export_diff", ".o_form_view",
    ]) {
      const found = document.querySelector(selector);
      if (found) { return found; }
    }
    return null;
  };
  const root = surfaceRoot();
  if (!root) { return JSON.stringify({error: "no connector surface on screen"}); }
  const name = (el) => {
    const cls = String(el.className || "").split(/\s+/).filter(Boolean)[0];
    return el.tagName.toLowerCase() + (cls ? "." + cls : "") +
           (el.name ? "[name='" + el.name + "']" : "");
  };
  const controls = Array.from(root.querySelectorAll(
    "button, a[href], input, select, textarea, [tabindex]:not([tabindex='-1'])"
  )).filter((el) => {
    if (el.disabled) { return false; }
    if (!el.getClientRects().length) { return false; }
    const cs = getComputedStyle(el);
    return cs.visibility !== "hidden" && cs.display !== "none";
  });
  if (!controls.length) {
    return JSON.stringify({error: "no actionable control on this surface"});
  }
  const last = controls[controls.length - 1];
  last.scrollIntoView({block: "nearest", inline: "nearest"});
  const r = last.getBoundingClientRect();
  return JSON.stringify({
    selector: name(last),
    label: (last.textContent || last.value || "").trim().slice(0, 60),
    control_count: controls.length,
    rect: {top: r.top, right: r.right, bottom: r.bottom, left: r.left},
    viewport: {width: window.innerWidth, height: window.innerHeight},
    // 1px of tolerance throughout: sub-pixel layout rounding is not
    // unreachability.
    reachable: r.bottom <= window.innerHeight + 1 && r.top >= -1 &&
               r.right <= window.innerWidth + 1 && r.left >= -1,
  });
})()
"""

#: Where focus actually is, after a real Tab press.
ACTIVE_ELEMENT_JS = r"""
(() => {
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) {
    return JSON.stringify({is_body: true, selector: "body", visible: false,
                           matches_target: false});
  }
  const name = (node) => {
    const cls = String(node.className || "").split(/\s+/).filter(Boolean)[0];
    return node.tagName.toLowerCase() + (cls ? "." + cls : "") +
           (node.name ? "[name='" + node.name + "']" : "");
  };
  // See LAST_CONTROL_JS: priority order, never a comma list, or with a
  // dialog open this resolves to the form behind the modal.
  const surfaceRoot = () => {
    for (const selector of [
      // `.modal-content`, not `.modal-body`: a dialog's FINAL actionable
      // controls are its footer buttons, and the body excludes them, so a
      // body-scoped search called the consequence checkbox the last control
      // and never measured whether Confirm and Cancel could be reached.
      ".modal:not(.o_inactive_modal) .modal-content",
      ".o_sc_setup", ".o_sc_dashboard", ".o_sc_export_diff", ".o_form_view",
    ]) {
      const found = document.querySelector(selector);
      if (found) { return found; }
    }
    return null;
  };
  const root = surfaceRoot();
  let target = null;
  if (root) {
    const controls = Array.from(root.querySelectorAll(
      "button, a[href], input, select, textarea, [tabindex]:not([tabindex='-1'])"
    )).filter((node) => {
      if (node.disabled) { return false; }
      if (!node.getClientRects().length) { return false; }
      const cs = getComputedStyle(node);
      return cs.visibility !== "hidden" && cs.display !== "none";
    });
    target = controls[controls.length - 1] || null;
  }
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  return JSON.stringify({
    is_body: false,
    selector: name(el),
    // Focus landing on something the user cannot see is SC 2.4.11's failure
    // and it is completely silent, so it is measured rather than assumed.
    visible: r.width > 0 && r.height > 0 && cs.visibility !== "hidden" &&
             cs.display !== "none" && parseFloat(cs.opacity || "1") > 0.01,
    matches_target: target !== null && el === target,
  });
})()
"""

#: Every ARIA live region and every alert band inside one surface, with the
#: text each one would announce. `%s` is the surface's root selector.
LIVE_REGION_JS = r"""
(() => {
  const root = document.querySelector(%s);
  if (!root) { return JSON.stringify({error: "surface not on screen"}); }
  const text = (el) => (el.textContent || "").replace(/\s+/g, " ").trim();
  const LIVE_ROLES = ["alert", "log", "marquee", "status", "timer"];
  const regions = Array.from(
    root.querySelectorAll("[role], [aria-live]")
  ).map((el) => {
    const r = el.getBoundingClientRect();
    return {
      role: el.getAttribute("role"),
      aria_live: el.getAttribute("aria-live"),
      is_live_region: LIVE_ROLES.includes(el.getAttribute("role")) ||
                      Boolean(el.getAttribute("aria-live")),
      cls: String(el.className || "").split(/\s+/)[0],
      // A band nobody can see is not readable, and "the note is static" is
      // worth nothing if the note was not on screen (Batch 2 closure).
      visible: r.width > 0 && r.height > 0 &&
               getComputedStyle(el).visibility !== "hidden" &&
               getComputedStyle(el).display !== "none",
      text: text(el).slice(0, 400),
    };
  });
  // An `alert-*` band with no role at all: styled to look urgent and
  // carrying nothing that tells a screen reader to read it.
  const rolelessAlerts = Array.from(
    root.querySelectorAll("[class*='alert-']")
  ).filter((el) => !el.getAttribute("role") &&
                   !String(el.className).includes("alert-link"))
   .map((el) => ({cls: String(el.className), text: text(el).slice(0, 200)}));
  return JSON.stringify({regions: regions, roleless_alerts: rolelessAlerts});
})()
"""

#: Is the INTENDED surface on screen, and can it be seen? `%s` is the
#: surface-specific selector. Batch 2 evidence closure (2026-07-31): an RTL row
#: recorded against `.o_form_view` says a form was rendered, not WHICH form,
#: and a row that names a surface has to be able to show that surface was the
#: one measured.
SURFACE_PRESENT_JS = r"""
(() => {
  const nodes = Array.from(document.querySelectorAll(%s));
  const visible = nodes.filter((el) => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" &&
           cs.display !== "none";
  });
  return JSON.stringify({
    matched: nodes.length,
    visible: visible.length,
    rects: visible.slice(0, 4).map((el) => {
      const r = el.getBoundingClientRect();
      return {width: Math.round(r.width), height: Math.round(r.height)};
    }),
  });
})()
"""

#: Fill in the open dialog's mandatory reason, so the `note` band can be
#: compared before and after the operator has actually done something.
TYPE_REASON_JS = r"""
(async () => {
  const dialog = document.querySelector(".modal:not(.o_inactive_modal)");
  if (!dialog) { throw new Error("no dialog on screen"); }
  const input = dialog.querySelector(
    ".o_field_widget[name='reason'] input, .o_field_widget[name='reason'] textarea");
  if (!input) { throw new Error("the dialog has no reason field"); }
  const proto = input.tagName === "TEXTAREA"
    ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, "value").set.call(
    input, "Announced-state evidence run");
  input.dispatchEvent(new Event("input", {bubbles: true}));
  await new Promise((r) => requestAnimationFrame(
    () => requestAnimationFrame(r)));
  return true;
})()
"""

#: Submit the open dialog with its mandatory field empty, then report how the
#: refusal was communicated.
INVALID_SUBMIT_JS = r"""
(async () => {
  const waitFor = async (label, predicate, ms = 20000) => {
    const deadline = Date.now() + ms;
    while (Date.now() < deadline) {
      if (predicate()) {
        await new Promise((r) => requestAnimationFrame(
          () => requestAnimationFrame(r)));
        return true;
      }
      await new Promise((r) => setTimeout(r, 50));
    }
    return false;
  };
  const dialog = document.querySelector(".modal:not(.o_inactive_modal)");
  if (!dialog) { return JSON.stringify({error: "no dialog on screen"}); }
  const confirm = dialog.querySelector("footer button[name='action_confirm']");
  if (!confirm) { return JSON.stringify({error: "no confirm control"}); }
  confirm.click();
  const invalidShown = await waitFor(
    "an invalid field",
    () => document.querySelector(".o_field_invalid, [aria-invalid='true']"));
  const text = (el) => (el.textContent || "").replace(/\s+/g, " ").trim();
  const fields = Array.from(document.querySelectorAll(
    ".o_field_invalid, [aria-invalid='true']"
  )).map((el) => {
    const widget = el.closest("[name]") || el;
    const control = el.matches("input, select, textarea")
      ? el : el.querySelector("input, select, textarea");
    return {
      field: widget.getAttribute("name"),
      cls: String(el.className || "").split(/\s+/)[0],
      // Odoo marks the CONTROL, so look there as well as at the wrapper --
      // `aria-invalid` on neither is the finding.
      aria_invalid: el.getAttribute("aria-invalid") === "true" ||
                    Boolean(control && control.getAttribute("aria-invalid") === "true"),
    };
  });
  // Anything that would be READ OUT: Odoo's notification manager, or any
  // live region that appeared with the refusal in it.
  const announced = Array.from(document.querySelectorAll(
    "[role='alert'], [role='status'], [aria-live]"
  )).map((el) => ({
    role: el.getAttribute("role"),
    aria_live: el.getAttribute("aria-live"),
    cls: String(el.className || "").split(/\s+/)[0],
    text: text(el).slice(0, 300),
  })).filter((r) => r.text);
  return JSON.stringify({
    invalid_shown: invalidShown,
    invalid_fields: fields,
    announced: announced,
  });
})()
"""


def _open_dialog_js(label):
    """Press a header control by its visible label and wait for its dialog.

    An XML `type="action"` button renders its `name` as the RESOLVED numeric
    action id, so there is no stable attribute to select on; the label is what
    an operator reads and what the tours already target.
    """
    return r"""
(async () => {
%s
  const labelled = () => Array.from(
    document.querySelectorAll(".o_form_view button, .o-dropdown--menu button")
  ).find((b) => b.textContent.includes(%s));
  let btn = labelled();
  if (!btn) {
    // NOT a connector defect, and not something to route around silently.
    // Odoo's own `web.StatusBarButtons` keeps the FIRST header control
    // inline on a small screen and folds the rest into a "More" dropdown
    // (`env.isSmall`), so at 390px the withdrawal control is behind that
    // menu. A driver that only looked for the button would report the
    // control missing on mobile, which would be a false finding; one that
    // skipped the surface on mobile would report nothing at all. It is
    // opened, the way an operator opens it, and then measured.
    const more = document.querySelector(
      ".o_form_view .o_statusbar_buttons .dropdown-toggle, " +
      ".o_form_view .o_statusbar_buttons button[title='More']");
    if (more) {
      more.click();
      await waitFor("the collapsed header menu", () => Boolean(labelled()));
      btn = labelled();
    }
  }
  if (!btn) {
    throw new Error("no control labelled " + %s + " on this form");
  }
  btn.click();
  await waitFor("the dialog",
                () => document.querySelector(
                  ".modal:not(.o_inactive_modal) .o_form_view"));
  return true;
})()
""" % (_DRIVE_PRELUDE, json.dumps(label), json.dumps(label))

def _toggle_boolean_js(selector):
    """Flip one boolean field, the way an operator flips it.

    Batch 2 evidence closure (2026-07-31). "The note band is static" is only
    worth asserting against a REAL production state change on the same visible
    surface, and the canonical Store Settings form is a record form whose
    changes are field edits. A click on the checkbox is that change: Odoo
    records it on the model and marks the form dirty, which is waited for
    rather than assumed -- a click that landed on nothing would otherwise
    leave the comparison measuring the same screen twice and passing.
    """
    return r"""
(async () => {
%s
  const box = document.querySelector(%s);
  if (!box) { throw new Error("no boolean control matched " + %s); }
  if (box.disabled) { throw new Error(%s + " is disabled"); }
  box.click();
  await waitFor("the form to record the edit",
                () => document.querySelector(".o_form_dirty"));
  return true;
})()
""" % (_DRIVE_PRELUDE, json.dumps(selector), json.dumps(selector),
       json.dumps(selector))


OVERFLOW_JS = r"""
(() => {
  // WHERE "DIRECTION" HAS TO BE READ, AND WHY NOT ON <html>.
  //
  // Odoo 19's BACKEND never sets `dir` on `<html>` or `<body>`. Measured under
  // a real `ar_001` session with both rtlcss bundles served and `.o_rtl`
  // present on the main components container: `documentElement` and `body`
  // both compute `direction: ltr`. Odoo's backend RTL mechanism is rtlcss --
  // it flips PHYSICAL properties inside the CSS bundle -- and it does not need
  // `direction` to do that.
  //
  // The connector's own stylesheets are written entirely in LOGICAL
  // properties, which have nothing for rtlcss to flip and instead resolve
  // against `direction`. So the meaningful measurement is the direction of the
  // CONNECTOR SURFACE ROOT, which the components now bind to the user's
  // locale. Asserting on `documentElement` would be asserting against Odoo's
  // design, and would fail forever for a reason this repository cannot fix.
  //
  // BATCH 2 EVIDENCE CLOSURE (2026-07-31). `OWL_ROOT_SELECTOR` stays exactly
  // what it was: the three surfaces the connector renders with its OWN
  // stylesheet, whose logical properties resolve against `direction` and which
  // therefore bind it. The Batch 2 surfaces are ordinary Odoo form views whose
  // arch the connector owns and whose CHROME it does not -- Odoo mirrors those
  // through its rtlcss bundle and never touches `direction` -- so promoting
  // them into this probe would assert a property no layer of this repository
  // sets. They are measured for direction all the same, reported separately in
  // `connector_roots`, and the RTL test asserts the signal that actually
  // carries RTL for each surface rather than the one that reads best.
  const OWL_ROOT_SELECTOR = ".o_sc_dashboard, .o_sc_export_diff, .o_sc_setup";
  const root = document.querySelector(OWL_ROOT_SELECTOR);

  // TD-016. WHY THE DOCUMENT TOTAL IS NOT ENOUGH.
  //
  // The original instrument compared `documentElement.scrollWidth` against
  // `innerWidth` and nothing else. That measures ONE thing: whether the page
  // body scrolls sideways. It is a real rule (§10) and worth keeping, but it
  // is structurally incapable of failing for a connector-owned defect,
  // because every Odoo backend surface sits inside `.o_content`, which is
  // `overflow: auto`. A connector panel 300px too wide is clipped or scrolled
  // by that ancestor and contributes exactly nothing to the document total.
  // So the check could only ever fail for something Odoo itself did.
  //
  // What actually needs measuring is each connector-owned surface against
  // the box it is rendered into, plus whether any of its descendants are
  // pushed outside the region a user can see or reach.
  // Every connector-owned surface root, and the inner element each one
  // actually lays its content out in. Both are measured: the root is what
  // the ancestor clips, the inner is where the content that could overflow
  // lives. `[class^="o_sc_"]` would be tempting but would also match future
  // utility classes; this list is exact and
  // `test_the_overflow_instrument_covers_every_connector_surface` fails if
  // a new `o_sc_*` root appears without being added to it.
  const SURFACE_SELECTOR = [
    ".o_sc_dashboard", ".o_sc_dashboard__inner",
    ".o_sc_export_diff", ".o_sc_export_diff__inner",
    // S1 (2026-07-27): the guided setup surface. Its non-root elements use
    // the `sc_` prefix precisely so this list stays the inventory of
    // MEASURED ROOTS rather than a list of every class in the connector.
    ".o_sc_setup", ".o_sc_setup__inner",
    // BATCH 1 UI COMPLETION (2026-07-30). The two withdrawal wizards are
    // connector-owned CONTENT rendered inside Odoo's dialog chrome, and they
    // carry the longest consequence copy in the module plus a `<field>` on
    // its own line inside a sentence -- the two shapes that overflow a
    // 390px dialog. The chrome is Odoo's and is not the connector's to fix;
    // the arch inside it is, so the modal BODY is what is measured. Nothing
    // else opens a dialog in this campaign, so every measurement here is of
    // a connector wizard.
    ".modal:not(.o_inactive_modal) .modal-body",
    ".modal:not(.o_inactive_modal) .modal-body .o_form_view",
    // BATCH 2 EVIDENCE CLOSURE (2026-07-31). Four of the six Batch 2 surfaces
    // produced NO connector-owned measurement at all, at any width, in either
    // direction, while the campaign counted them as covered: the canonical
    // Store Settings form, the store form carrying both import control
    // groups, and the pending and resolved match-decision record surfaces are
    // ordinary Odoo form views, and nothing above matched them. The two that
    // did match matched only through `.modal-body`, which is Odoo's chrome
    // and is the same string for every dialog -- so the tax decision and the
    // product match decision were indistinguishable in the matrix, and any
    // dialog at all would have satisfied either row.
    //
    // These marker classes are declared in the connector's own view arch,
    // carry no styling anywhere, and exist only to identify a surface.
    // `test_the_overflow_instrument_covers_every_connector_surface` reads
    // them out of `views/` and `wizards/` as well as `static/src/`, so a
    // future surface that declares one and forgets this instrument fails
    // rather than going unmeasured.
    //
    // The three RECORD-form markers are listed here because a `class` on
    // `<sheet>` lands on Odoo's `.o_form_sheet_bg`, which is the box the
    // form's content is actually laid out in and already behaves like the
    // measured roots above.
    //
    // The two DIALOG markers are deliberately NOT listed, and the reason is
    // measured rather than assumed. A wizard form has no `<sheet>`, so the
    // only way to mark the dialog body AS A BOX was to interpose a plain
    // block `<div>` -- and `<group>` compiles to a Bootstrap `.row`, whose
    // negative gutter margins put its children 8px outside any intermediate
    // block box on each side. Measured, that div reported a 16px
    // `unhandled_self_overflow` at every width on content that is not
    // clipped and never was: the form's own horizontal padding absorbs the
    // gutters, exactly as before. Rather than add a box and then argue its
    // measurement away, the dialog markers are declared on a band that is
    // already there, no element is added to either dialog, and the roots
    // Batch 1 measured -- the modal BODY and the wizard's own form root --
    // are kept. `markers` below attributes each measured root to the surface
    // that owns it, which is what the per-surface matrix actually needs.
    ".o_sc_store_settings",
    ".o_sc_store_form",
    ".o_sc_match_decision",
  ].join(", ");

  //: Every connector-owned root, marked or Owl, that is actually on screen.
  const CONNECTOR_ROOT_SELECTOR = [
    OWL_ROOT_SELECTOR,
    ".o_sc_store_settings", ".o_sc_store_form", ".o_sc_match_decision",
    ".o_sc_tax_decision", ".o_sc_match_decision_wizard",
  ].join(", ");

  const box = (el) => {
    const r = el.getBoundingClientRect();
    return {top: r.top, right: r.right, bottom: r.bottom, left: r.left,
            width: r.width, height: r.height};
  };

  // The nearest ancestor that CONSTRAINS this element horizontally, and
  // what it does about the overflow. The distinction is the whole point:
  //
  //   `auto` / `scroll` — the overflow is REACHABLE. §10 names this as the
  //       design system's answer to wide content ("wide content must scroll
  //       inside its own `overflow-x: auto` container"), so a table row
  //       extending past its own scroll container is the rule working, not
  //       a defect.
  //
  //   `hidden` / `clip` — the overflow is GONE, silently, with no scrollbar
  //       for anyone to notice. That is the defect this instrument exists
  //       to find.
  //
  // Walked from the element itself, not from the surface root. Measuring a
  // descendant against the SURFACE's clipper skips any scroll container
  // between them and reports every legitimately-scrolling table as broken.
  const constrainer = (el, stopAt) => {
    for (let p = el.parentElement; p; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (/auto|scroll/.test(cs.overflowX)) {
        return {node: p, scrolls: true};
      }
      if (/hidden|clip/.test(cs.overflowX)) {
        return {node: p, scrolls: false};
      }
      if (p === stopAt) break;
    }
    return null;
  };

  const name = (el) =>
    (el.className ? String(el.className).split(/\s+/)[0] : "") || el.tagName;

  const surfaces = [];
  for (const el of document.querySelectorAll(SURFACE_SELECTOR)) {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    const cs = getComputedStyle(el);
    const scrollable = /auto|scroll/.test(cs.overflowX);
    const self_overflow = el.scrollWidth - el.clientWidth;
    const own = constrainer(el, null);

    // Descendants clipped away by a `hidden`/`clip` ancestor. 1px of
    // tolerance throughout: sub-pixel layout rounding is not clipping.
    const escaped = [];
    for (const child of el.querySelectorAll("*")) {
      const cr = child.getBoundingClientRect();
      if (cr.width <= 0 || cr.height <= 0) continue;
      if (getComputedStyle(child).visibility === "hidden") continue;
      const gate = constrainer(child, null);
      if (!gate || gate.scrolls) continue;  // reachable by scrolling
      const gateRect = gate.node.getBoundingClientRect();
      const over_right = cr.right - gateRect.right;
      const over_left = gateRect.left - cr.left;
      if (over_right > 1 || over_left > 1) {
        escaped.push({
          tag: child.tagName.toLowerCase(),
          cls: String(child.className || "").split(/\s+/)[0],
          // A control the user cannot reach is worse than text they
          // cannot read, so it is reported separately.
          interactive: !!child.closest("button, a[href], input, select, textarea, [tabindex]"),
          clipped_by: name(gate.node),
          over_right: Math.round(over_right),
          over_left: Math.round(over_left),
        });
      }
      if (escaped.length >= 12) break;  // enough to diagnose; not a dump
    }

    // VERTICAL REACHABILITY (Wave 5). The horizontal rules above say
    // nothing about whether content BELOW the fold can be got to, and a
    // client action is exactly where it cannot: `.o_action_manager` is
    // `overflow: hidden` at the pinned Odoo and provides no scrolling of
    // its own, because scrolling is a view's job and a bare client action
    // is not a view. A surface that does not declare its own
    // `overflow-y: auto` therefore has everything past the first screen
    // clipped away with no scrollbar for anyone to notice -- which is the
    // same defect shape as `clipped_silently`, one axis over, and was
    // measured on the guided setup at up to 1774px before this wave.
    const vs = getComputedStyle(el);
    const selfScrollsY = /auto|scroll/.test(vs.overflowY);
    let reachableBy = null;
    for (let node = el; node; node = node.parentElement) {
      const cs = getComputedStyle(node);
      if (/auto|scroll/.test(cs.overflowY) &&
          node.scrollHeight > node.clientHeight + 4) {
        reachableBy = name(node);
        break;
      }
      if (node === document.body) break;
    }
    const docEl = document.scrollingElement;
    if (!reachableBy && docEl.scrollHeight > docEl.clientHeight + 4) {
      reachableBy = "document";
    }
    const verticalOverflow = el.scrollHeight - el.clientHeight;

    // WHICH SURFACE THIS MEASURED ROOT BELONGS TO (Batch 2 closure).
    // `cls` is the element's FIRST class, and Odoo puts its own there:
    // a `<sheet class="o_sc_store_settings">` renders as
    // `class="o_form_sheet_bg o_sc_store_settings"`, so a matrix keyed on
    // `cls` alone reports `o_form_sheet_bg` for four different screens. The
    // connector's markers, on the root or anywhere inside it, are what say
    // which one this row is about.
    const markerSet = new Set();
    for (const klass of String(el.className || "").split(/\s+/)) {
      if (klass.startsWith("o_sc_")) { markerSet.add(klass); }
    }
    for (const node of el.querySelectorAll("[class*='o_sc_']")) {
      for (const klass of String(node.className || "").split(/\s+/)) {
        if (klass.startsWith("o_sc_")) { markerSet.add(klass); }
      }
    }

    const ownRect = own ? own.node.getBoundingClientRect() : null;
    surfaces.push({
      cls: name(el),
      classes: String(el.className || "").split(/\s+/).filter(Boolean),
      markers: Array.from(markerSet).sort(),
      // How far this surface's own content extends past its box, and
      // whether ANY ancestor can actually scroll to it.
      vertical_overflow: verticalOverflow,
      scrolls_vertically: selfScrollsY,
      vertical_reachable_by: reachableBy,
      unreachable_vertical: (verticalOverflow > 4 && !reachableBy)
        ? verticalOverflow : 0,
      rect: box(el),
      scroll_width: el.scrollWidth,
      client_width: el.clientWidth,
      // Overflow the surface itself declares it will handle. A table that
      // scrolls inside its own container is the design system's ANSWER to
      // wide content (§10), not a defect.
      overflow_x: cs.overflowX,
      self_overflow: self_overflow,
      unhandled_self_overflow: (!scrollable && self_overflow > 1)
        ? self_overflow : 0,
      clipped_by: own ? name(own.node) : null,
      clipped_silently: !!(own && !own.scrolls),
      clip_rect: ownRect ? {left: ownRect.left, right: ownRect.right} : null,
      // Horizontal displacement of the surface itself relative to a
      // constrainer that does NOT scroll -- the RTL failure shape, where a
      // mirrored layout pushes content off the opposite edge for good.
      escapes_left: (own && !own.scrolls)
        ? Math.round(Math.max(0, ownRect.left - r.left)) : 0,
      escapes_right: (own && !own.scrolls)
        ? Math.round(Math.max(0, r.right - ownRect.right)) : 0,
      escaped_descendants: escaped,
    });
  }

  // Every connector-owned root on screen, with the direction it actually
  // computes and whether the connector owns the STYLESHEET behind it. The
  // RTL matrix needs both: an Owl root that does not resolve `rtl` is a
  // defect in this repository, and a marked form root that does not is Odoo
  // mirroring through rtlcss exactly as it is designed to.
  const connectorRoots = [];
  for (const el of document.querySelectorAll(CONNECTOR_ROOT_SELECTOR)) {
    const r = el.getBoundingClientRect();
    connectorRoots.push({
      cls: name(el),
      // The marker, not just the first class: an RTL row that says it
      // measured `alert` or `o_form_sheet_bg` does not say WHICH surface,
      // and four different screens report the same first class.
      markers: String(el.className || "").split(/\s+/)
        .filter((klass) => klass.startsWith("o_sc_")).sort(),
      owl: el.matches(OWL_ROOT_SELECTOR),
      visible: r.width > 0 && r.height > 0 &&
               getComputedStyle(el).visibility !== "hidden",
      direction: getComputedStyle(el).direction,
    });
  }

  return JSON.stringify({
    doc_scroll_width: document.documentElement.scrollWidth,
    inner_width: window.innerWidth,
    direction: getComputedStyle(document.documentElement).direction,
    body_direction: getComputedStyle(document.body).direction,
    odoo_rtl_class: !!document.querySelector(".o_rtl"),
    rtl_stylesheets: Array.from(document.styleSheets)
      .map((s) => s.href).filter((h) => h && h.includes(".rtl.")).length,
    connector_root: root ? root.className.split(/\s+/)[0] : null,
    connector_direction: root ? getComputedStyle(root).direction : null,
    connector_roots: connectorRoots,
    surfaces: surfaces,
  });
})()
"""

FOCUSABLES_JS = r"""
(() => {
  const out = [];
  const roots = document.querySelectorAll(
    ".o_sc_dashboard, .o_sc_export_diff, .o_sc_setup, .o_form_view, .o_list_view, .modal-content"
  );
  for (const root of roots) {
    for (const el of root.querySelectorAll(
      "button:not([disabled]), a[href], input:not([disabled]), " +
      "select:not([disabled]), textarea:not([disabled]), [tabindex]"
    )) {
      const r = el.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0) continue;
      if (getComputedStyle(el).visibility === "hidden") continue;
      if (!el.id) {
        el.setAttribute("data-sc-focus-probe", out.length);
      }
      out.push({
        index: out.length,
        selector: `[data-sc-focus-probe="${out.length}"]`,
        classes: typeof el.className === "string" ? el.className : "",
        tag: el.tagName.toLowerCase(),
        label: (el.getAttribute("aria-label") || el.textContent || "")
          .trim().slice(0, 40),
        tab_index: el.tabIndex,
        width: Math.round(r.width),
        height: Math.round(r.height),
      });
    }
  }
  return JSON.stringify(out);
})()
"""


def _focus_indicator_js(selector):
    return r"""
(() => {
  const el = document.querySelector(%s);
  if (!el) return JSON.stringify({error: "gone"});
  el.focus();
  const s = getComputedStyle(el);
  const parse = (c) => {
    const m = c && c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[,\s/]+/).filter(Boolean).map(Number);
    return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1};
  };
  const lum = (c) => {
    const ch = [c.r, c.g, c.b].map((v) => {
      const x = v / 255;
      return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
    });
    return 0.2126*ch[0] + 0.7152*ch[1] + 0.0722*ch[2];
  };
  const bgOf = (node) => {
    while (node && node.nodeType === 1) {
      const c = parse(getComputedStyle(node).backgroundColor);
      if (c && c.a > 0.9) return c;
      node = node.parentElement;
    }
    return {r: 255, g: 255, b: 255, a: 1};
  };
  const outlineW = parseFloat(s.outlineWidth) || 0;
  const outlineC = parse(s.outlineColor);
  const bg = bgOf(el.parentElement || el);
  const ratio = (a, b) => {
    const l1 = lum(a), l2 = lum(b);
    return (Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05);
  };
  return JSON.stringify({
    focused: document.activeElement === el,
    outline_style: s.outlineStyle,
    outline_width_px: outlineW,
    outline_color: s.outlineColor,
    outline_offset: s.outlineOffset,
    box_shadow: s.boxShadow,
    background_behind: `rgb(${Math.round(bg.r)}, ${Math.round(bg.g)}, ${Math.round(bg.b)})`,
    indicator_contrast:
      outlineW > 0 && outlineC && outlineC.a > 0
        ? Math.round(ratio(outlineC, bg) * 100) / 100
        : null,
    has_indicator:
      (outlineW > 0 && s.outlineStyle !== "none") ||
      (s.boxShadow && s.boxShadow !== "none"),
  });
})()
""" % json.dumps(selector)


@tagged('post_install', '-at_install', '-standard', 'shopify_connector_visual')
class TestUiVisualEvidence(HttpCase):

    # ------------------------------------------------------------------
    # Harness
    # ------------------------------------------------------------------

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.evidence_dir = os.environ.get('SC_EVIDENCE_DIR')
        if cls.evidence_dir:
            cls._out = pathlib.Path(cls.evidence_dir)
            cls._persist = True
        else:
            cls._tmp = tempfile.TemporaryDirectory(suffix='_sc_evidence')
            cls.addClassCleanup(cls._tmp.cleanup)
            cls._out = pathlib.Path(cls._tmp.name)
            cls._persist = False
        (cls._out / 'screenshots').mkdir(parents=True, exist_ok=True)
        cls.manifest = []
        # ADMINISTRATOR, not User -- and this is a correction, not a
        # convenience (Wave 5).
        #
        # The guided setup is Administrator-only on every entry point
        # INCLUDING the read, so a Connector User opening it gets an
        # `AccessError` from `get_setup_state`, the component renders its
        # error band, and `.o_sc_setup` is present on the page. Every
        # instrument here waits for that selector — so the S1 capture was
        # succeeding, and photographing a permission error rather than the
        # wizard. Nothing asserted was wrong; what was measured was the wrong
        # screen.
        #
        # Administrator implies User, Operator and Reviewer under the accepted
        # SEC-2 role model, so this strictly widens what every other surface
        # in the set renders. It never narrows one.
        cls.user = new_test_user(
            cls.env, login='sc_visual', password='sc_visual',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_admin',
        )

    @classmethod
    def tearDownClass(cls):
        if cls.manifest:
            (cls._out / 'manifest.json').write_text(
                json.dumps(cls.manifest, indent=2, sort_keys=True))
            _logger.info(
                'CONNECTOR-VISUAL-EVIDENCE artifacts=%d dir=%s persisted=%s',
                len(cls.manifest), cls._out, cls._persist)
        super().tearDownClass()

    @contextlib.contextmanager
    def _browser(self, login='sc_visual'):
        browser = ChromeBrowser(self, headless=True)
        with self.allow_requests(browser=browser), contextlib.ExitStack() as stack:
            stack.callback(self._wait_remaining_requests)
            stack.enter_context(browser.cleanup)
            self.authenticate(login, login, browser=browser)
            self.cr.flush()
            self.cr.clear()
            yield browser

    def _eval(self, browser, expression, timeout=10.0):
        # `_websocket_request` returns the CDP RESULT PAYLOAD, not the whole
        # message (see `ChromeBrowser.take_screenshot`, which reads
        # `f.result()['data']` directly). So for `Runtime.evaluate` the shape
        # is {'result': {'type', 'value'}, 'exceptionDetails': ...} -- one
        # level shallower than the raw protocol message.
        #
        # `timeout` matters for the post-open ACTIONS: those await a real
        # round trip to the server and Odoo's CDP default is 10s, so a slower
        # machine turned a working page into a `TimeoutError` that hid the
        # in-page error message entirely. The waits inside the scripts are
        # shorter than this, so a genuine failure reports its own reason.
        res = browser._websocket_request('Runtime.evaluate', timeout=timeout, params={
            'expression': expression,
            'returnByValue': True,
            'awaitPromise': True,
        })
        if res.get('exceptionDetails'):
            self.fail('in-page evaluation failed: %s'
                      % json.dumps(res['exceptionDetails'])[:2000])
        return res.get('result', {}).get('value')

    def _viewport(self, browser, width, height=900):
        browser._websocket_request('Emulation.setDeviceMetricsOverride', params={
            'width': width, 'height': height,
            'deviceScaleFactor': 1, 'mobile': width <= 480,
        })

    def _emulate_reduced_motion(self, browser, reduce_motion):
        browser._websocket_request('Emulation.setEmulatedMedia', params={
            'features': [{
                'name': 'prefers-reduced-motion',
                'value': 'reduce' if reduce_motion else 'no-preference',
            }],
        })

    def _key(self, browser, key, code=None, vk=None):
        """One real key press at the browser's input layer."""
        for kind in ('rawKeyDown', 'keyUp'):
            browser._websocket_request('Input.dispatchKeyEvent', params={
                'type': kind, 'key': key, 'code': code or key,
                'windowsVirtualKeyCode': vk or 0,
                'nativeVirtualKeyCode': vk or 0,
            })

    def _dismiss_dialogs(self, browser):
        """Close anything modal, the way an operator closes it.

        A surface reached THROUGH a dialog leaves that dialog on screen, and
        navigating away from one whose focus is trapped inside it stalled
        `Page.navigate` until its 20-second timeout -- a failure that reads as
        a slow machine and is not one. Escape is used rather than a synthetic
        click on whatever button happens to match /cancel|close/: that
        matched buttons in INACTIVE modals too, and pressing a control in a
        dialog the user cannot see is not dismissal, it is a second action.

        Blurs first, so focus is back on the document before the page changes
        under it, and verifies the dialogs actually went rather than assuming
        the keypress worked.
        """
        self._eval(browser,
                   'document.activeElement && document.activeElement.blur(); '
                   'true')
        for _attempt in range(5):
            if not self._eval(
                browser, 'document.querySelector(".modal") !== null'
            ):
                return
            self._key(browser, 'Escape', vk=27)
            deadline = time.time() + 5
            while time.time() < deadline:
                if not self._eval(
                    browser, 'document.querySelector(".modal") !== null'
                ):
                    return
                time.sleep(0.1)
        # Escape did not clear it; say so rather than navigating into a stall.
        self.fail('a modal dialog would not close, so the next surface would '
                  'have been measured behind it')

    def _open(self, browser, path, wait_for='.o_list_view, .o_form_view, '
                                            '.o_sc_dashboard, .o_sc_export_diff',
              after=None):
        from odoo.tests.common import HOST  # noqa: PLC0415
        url = 'http://%s:%s%s' % (HOST, odoo_http_port(), path)
        self._dismiss_dialogs(browser)
        browser.navigate_to(url, wait_stop=True)
        deadline = time.time() + 30
        while time.time() < deadline:
            found = self._eval(
                browser, 'document.querySelector(%s) !== null'
                         % json.dumps(wait_for))
            if found:
                # Let Owl finish its first paint before measuring.
                self._eval(browser, 'new Promise(r => requestAnimationFrame('
                                    '() => requestAnimationFrame(r)))')
                if after:
                    action_js, action_wait = after
                    self._eval(browser, action_js, timeout=90.0)
                    if not self._wait_for_selector(browser, action_wait):
                        self.fail('surface %r never reached %r after its '
                                  'post-open action' % (path, action_wait))
                return True
            time.sleep(0.25)
        self.fail('surface %r never rendered %r' % (path, wait_for))

    def _wait_for_selector(self, browser, selector, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._eval(browser, 'document.querySelector(%s) !== null'
                                   % json.dumps(selector)):
                self._eval(browser, 'new Promise(r => requestAnimationFrame('
                                    '() => requestAnimationFrame(r)))')
                return True
            time.sleep(0.25)
        return False

    def _shoot(self, browser, name, criterion):
        data = browser._websocket_request('Page.captureScreenshot', params={
            'format': 'png', 'captureBeyondViewport': True,
        })
        png = data.get('data')
        self.assertTrue(png, 'no screenshot data for %s' % name)
        raw = base64.b64decode(png)
        path = self._out / 'screenshots' / ('%s.png' % name)
        path.write_bytes(raw)
        type(self).manifest.append({
            'artifact': 'screenshots/%s.png' % name,
            'bytes': len(raw),
            'criterion': criterion,
        })
        return path

    def _record(self, name, payload, criterion):
        path = self._out / ('%s.json' % name)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        type(self).manifest.append({
            'artifact': '%s.json' % name,
            'criterion': criterion,
        })

    # ------------------------------------------------------------------
    # Fixtures: the states each surface must be photographed in
    # ------------------------------------------------------------------

    def _seed(self):
        """One store with U2 and U3 rows in their non-empty states."""
        store = self.env['shopify.connector.store'].sudo().create({
            'name': 'Visual evidence store',
            'shop_domain': 'visual-evidence.myshopify.com',
            'api_version': '2026-07',
        })
        store.sudo().write({'state': 'connected'})
        self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': store.id,
            'inventory_domain_enabled': True,
        })
        self._seed_setup_states(store)
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1)
        location = self.env['stock.location'].sudo().create({
            'name': 'Visual evidence location',
            'usage': 'internal',
            'location_id': warehouse.view_location_id.id,
        })
        mapping = self.env['shopify.connector.location.mapping'].sudo().create({
            'store_id': store.id,
            'shopify_gid': 'gid://shopify/Location/VIS',
            'odoo_location_id': location.id,
            'match_key': 'manual',
            'shopify_location_name_snapshot': 'Visual warehouse',
        })
        template = self.env['product.template'].sudo().create({
            'name': 'Visual evidence widget'})
        tbinding = self.env[
            'shopify.connector.product.template.binding'].sudo().create({
                'store_id': store.id,
                'shopify_gid': 'gid://shopify/Product/VIS',
                'product_template_id': template.id,
            })
        vbinding = self.env[
            'shopify.connector.product.variant.binding'].sudo().create({
                'store_id': store.id,
                'shopify_gid': 'gid://shopify/ProductVariant/VIS',
                'product_variant_id': template.product_variant_id.id,
                'product_template_binding_id': tbinding.id,
            })
        level = self.env[
            'shopify.connector.inventory.level.binding'].sudo().create({
                'store_id': store.id,
                'product_variant_binding_id': vbinding.id,
                'location_mapping_id': mapping.id,
                'shopify_inventory_item_gid': 'gid://shopify/InventoryItem/VIS',
                'first_push_state': 'previewed',
                'first_push_preview_qty': 12.0,
                'pending_target_available': 12.0,
            })
        preview = self._seed_export_preview(store, template, tbinding)
        batch2 = self._seed_batch2(store)
        self.env.flush_all()
        return dict({
            'store': store, 'mapping': mapping, 'level': level,
            'template_binding': tbinding, 'variant_binding': vbinding,
            'preview': preview,
        }, **batch2)

    def _seed_batch2(self, store):
        """The Batch 2 P0 surfaces, in the states worth photographing.

        ONE STORE, AND THAT IS MEASURED RATHER THAN ASSUMED. The first version
        of this seed created a second store so the order controls and the
        product controls could be photographed separately. It broke four
        guided-setup captures with `no offline path on the credential chooser`:
        the setup surface is opened by action with no id and auto-selects a
        store only while there is exactly one, so a second store replaced the
        credential step with a picker. Both control groups live on the same
        form anyway, so one capture measures both.

        The decision rows below are produced through PRODUCTION code -- the
        importer's own evidence builder, the tax importer's own refusal, and
        the dispatcher's own `_route_failure` seam -- rather than hand-written,
        so a change to either evidence schema or to the routing breaks this
        fixture instead of leaving it photographing a shape the product no
        longer produces.
        """
        settings = self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )
        values = {
            'product_domain_enabled': True,
            'product_first_sync_source': 'shopify_source',
            'sale_domain_enabled': True,
        }
        for optional in (
            'product_scheduled_sync_enabled', 'order_scheduled_sync_enabled',
        ):
            if optional in settings._fields:
                values[optional] = True
        settings.sudo().write(values)
        out = {'settings': settings}
        out.update(self._seed_batch2_match(store))
        out.update(self._seed_batch2_tax(store))
        return out

    def _block_match_import(self, store, candidates, gid, stamp):
        """One ambiguous product import, stopped by PRODUCTION code.

        Extracted from `_seed_batch2_match` (Batch 2 evidence closure,
        2026-07-31) so the live-region test can raise a SECOND, NEWER
        ambiguity for the same Shopify product and let the model's own
        `_supersede_stale_siblings` retire the first one -- which is the only
        honest way to render the `superseded` band, and is what makes that
        band's semantics measurable rather than argued.
        """
        from odoo.addons.shopify_connector_product.models.\
            shopify_connector_product_match_decision import (
                DECISION_LEVEL_TEMPLATE,
                build_match_evidence,
            )
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': stamp,
            'shopify_target_gid': gid,
        })
        evidence = build_match_evidence(
            self.env,
            level=DECISION_LEVEL_TEMPLATE,
            shopify_product_gid=gid,
            remote_updated_at=stamp,
            match_key='sku_reference',
            match_values=['VIS-DUP'],
            candidate_ids=candidates.ids,
            candidate_total=len(candidates),
            title_preview='Visual evidence ambiguous product',
            sku_preview='VIS-DUP',
        )
        self.env['shopify.connector.job.dispatch']._route_failure(
            job, 'ambiguous_match',
            'Ambiguous product-template match for Shopify product %s: %d '
            'candidate product.template record(s) found.'
            % (gid, len(candidates)),
            evidence,
        )
        job.invalidate_recordset()
        return job, self.env[
            'shopify.connector.product.match.decision'
        ].sudo().search([('job_id', '=', job.id)], limit=1)

    def _seed_batch2_match(self, store):
        if 'shopify.connector.product.match.decision' not in self.env:
            return {}
        first = self.env['product.template'].sudo().create(
            {'name': 'Visual evidence candidate A'})
        second = self.env['product.template'].sudo().create(
            {'name': 'Visual evidence candidate B'})
        (first | second).product_variant_ids.sudo().write(
            {'default_code': 'VIS-DUP'})
        candidates = first | second

        def blocked(gid, stamp):
            return self._block_match_import(store, candidates, gid, stamp)

        pending_job, pending = blocked(
            'gid://shopify/Product/7346299043911', '2026-07-30T09:15:00Z')
        resolved_job, resolved = blocked(
            'gid://shopify/Product/7346299043928', '2026-07-30T09:16:00Z')
        if resolved:
            resolved.sudo().write({
                'state': 'confirmed',
                'selected_template_id': first.id,
                'resolved_uid': self.env.user.id,
                'resolved_at': fields.Datetime.now(),
                'resumed_job_state': 'queued',
            })
        return {
            'match_job': pending_job,
            'match_decision': pending,
            'match_decision_resolved': resolved,
            'match_resolved_job': resolved_job,
            'match_candidate': first,
            'match_candidates': candidates,
        }

    def _seed_batch2_tax(self, store):
        """One order stopped on a tax fingerprint the connector does not know.

        Produced by the importer's own refusal, so the evidence on screen is
        the evidence production writes -- never a hand-built job-log row.
        """
        if 'shopify.connector.tax.mapping' not in self.env:
            return {}
        settings = self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings.order_company_id:
            return {}
        company = settings.order_company_id
        partner = self.env['res.partner'].sudo().create(
            {'name': 'Visual evidence tax customer'})
        order = self.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'company_id': company.id,
        })
        evidence = {
            'title': 'Visual evidence VAT',
            'source': 'Shopify',
            'rate': 0.05,
            'ratePercentage': 5.0,
            'channelLiable': None,
            'priceSet': {
                'shopMoney': {'amount': '5.00'},
                'presentmentMoney': {'amount': '5.00'},
            },
        }
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'manual_sync',
            'job_type': 'order_import_sync',
            'state': 'queued',
            'payload_hash': 'visual-evidence-tax',
            'shopify_target_gid': 'gid://shopify/Order/VISTAX',
        })
        try:
            self.env['shopify.connector.order.importer']._resolve_taxes(
                order, store, [evidence], False, settings,
            )
        except Exception as exc:  # the importer's own classified refusal
            error_class = getattr(exc, 'error_class', None)
            if not error_class:
                job.sudo().unlink()
                return {}
            self.env['shopify.connector.job.dispatch']._route_failure(
                job, error_class, getattr(exc, 'reason', str(exc)),
                getattr(exc, 'technical_detail', False),
            )
        else:
            job.sudo().unlink()
            return {}
        job.invalidate_recordset()
        if not job.tax_decision_pending:
            return {}
        return {'tax_job': job}

    def _seed_setup_states(self, store):
        """Put the guided setup into the three states worth photographing.

        Wave 5 makes the setup surface the one that most needs measuring at
        390px: the Permissions step is the longest body copy in the connector,
        the Location mapping step renders an unbounded list of Shopify
        identities (long, unbreakable strings -- the classic overflow shape),
        and the Final readiness step renders one row per check with a reason
        and an action control on each. All three are captured, and all three
        are measured for connector-owned horizontal overflow rather than only
        looked at.

        The resume point is what selects which step renders, so it is written
        here per capture -- the surfaces list below re-points it before each
        one. Odoo rows only: no credential is used and nothing is enqueued.
        """
        settings = self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )
        # A populated Shopify location cache, so the Location mapping step has
        # something to render -- and enough rows that the list is long.
        #
        # BATCH 1 UI COMPLETION. 60, not 6, and the number is load bearing:
        # the search page is 50 rows, so a set of 60 is the smallest one that
        # renders a FULL page, offers Load more, and then exhausts. Six rows
        # photographed a list that never paged, so the surface the correction
        # rebuilt -- the paged one, with its counter, its Load more control
        # and its four empty states -- was never in the measured set at all.
        if 'shopify.connector.location' in self.env:
            existing = self.env['shopify.connector.location'].sudo().search_count(
                [('store_id', '=', store.id)],
            )
            for index in range(existing + 1, LOCATION_FIXTURE_ROWS + 1):
                self.env['shopify.connector.location'].sudo().create({
                    'store_id': store.id,
                    'shopify_location_gid':
                        'gid://shopify/Location/VISUAL%d' % index,
                    # A long, unbreakable identity in the name of one row: the
                    # classic horizontal-overflow shape, and the reason this
                    # list is measured rather than looked at.
                    'name': 'Visual evidence warehouse %d%s' % (
                        index,
                        ' — Groot-Bijgaarden distributiecentrum Noordwest'
                        if index == 1 else '',
                    ),
                    'shopify_location_active': True,
                })
        # A recorded readiness result, so the Final readiness step renders a
        # full result list rather than "Not run yet".
        self.env['shopify.connector.readiness.check'].run_for_store(store)
        settings.sudo().write({'setup_wizard_step_key': 'scopes'})
        self.env.flush_all()
        return settings

    def _set_setup_step(self, store, step_key):
        """Point the wizard at one step, for one capture."""
        self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        ).write({'setup_wizard_step_key': step_key})
        self.env.flush_all()

    def _seed_export_preview(self, store, template, binding):
        """One export preview carrying a REFUSAL and a TAG REMOVAL.

        Those two are the whole reason the S7 diff exists: the refusals must
        sit above the confirm control, and the tag removals must be
        enumerated by name. A screenshot of an empty diff would prove neither,
        so the fixture puts both on screen.

        Returns `None` when `shopify_connector_product_export` is not
        installed -- the same condition `_reachable_surfaces` already handles
        for every export action. The canonical runner installs it always, and
        `test_the_export_diff_surface_is_reachable_when_export_is_installed`
        fails if it is installed and this surface is nonetheless dropped, so
        the diff cannot go missing quietly.

        Odoo rows only -- no store credential is used, no Shopify request is
        made, and nothing is enqueued.
        """
        if 'shopify.connector.product.export.preview' not in self.env:
            _logger.info('visual evidence: product_export not installed; the '
                         'S7 diff surface is not captured in this build')
            return None
        self.env['shopify.connector.store.settings'].sudo().search([
            ('store_id', '=', store.id)]).write({
                'product_export_domain_enabled': True,
                'price_source_of_truth': 'odoo_authoritative',
            })
        template.sudo().write({
            'shopify_export_enabled': True,
            'shopify_export_tags': 'keep-me',
        })
        now = fields.Datetime.now()
        Preview = self.env['shopify.connector.product.export.preview']
        return Preview._preview_surface('_create_preview').create({
            'store_id': store.id,
            'product_template_id': template.id,
            'product_template_binding_id': binding.id,
            'export_path': 'update',
            'state': 'previewed',
            'diff': {
                'scalars': [{'field': 'tags',
                             'from': ['keep-me', 'merchant-added'],
                             'to': ['keep-me']}],
                'tag_replacement': {
                    'applies': True,
                    'removed': ['merchant-added'],
                    'resulting': ['keep-me'],
                    'note': "Confirming this export replaces the product's "
                            'COMPLETE Shopify tag list with the Odoo list.',
                },
                'untouched': {'collections': True, 'metafields': False,
                              'existing_media': True,
                              'note': 'Never included in this export.'},
                'media': {'exported': False, 'reason': 'Media export is off.',
                          'appends': []},
            },
            'apply_plan': {'steps': [{'step': 'product_export_update',
                                      'state': 'pending',
                                      'fields': ['tags']}], 'cursor': 0},
            'blocked_differences': {'items': [{
                'kind': 'unowned_remote_variant',
                'detail': 'A Shopify variant is not bound to any Odoo '
                          'variant. It is left exactly as it is.',
            }]},
            'has_blocked_differences': True,
            'remote_product_gid': binding.shopify_gid,
            'remote_updated_at': '2026-07-26T00:00:00Z',
            'source_write_date': Preview._source_write_date(template),
            'previewed_at': now,
            'expires_at': fields.Datetime.add(now, hours=24),
        })

    #: (name, path, wait-for selector, criterion[, after_js[, setup_step]])
    #: for every captured surface. `after_js` runs once the page has rendered,
    #: for the one surface that is reached by pressing a control rather than
    #: by URL. `setup_step` is a SEMANTIC step key written to the store's
    #: resume point BEFORE the page is opened, which is how the guided setup
    #: is photographed on a specific step -- the wizard resumes where the
    #: server says it left off, so that is the only honest way to select one.
    def _surfaces(self, seeded):
        act = '/odoo/action-%s'
        return [
            ('u0-dashboard-healthy',
             act % 'shopify_connector_core.action_shopify_connector_dashboard',
             '.o_sc_dashboard', 'DESIGN SYSTEM §9 dashboard hierarchy'),
            # S1 (2026-07-27). The guided setup is the connector's THIRD
            # stylesheet-bearing Owl surface and the first screen a new
            # operator ever sees, so it belongs in the measured set rather
            # than in the structurally-implemented-and-never-rendered
            # category this whole file exists to close. It is reachable by
            # URL and opens on step 1, which is the step with the most copy
            # and therefore the most contrast pairs.
            ('s1-setup-wizard-welcome',
             act % 'shopify_connector_core.action_shopify_connector_setup_wizard',
             '.o_sc_setup', 'S1 guided setup; §12 a11y gates, §14 responsive',
             None, 'welcome'),
            # WAVE 5. The three states that make the sticky action row and the
            # 390px overflow rule falsifiable rather than merely asserted:
            # the longest body copy in the connector, an unbounded list of
            # long unbreakable Shopify identities, and one row per readiness
            # check with a reason and an action control on each.
            ('s1-setup-permissions-long',
             act % 'shopify_connector_core.action_shopify_connector_setup_wizard',
             '.o_sc_setup',
             'S1 long Permissions step; sticky actions over long content',
             None, 'scopes'),
            ('s1-setup-location-mapping',
             act % 'shopify_connector_core.action_shopify_connector_setup_wizard',
             '.o_sc_setup',
             'S1 Location mapping with multiple cached Shopify locations',
             None, 'location_mapping'),
            # BATCH 1 UI COMPLETION (2026-07-30). Everything below is a
            # surface the correction CHANGED, and none of them existed in the
            # measured set: four of the six do not exist until an operator
            # acts, and the previous campaign photographed the step they live
            # on before the thing under test was on it.
            ('s1-setup-credential-dev-dashboard',
             act % 'shopify_connector_core.action_shopify_connector_setup_wizard',
             '.o_sc_setup',
             'S1 credential chooser, Dev Dashboard path (default)',
             None, 'credential'),
            ('s1-setup-credential-offline-token',
             act % 'shopify_connector_core.action_shopify_connector_setup_wizard',
             '.o_sc_setup',
             'S1 credential chooser, offline access-token path selected',
             (CREDENTIAL_OFFLINE_JS, '.sc_setup_token'), 'credential'),
            ('s1-setup-location-search-results',
             act % 'shopify_connector_core.action_shopify_connector_setup_wizard',
             '.o_sc_setup',
             'S1 location search with a result set, counter and Clear',
             (LOCATION_SEARCH_JS, '.sc_setup_search_shopify_clear'),
             'location_mapping'),
            ('s1-setup-location-loaded-more',
             act % 'shopify_connector_core.action_shopify_connector_setup_wizard',
             '.o_sc_setup',
             'S1 location search with a second page accumulated',
             (LOCATION_LOAD_MORE_JS, '.sc_setup_search_shopify_clear'),
             'location_mapping'),
            ('s1-setup-location-no-result',
             act % 'shopify_connector_core.action_shopify_connector_setup_wizard',
             '.o_sc_setup',
             'S1 location search that matched nothing, keeping its way out',
             (LOCATION_NO_RESULT_JS, '.sc_setup__empty--shopify'),
             'location_mapping'),
            ('s1-setup-final-readiness',
             act % 'shopify_connector_core.action_shopify_connector_setup_wizard',
             '.o_sc_setup',
             'S1 Final readiness with a long result list',
             None, 'final_readiness'),
            ('u2-orders-workspace-empty',
             act % 'shopify_connector_sale.action_shopify_connector_order_workspace',
             '.o_list_view, .o_view_nocontent', 'U2 S9 orders; §11 empty state'),
            ('u2-cod-reconciliation-empty',
             act % 'shopify_connector_sale.action_shopify_connector_cod_reconciliation',
             '.o_list_view, .o_view_nocontent', 'U2 COD ledger; §11 empty state'),
            ('u2-customer-matching-empty',
             act % 'shopify_connector_sale.action_shopify_connector_customer_binding',
             '.o_list_view, .o_view_nocontent', 'U2 S6 customer matching'),
            ('u2-product-matching',
             act % 'shopify_connector_product.action_shopify_connector_product_template_binding',
             '.o_list_view, .o_view_nocontent', 'U2 S8 product matching'),
            ('u2-inventory-workspace',
             act % 'shopify_connector_inventory.action_shopify_connector_inventory_workspace',
             '.o_list_view', 'U2 S19 inventory workspace'),
            ('u2-first-push-guard-previewed',
             act % 'shopify_connector_inventory.action_shopify_connector_inventory_first_push',
             '.o_list_view', 'U2 S11 first-push guard; warning state'),
            ('u2-first-push-form-awaiting-confirmation',
             (act % 'shopify_connector_inventory.action_shopify_connector_inventory_first_push')
             + '/%d' % seeded['level'].id,
             '.o_form_view', 'U2 S11 form; warning state + action control'),
            ('u2-location-mapping-form',
             (act % 'shopify_connector_inventory.action_shopify_connector_location_mapping')
             + '/%d' % seeded['mapping'].id,
             '.o_form_view', 'U2 S10 location mapping; action control'),
            # The two withdrawal dialogs, opened by pressing the control an
            # operator presses. The consequence copy inside them is the
            # longest in the module and it is what an administrator reads
            # before an irreversible ceremony restarts, so it is measured at
            # every width, in both directions, and at 200% zoom.
            ('u2-first-push-withdraw-dialog',
             (act % 'shopify_connector_inventory.action_shopify_connector_inventory_first_push')
             + '/%d' % seeded['level'].id,
             '.o_form_view',
             'TD-020 single-pair withdrawal dialog; consequence copy',
             (_open_dialog_js('Withdraw First Push'),
              '.modal:not(.o_inactive_modal) .o_form_view')),
            ('u2-location-withdraw-all-dialog',
             (act % 'shopify_connector_inventory.action_shopify_connector_location_mapping')
             + '/%d' % seeded['mapping'].id,
             '.o_form_view',
             'TD-020 mapping-level withdrawal dialog; counts + storefront '
             'consequence',
             (_open_dialog_js('Withdraw First Pushes'),
              '.modal:not(.o_inactive_modal) .o_form_view')),
            ('u3-export-previews',
             act % 'shopify_connector_product_export.action_shopify_connector_product_export_preview',
             '.o_list_view, .o_view_nocontent', 'U3 S7 export review queue'),
            ('u3-exported-media',
             act % 'shopify_connector_product_export.action_shopify_connector_product_media_binding',
             '.o_list_view, .o_view_nocontent', 'U3 media registry'),
            ('u3-reconnect-backfill',
             act % 'shopify_connector_product_export.action_shopify_connector_export_backfill',
             '.o_list_view, .o_form_view, .o_view_nocontent',
             'U3 S25/S26 reconnect and backfill'),
            ('u3-export-diagnostics',
             act % 'shopify_connector_product_export.action_shopify_connector_export_diagnostics',
             '.o_list_view, .o_form_view, .o_view_nocontent',
             'U3 S31 export diagnostics'),
            ('u3-export-settings',
             act % 'shopify_connector_product_export.action_shopify_connector_store_settings_export',
             '.o_list_view, .o_form_view, .o_view_nocontent',
             'U3 export settings/ownership/retention'),
            # The S7 Owl diff. It is the safety-critical U3 surface -- the one
            # that discloses the refusals and enumerates the tag removals
            # above the confirm control -- and it is the only connector
            # surface with its own stylesheet besides the dashboard, so it is
            # the one that most needs a measured contrast and RTL result.
            # It is not reachable by URL: it is a client action opened by the
            # preview form's "Review Export" button, so the button is pressed.
        ] + ([
            # BATCH 2 P0 MERCHANT REACHABILITY (2026-07-31). Six surfaces that
            # DID NOT EXIST before this batch, which is exactly the category
            # the earlier campaigns could not have covered.
            ('b2-store-settings-canonical',
             (act % 'shopify_connector_core.'
                    'action_shopify_connector_store_settings_canonical')
             + '/%d' % seeded['settings'].id,
             '.o_form_view',
             'Batch 2 canonical Store Settings; the surface that did not exist',
             ),
            ('b2-store-form-controls',
             (act % 'shopify_connector_core.action_shopify_connector_store')
             + '/%d' % seeded['store'].id,
             '.o_form_view',
             'Batch 2 order AND product import controls, with the '
             'scheduled-position copy beside each'),
        ] if seeded.get('settings') else []) + ([
            ('b2-tax-decision-dialog',
             (act % 'shopify_connector_core.'
                    'action_shopify_connector_error_center')
             + '/%d' % seeded['tax_job'].id,
             '.o_form_view',
             'Batch 2 tax decision dialog; what Shopify charged, above the '
             'choice',
             (_open_dialog_js('Map tax'),
              '.modal:not(.o_inactive_modal) .o_form_view')),
        ] if seeded.get('tax_job') else []) + ([
            ('b2-product-match-decisions-list',
             act % 'shopify_connector_product.'
                   'action_shopify_connector_product_match_decision',
             '.o_list_view, .o_view_nocontent',
             'Batch 2 Match Decisions workspace; state as text and colour'),
            ('b2-product-match-decision-pending',
             (act % 'shopify_connector_product.'
                    'action_shopify_connector_product_match_decision')
             + '/%d' % seeded['match_decision'].id,
             '.o_form_view',
             'Batch 2 pending product match decision; evidence + candidates'),
            ('b2-product-match-decision-dialog',
             (act % 'shopify_connector_core.'
                    'action_shopify_connector_error_center')
             + '/%d' % seeded['match_job'].id,
             '.o_form_view',
             'Batch 2 match decision dialog; consequence copy above the choice',
             (_open_dialog_js('Choose the matching Odoo product'),
              '.modal:not(.o_inactive_modal) .o_form_view')),
            ('b2-product-match-decision-resolved',
             (act % 'shopify_connector_product.'
                    'action_shopify_connector_product_match_decision')
             + '/%d' % seeded['match_decision_resolved'].id,
             '.o_form_view',
             'Batch 2 resolved decision; actor, choice and resumed job state'),
        ] if seeded.get('match_decision')
             and seeded.get('match_decision_resolved') else []) + ([
            ('u3-export-diff-refusal-and-tag-removal',
             (act % 'shopify_connector_product_export.'
                    'action_shopify_connector_product_export_preview')
             + '/%d' % seeded['preview'].id,
             '.o_form_view',
             'U3 S7 export diff: refusal disclosure + enumerated tag removals',
             (REVIEW_EXPORT_JS, '.o_sc_export_diff')),
        ] if seeded.get('preview') else [])

    def _reachable_surfaces(self, seeded):
        """Only the surfaces whose action actually exists in this build."""
        out = []
        for entry in self._surfaces(seeded):
            name, path, wait, criterion = entry[:4]
            after = entry[4] if len(entry) > 4 else None
            setup_step = entry[5] if len(entry) > 5 else None
            xmlid = path.split('/odoo/action-')[1].split('/')[0]
            if self.env.ref(xmlid, raise_if_not_found=False):
                out.append((name, path, wait, criterion, after, setup_step))
            else:
                _logger.info(
                    'visual evidence: skipping %s -- action %s not present '
                    'in this build', name, xmlid)
        self.assertGreaterEqual(
            len(out), 8,
            'only %d U2/U3 surfaces resolved; the evidence set would be too '
            'thin to be meaningful' % len(out))
        return out

    def test_the_export_diff_surface_is_reachable_when_export_is_installed(self):
        """The S7 diff must not drop out of the evidence set quietly.

        It is the only U3 surface whose refusal disclosure and enumerated tag
        removals can be photographed, and it is reached by pressing a control
        rather than by URL -- which is exactly the kind of surface that goes
        missing from a capture set without anyone noticing.
        """
        if 'shopify.connector.product.export.preview' not in self.env:
            self.skipTest('shopify_connector_product_export is not installed')
        seeded = self._seed()
        self.assertTrue(
            seeded.get('preview'),
            'product_export is installed but no export preview was seeded, so '
            'the S7 diff would not be captured',
        )
        names = [entry[0] for entry in self._reachable_surfaces(seeded)]
        self.assertIn(
            'u3-export-diff-refusal-and-tag-removal', names,
            'the S7 export diff is not in the captured surface set',
        )

    def test_the_setup_captures_render_the_wizard_not_a_permission_error(self):
        """The S1 captures must photograph the wizard, not its error band.

        `.o_sc_setup` is present in BOTH the ready and the error branch of the
        component, so every instrument in this file waits for a selector that
        an `AccessError` also satisfies. That is how a Connector User could
        produce a green, complete, entirely worthless S1 capture set. This
        asserts the distinguishing evidence directly: the step rail exists,
        it carries all four merchant phases, the action row exists, and no error band
        is on screen.
        """
        seeded = self._seed()
        checked = 0
        with self._browser() as browser:
            self._viewport(browser, WIDTHS['desktop'])
            for name, path, wait, _criterion, after, setup_step in (
                self._reachable_surfaces(seeded)
            ):
                if not name.startswith('s1-setup'):
                    continue
                checked += 1
                if setup_step:
                    self._set_setup_step(seeded['store'], setup_step)
                self._open(browser, path, wait, after)
                payload = json.loads(self._eval(browser, r"""
(() => JSON.stringify({
  steps: document.querySelectorAll(".sc_setup_phase").length,
  has_actions: !!document.querySelector(".sc_setup__actions"),
  has_error: !!document.querySelector(".sc_setup__panel") ? false : true,
  heading: (document.querySelector(".sc_setup__heading") || {}).textContent
    ? document.querySelector(".sc_setup__heading").textContent.trim()
      .replace(/\s+/g, " ").slice(0, 60)
    : null,
}))()
"""))
                self.assertEqual(
                    payload['steps'], 4,
                    '%s rendered %d phases, so it is not the wizard'
                    % (name, payload['steps']))
                self.assertTrue(
                    payload['has_actions'],
                    '%s has no action row, so it rendered the error branch'
                    % name)
                self.assertFalse(
                    payload['has_error'],
                    '%s rendered no step panel at all' % name)
                self.assertTrue(payload['heading'], '%s has no heading' % name)
        self.assertGreaterEqual(
            checked, 4,
            'only %d S1 setup surfaces were reachable; the Wave 5 capture set '
            'is not present' % checked)

    # ------------------------------------------------------------------
    # A + B. Desktop, tablet and mobile
    # ------------------------------------------------------------------

    def _clipping_defects(self, name, width, metrics):
        """Connector-owned clipping at one surface and width (TD-016).

        Two distinct defects, kept separate because they fail differently:

        `unhandled_self_overflow` — the surface is wider than its own box
        and has not declared `overflow-x: auto|scroll`. The design system's
        answer to wide content is that the CONTENT scrolls inside its own
        container (§10); a surface that overflows without offering that is
        content the user simply cannot get to.

        `unreachable_vertical_content` (Wave 5) — the same defect one axis
        over, and the one the horizontal rules were structurally unable to
        see. A client action renders inside `.o_action_manager`, which is
        `overflow: hidden` and provides no scrolling of its own, so a
        surface that does not declare `overflow-y: auto` has everything past
        the first screen clipped away with no scrollbar for anyone to
        notice. Measured on the guided setup at between 328px and 1774px
        before this wave, at all four required widths, with `doc_extent: 0`
        and no scrollable element anywhere in the ancestor chain.

        `escaped_descendants` — something inside the surface is rendered
        outside the rectangle its clipping ancestor actually shows. This is
        the case the document-total check could never see, because an
        ancestor with `overflow: hidden` clips it silently and the page
        never grows.
        """
        defects = []
        for surface in metrics.get('surfaces') or []:
            if surface['unhandled_self_overflow']:
                defects.append({
                    'kind': 'unhandled_self_overflow',
                    'page': name, 'width': width, 'surface': surface['cls'],
                    'scroll_width': surface['scroll_width'],
                    'client_width': surface['client_width'],
                    'overflow_x': surface['overflow_x'],
                })
            if surface.get('unreachable_vertical'):
                defects.append({
                    'kind': 'unreachable_vertical_content',
                    'page': name, 'width': width, 'surface': surface['cls'],
                    'vertical_overflow': surface['vertical_overflow'],
                    'scrolls_vertically': surface['scrolls_vertically'],
                    'vertical_reachable_by': surface['vertical_reachable_by'],
                })
            if surface['escapes_left'] > 1 or surface['escapes_right'] > 1:
                defects.append({
                    'kind': 'surface_displaced',
                    'page': name, 'width': width, 'surface': surface['cls'],
                    'clipped_by': surface['clipped_by'],
                    'escapes_left': surface['escapes_left'],
                    'escapes_right': surface['escapes_right'],
                })
            escaped = surface.get('escaped_descendants') or []
            if escaped:
                defects.append({
                    'kind': 'clipped_content',
                    'page': name, 'width': width, 'surface': surface['cls'],
                    'clipped_by': surface['clipped_by'],
                    'clipped_silently': surface['clipped_silently'],
                    'interactive': [
                        item for item in escaped if item['interactive']
                    ],
                    'escaped': escaped,
                })
        return defects

    def test_the_overflow_instrument_covers_every_connector_surface(self):
        """TD-016: a new surface cannot be added outside the measurement.

        The instrument names its surfaces explicitly rather than matching a
        prefix, which is precise but goes stale silently. This reads the
        `o_sc_*` roots that actually exist in the shipped Owl templates and
        stylesheets and fails if one of them is not measured — so the cost
        of adding a surface is one line here, and the cost of forgetting is
        a failing test rather than an unmeasured screen.

        BATCH 2 EVIDENCE CLOSURE (2026-07-31): `views/` and `wizards/` are
        read too. Until this correction every connector surface root lived in
        an Owl template under `static/src/`, so globbing only there was
        complete; the Batch 2 surfaces are ordinary form views and declare
        their measured roots in the view arch, which this guard could not see
        at all. A marker class added to a form arch and left out of the
        instrument would have been exactly the omission this test exists to
        prevent, going unnoticed by the test that prevents it.
        """
        import re

        addons = pathlib.Path(__file__).resolve().parents[2]
        found = set()
        for pattern in ('shopify_connector_*/static/src/**/*.xml',
                        'shopify_connector_*/static/src/**/*.scss',
                        'shopify_connector_*/views/**/*.xml',
                        'shopify_connector_*/wizards/**/*.xml'):
            for path in addons.glob(pattern):
                found.update(re.findall(r'\bo_sc_[a-z0-9_]+', path.read_text()))
        self.assertTrue(
            found,
            'no connector surface classes were discovered at all; this '
            'guard is vacuous and the glob is wrong.',
        )
        unmeasured = sorted(
            name for name in found if '.%s' % name not in OVERFLOW_JS
        )
        self.assertFalse(unmeasured, (
            'these connector surface classes exist but the TD-016 overflow '
            'instrument does not measure them, so clipping on them would go '
            'unseen: %s' % unmeasured
        ))

    def test_the_overflow_instrument_can_actually_fail(self):
        """TD-016's central assertion: this instrument is falsifiable.

        The defect TD-016 records is not that a surface overflowed. It is
        that the *check* could not have noticed if one had. The old
        instrument compared `documentElement.scrollWidth` against
        `innerWidth`, and every connector surface sits inside
        `.o_action_manager`, which is `overflow: hidden` — so a connector
        panel 400px too wide was clipped silently, the document never grew,
        and the assertion passed. A green result meant nothing.

        So this injects exactly that defect — an element far wider than its
        surface, inside an ancestor that hides rather than scrolls — and
        requires the instrument to report it. Without this, "no clipping
        found" is indistinguishable from "no clipping findable".
        """
        seeded = self._seed()
        with self._browser() as browser:
            self._viewport(browser, WIDTHS['mobile'])
            name, path, wait, _criterion, after, setup_step = (
                self._reachable_surfaces(seeded)[0]
            )
            # The guided setup resumes where the server says it left off, so
            # selecting a step to photograph means moving that resume point.
            if setup_step:
                self._set_setup_step(seeded['store'], setup_step)
            self._open(browser, path, wait, after)

            clean = json.loads(self._eval(browser, OVERFLOW_JS))
            self.assertFalse(
                self._clipping_defects(name, WIDTHS['mobile'], clean),
                'the control measurement must be clean before the injected '
                'defect means anything',
            )

            injected = self._eval(browser, r"""
(() => {
  const host = document.querySelector(
    ".o_sc_dashboard__inner, .o_sc_export_diff__inner, .o_sc_setup__inner"
  );
  if (!host) return "no connector surface on this page";
  const el = document.createElement("div");
  el.id = "sc-td016-probe";
  // Far wider than any viewport under test, and positioned so it extends
  // past the right edge of a surface whose ancestor HIDES the overflow.
  el.style.cssText = "width:4000px;height:24px;background:#f00";
  el.textContent = "TD-016 probe";
  host.appendChild(el);
  return "ok";
})()
""")
            self.assertEqual(injected, 'ok', injected)

            probed = json.loads(self._eval(browser, OVERFLOW_JS))
            defects = self._clipping_defects(name, WIDTHS['mobile'], probed)
            self.assertTrue(defects, (
                'the instrument did not report a 4000px element inside a '
                'surface whose ancestor hides overflow, so it cannot detect '
                'connector-owned clipping and a green result from it proves '
                'nothing (TD-016). Measured: %s'
                % json.dumps(probed.get('surfaces'), indent=2)
            ))
            self.assertTrue(
                any(entry['kind'] == 'clipped_content' for entry in defects),
                'the injected element was clipped away, so it must be '
                'reported as clipped content: %s' % json.dumps(defects)[:800],
            )
            # And the document total -- the ONLY thing the old instrument
            # looked at -- is unchanged, which is precisely why it could
            # never have caught this.
            self.assertLessEqual(
                probed['doc_scroll_width'], probed['inner_width'] + 1,
                'this probe is only meaningful while the ancestor absorbs '
                'the overflow; if the document itself grew, it is testing '
                'the old check rather than the new one',
            )

    def test_responsive_screenshots_and_no_horizontal_overflow(self):
        """Every U2/U3 surface, at all three widths, measured per surface.

        Two rules, and TD-016 is about the second one having been absent.

        The document rule (§10): the page body never scrolls horizontally.
        Wide content is the table's problem, not the document's. Measured
        from `documentElement.scrollWidth` against `innerWidth`.

        The surface rule: no connector-owned surface may be wider than the
        box it is rendered into without handling it, and nothing inside one
        may be rendered outside the region the user can actually see. The
        old instrument checked only the document total, and every Odoo
        backend surface sits inside `.o_content`, which is `overflow: auto`
        — so a connector panel 300px too wide was absorbed by that ancestor
        and contributed nothing to the number being asserted. The check
        could not fail for a connector-owned defect, which made a green
        result evidence of nothing.
        """
        seeded = self._seed()
        overflows = []
        clipping = []
        per_surface = {}
        with self._browser() as browser:
            for label, width in WIDTHS.items():
                self._viewport(browser, width)
                for name, path, wait, criterion, after, setup_step in (
                    self._reachable_surfaces(seeded)):
                    # The guided setup resumes where the server says it left off, so
                    # selecting a step to photograph means moving that resume point.
                    if setup_step:
                        self._set_setup_step(seeded['store'], setup_step)
                    self._open(browser, path, wait, after)
                    self._shoot(browser, '%s-%s-%dpx' % (name, label, width),
                                criterion)
                    metrics = json.loads(self._eval(browser, OVERFLOW_JS))
                    per_surface['%s@%dpx' % (name, width)] = {
                        'doc_scroll_width': metrics['doc_scroll_width'],
                        'inner_width': metrics['inner_width'],
                        'surfaces': [
                            {key: surface[key] for key in (
                                'cls', 'scroll_width', 'client_width',
                                'overflow_x', 'self_overflow',
                                'unhandled_self_overflow', 'clipped_by',
                                'clipped_silently', 'escapes_left',
                                'escapes_right', 'vertical_overflow',
                                'scrolls_vertically', 'vertical_reachable_by',
                                'unreachable_vertical',
                            )}
                            for surface in metrics.get('surfaces') or []
                        ],
                    }
                    # 1px of tolerance: sub-pixel layout rounding is not a
                    # horizontal scrollbar.
                    if metrics['doc_scroll_width'] > metrics['inner_width'] + 1:
                        overflows.append({
                            'surface': name, 'width': width,
                            'doc_scroll_width': metrics['doc_scroll_width'],
                            'inner_width': metrics['inner_width']})
                    clipping.extend(
                        self._clipping_defects(name, width, metrics)
                    )
        self._record('responsive',
                     {'widths': WIDTHS, 'overflows': overflows,
                      'clipping': clipping, 'measured': per_surface},
                     'DESIGN SYSTEM §10 responsive; §14 screenshot set; '
                     'TD-016 per-surface clipping')
        self.assertTrue(
            any(entry['surfaces'] for entry in per_surface.values()),
            'no connector-owned surface was measured at any width, so this '
            'instrument proved nothing (TD-016).',
        )
        self.assertFalse(
            overflows,
            'these surfaces scroll the page horizontally, which the design '
            'system forbids:\n%s' % json.dumps(overflows, indent=2))
        self.assertFalse(
            clipping,
            'these connector surfaces clip or hide their own content:\n%s'
            % json.dumps(clipping, indent=2))

    # ------------------------------------------------------------------
    # B2. The sticky setup action row (Wave 5)
    # ------------------------------------------------------------------

    #: The four widths the correction packet names for the action row. 1440 is
    #: measured HERE rather than added to `WIDTHS`: it matters for this one
    #: rule, and adding it to the global set would multiply every screenshot
    #: in the file by a third for surfaces where 1366 already proves the same
    #: thing.
    STICKY_WIDTHS = (1366, 1440, 768, 390)

    #: The setup steps whose content is long enough for the rule to be
    #: falsifiable at all. On a short step the bar is on screen whatever the
    #: stylesheet does, so measuring one would prove nothing.
    STICKY_STEPS = ('scopes', 'location_mapping', 'final_readiness')

    STICKY_JS = r"""
(() => {
  const bar = document.querySelector(".sc_setup__actions");
  if (!bar) return JSON.stringify({error: "no action row on this surface"});
  const surface = document.querySelector(".o_sc_setup");
  const rect = bar.getBoundingClientRect();
  // Every control in the row, and whether each is inside the viewport.
  const controls = Array.from(
    bar.querySelectorAll("button")
  ).map((el) => {
    const r = el.getBoundingClientRect();
    return {
      label: (el.textContent || "").trim().slice(0, 24),
      disabled: !!el.disabled,
      top: r.top, bottom: r.bottom, left: r.left, right: r.right,
      in_viewport:
        r.bottom <= window.innerHeight + 1 && r.top >= -1 &&
        r.right <= window.innerWidth + 1 && r.left >= -1,
      scroll_margin_block_end:
        parseFloat(getComputedStyle(el).scrollMarginBlockEnd) || 0,
    };
  });
  // WHERE THE BAR IS SUPPOSED TO BE PINNED.
  //
  // Not the viewport bottom. `position: sticky` pins to the bottom of the
  // nearest SCROLLPORT's padding box, and this surface carries its own
  // padding -- so the correct target is the scroll container's bottom edge
  // minus its bottom padding. Comparing against `innerHeight` reports the
  // surface's own padding as a defect, which is how a correct sticky bar
  // gets "fixed" into a wrong one.
  const scroller = (() => {
    for (let node = bar.parentElement; node; node = node.parentElement) {
      const cs = getComputedStyle(node);
      if (/auto|scroll/.test(cs.overflowY)) return node;
      if (node === document.body) break;
    }
    return document.scrollingElement;
  })();
  const sRect = scroller.getBoundingClientRect();
  const sPadBottom = parseFloat(getComputedStyle(scroller).paddingBottom) || 0;
  return JSON.stringify({
    error: null,
    position: getComputedStyle(bar).position,
    surface_direction: surface ? getComputedStyle(surface).direction : null,
    bar: {top: rect.top, bottom: rect.bottom, left: rect.left,
          right: rect.right, height: rect.height},
    scrollport: {
      cls: (scroller.className && String(scroller.className).split(/\s+/)[0])
           || scroller.tagName,
      bottom: sRect.bottom,
      padding_bottom: sPadBottom,
      pin_target: sRect.bottom - sPadBottom,
      extent: scroller.scrollHeight - scroller.clientHeight,
    },
    viewport: {width: window.innerWidth, height: window.innerHeight},
    document_scroll_width: document.documentElement.scrollWidth,
    // The page must not have grown sideways because of the row.
    horizontal_overflow:
      Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
    controls: controls,
  });
})()
"""

    #: Scroll the connector surface's own scroll container to the middle, so
    #: the measurement happens while there IS content above and below -- which
    #: is the only state in which "sticky" means anything.
    SCROLL_JS = r"""
(() => {
  // WHICH ELEMENT ACTUALLY SCROLLS, AND WHAT IT DID.
  //
  // Walked from the surface upwards, and every candidate is REPORTED --
  // including the ones that could not scroll. The first version returned only
  // the winner, which meant a run where nothing scrolled at all recorded
  // `from: 0, to: 0` and looked indistinguishable from a run where the
  // scroll was attempted and the page happened to already be at the middle.
  // A mid-scroll claim that was never mid-scroll is exactly the kind of
  // evidence this whole file exists to stop producing.
  const chain = [];
  let scroller = null;
  for (let node = document.querySelector(".o_sc_setup"); node;
       node = node.parentElement) {
    const cs = getComputedStyle(node);
    const extent = node.scrollHeight - node.clientHeight;
    const scrollable = /auto|scroll/.test(cs.overflowY) && extent > 4;
    chain.push({
      node: (node.className && String(node.className).split(/\s+/)[0])
            || node.tagName,
      overflow_y: cs.overflowY,
      extent: extent,
      scrollable: scrollable,
    });
    if (scrollable && !scroller) { scroller = node; }
    if (node === document.body) { break; }
  }
  const doc = document.scrollingElement;
  const docExtent = doc.scrollHeight - doc.clientHeight;
  if (!scroller && docExtent > 4) { scroller = doc; }
  if (!scroller) {
    return JSON.stringify({
      scroller: null, scrolled: false, chain: chain,
      doc_extent: docExtent,
      note: "nothing on this surface scrolls at this viewport",
    });
  }
  const before = scroller.scrollTop;
  scroller.scrollTop = Math.floor(
    (scroller.scrollHeight - scroller.clientHeight) / 2
  );
  return JSON.stringify({
    scroller: (scroller.className && String(scroller.className).split(/\s+/)[0])
              || scroller.tagName,
    scrolled: scroller.scrollTop > before,
    scrollable: scroller.scrollHeight - scroller.clientHeight,
    from: before,
    to: scroller.scrollTop,
    chain: chain,
    doc_extent: docExtent,
  });
})()
"""

    def _setup_surface_path(self):
        return ('/odoo/action-shopify_connector_core.'
                'action_shopify_connector_setup_wizard')

    def test_the_setup_action_row_stays_reachable_while_content_scrolls(self):
        """Back / Continue / Save & Exit stay on screen through long content.

        MEASURED, not read out of the stylesheet. `position: sticky` resolves
        against the nearest scrolling ancestor, and a surface that
        accidentally becomes its own scroll container silently stops being
        sticky while the CSS still says it is -- which is exactly the failure
        a stylesheet review cannot see. So this scrolls the real container to
        the middle of real content and reads the rendered rectangle back.

        WHAT "STICKY" IS ASSERTED AS, AND WHY IT IS NOT "SCROLLED TO THE
        MIDDLE". The scroll is attempted and what actually scrolled is
        recorded, but the assertion does not depend on it: when a surface's
        content extends below the viewport, a sticky bar's bottom edge sits
        exactly at the viewport's bottom edge, and a non-sticky bar's does
        not — it sits at the end of the content, below the fold. That
        equality is therefore the direct evidence, it holds at the top of a
        long page as well as mid-scroll, and it fails for the defect this
        exists to catch (a surface that accidentally becomes its own scroll
        container, which makes `position` still report `sticky` while the bar
        stops being lifted).

        Three of the four viewport widths the packet names carry no
        `prefers-reduced-motion` or RTL variation here; both are covered by
        the whole-surface loops that already include this surface.
        """
        seeded = self._seed()
        measured = {}
        failures = []
        with self._browser() as browser:
            for width in self.STICKY_WIDTHS:
                self._viewport(browser, width, 768 if width == 1366 else 900)
                for step in self.STICKY_STEPS:
                    self._set_setup_step(seeded['store'], step)
                    self._open(browser, self._setup_surface_path(),
                               '.o_sc_setup')
                    scroll = json.loads(self._eval(browser, self.SCROLL_JS))
                    self._eval(browser,
                               'new Promise(r => requestAnimationFrame('
                               '() => requestAnimationFrame(r)))')
                    payload = json.loads(self._eval(browser, self.STICKY_JS))
                    key = '%s@%dpx' % (step, width)
                    measured[key] = {**payload, 'scroll': scroll}
                    if payload.get('error'):
                        failures.append({'case': key,
                                         'why': payload['error']})
                        continue
                    self._shoot(browser, 's1-setup-%s-sticky-%dpx'
                                % (step.replace('_', '-'), width),
                                'Wave 5 sticky action row; §10 responsive, '
                                'SC 2.4.11 focus not obscured')
                    if payload['position'] != 'sticky':
                        failures.append({
                            'case': key, 'why': 'the action row is not sticky',
                            'position': payload['position'],
                        })
                    # THE DIRECT EVIDENCE that the bar is being LIFTED
                    # rather than merely declared sticky: while there is
                    # content still below it, its bottom edge sits at the
                    # scrollport's pin target. A bar that had stopped being
                    # lifted would be at the end of the content instead,
                    # hundreds of pixels lower. 2px of tolerance for
                    # sub-pixel layout rounding.
                    port = payload['scrollport']
                    still_below = (
                        port['extent'] - (scroll.get('to') or 0)
                    ) > 4
                    off_target = abs(
                        payload['bar']['bottom'] - port['pin_target']
                    ) > 2
                    if still_below and off_target:
                        failures.append({
                            'case': key,
                            'why': 'content remains below the fold but the '
                                   'action row is not pinned to the '
                                   'scrollport, so it is declared sticky and '
                                   'is not behaving so',
                            'bar_bottom': payload['bar']['bottom'],
                            'pin_target': port['pin_target'],
                            'scrollport': port['cls'],
                        })
                    for control in payload['controls']:
                        if control['disabled']:
                            continue
                        if not control['in_viewport']:
                            failures.append({
                                'case': key,
                                'why': 'an action control is off screen',
                                'control': control,
                            })
                        if control['scroll_margin_block_end'] <= 0:
                            failures.append({
                                'case': key,
                                'why': 'an action control reserves no scroll '
                                       'clearance, so keyboard focus can land '
                                       'under the bar',
                                'control': control,
                            })
                    if payload['horizontal_overflow'] > 1:
                        failures.append({
                            'case': key,
                            'why': 'the page scrolls horizontally',
                            'overflow': payload['horizontal_overflow'],
                        })
        self._record(
            'sticky-action-row',
            {'widths': list(self.STICKY_WIDTHS),
             'steps': list(self.STICKY_STEPS),
             'measured': measured, 'failures': failures},
            'Wave 5 sticky action row; DESIGN SYSTEM §10; WCAG 2.2 SC 2.4.11')
        self.assertTrue(measured, 'no sticky-bar case was measured at all')
        self.assertFalse(failures, (
            'the setup action row is not reachable in these cases:\n%s'
            % json.dumps(failures, indent=2)[:4000]))

    def test_focus_near_the_bottom_of_long_content_is_not_concealed(self):
        """SC 2.4.11: a focused control must not be hidden by the sticky bar.

        Focus is moved to the LAST focusable control inside the scrolling
        panel, the browser is allowed to scroll it into view, and the
        resulting rectangle is compared against the bar's. `scroll-margin` on
        the target is what is supposed to keep them apart; this is the
        measurement that proves it did.
        """
        seeded = self._seed()
        overlaps = []
        measured = {}
        skipped = []
        with self._browser() as browser:
            for width in (1366, 390):
                self._viewport(browser, width, 768 if width == 1366 else 900)
                for step in self.STICKY_STEPS:
                    self._set_setup_step(seeded['store'], step)
                    self._open(browser, self._setup_surface_path(),
                               '.o_sc_setup')
                    payload = json.loads(self._eval(browser, r"""
(() => {
  const panel = document.querySelector(".sc_setup__panel");
  const bar = document.querySelector(".sc_setup__actions");
  if (!panel || !bar) return JSON.stringify({error: "surface incomplete"});
  const focusables = Array.from(panel.querySelectorAll(
    "button:not([disabled]), a[href], input:not([disabled]), " +
    "select:not([disabled]), textarea:not([disabled])"
  )).filter((el) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  });
  if (!focusables.length) return JSON.stringify({error: "no focusable"});
  const target = focusables[focusables.length - 1];
  target.focus();
  target.scrollIntoView({block: "nearest"});
  const t = target.getBoundingClientRect();
  const b = bar.getBoundingClientRect();
  return JSON.stringify({
    error: null,
    focused: document.activeElement === target,
    label: (target.textContent || target.id || target.tagName).trim()
      .slice(0, 40),
    target: {top: t.top, bottom: t.bottom},
    bar: {top: b.top, bottom: b.bottom},
    // Positive means the focused control is underneath the bar.
    concealed_by: Math.max(0, Math.min(t.bottom, b.bottom) - Math.max(t.top, b.top)),
    in_viewport: t.bottom <= window.innerHeight + 1 && t.top >= -1,
  });
})()
"""))
                    key = '%s@%dpx' % (step, width)
                    measured[key] = payload
                    if payload.get('error') == 'no focusable':
                        # A read-only step (Permissions is a list, not a form)
                        # genuinely has no focusable control inside the
                        # scrolling panel. Recorded rather than passed over in
                        # silence, and bounded by the assertion below, so this
                        # cannot quietly become "every case skipped".
                        skipped.append(key)
                        continue
                    self.assertIsNone(
                        payload.get('error'),
                        'the setup surface did not render for %s' % key)
                    self.assertTrue(
                        payload['focused'],
                        'the probe control did not take focus in %s' % key)
                    if payload['concealed_by'] > 1:
                        overlaps.append({'case': key, **payload})
                    if not payload['in_viewport']:
                        overlaps.append({'case': key, 'why': 'off screen',
                                         **payload})
                    self._shoot(browser, 's1-setup-%s-focus-bottom-%dpx'
                                % (step.replace('_', '-'), width),
                                'WCAG 2.2 SC 2.4.11 focus not obscured by the '
                                'sticky action row')
        self._record(
            'sticky-focus-clearance',
            {'measured': measured, 'overlaps': overlaps,
             'skipped_no_focusable_control': skipped},
            'WCAG 2.2 SC 2.4.11 Focus Not Obscured (Minimum)')
        measured_cases = [
            key for key, value in measured.items() if not value.get('error')
        ]
        self.assertGreaterEqual(
            len(measured_cases), 4,
            'only %d focus-clearance cases actually measured a control '
            '(skipped: %s); the check is too thin to mean anything'
            % (len(measured_cases), skipped))
        self.assertFalse(overlaps, (
            'a focused control is concealed by the sticky action row:\n%s'
            % json.dumps(overlaps, indent=2)[:4000]))

    # ------------------------------------------------------------------
    # C. RTL
    # ------------------------------------------------------------------

    def test_rtl_renders_mirrored_without_overflow(self):
        """A real RTL locale, rendered -- not logical CSS properties, read.

        The stylesheets use logical properties throughout, which is the right
        implementation. This proves the result: `direction: rtl` actually
        reaches the document, and the surfaces still fit.

        BATCH 2 EVIDENCE CLOSURE (2026-07-31): PER SURFACE, PER WIDTH. This
        used to accept the campaign on `any(...)`: one row anywhere in the run
        showing Odoo's flipped bundle, and one row anywhere showing `.o_rtl`,
        satisfied the whole matrix. Every individual surface could therefore
        have been photographed in a session that was not in RTL at all and the
        test would have passed on its neighbours' evidence. Each row now
        carries its own proof, taken while that exact surface was on screen:

          * the INTENDED surface is present and visible -- not `.o_form_view`,
            which is true of every form in the product;
          * Odoo's own `.o_rtl` class is applied to this page;
          * Odoo served at least one rtlcss bundle for this page;
          * where the connector owns a root with its own stylesheet, that root
            computes `direction: rtl`. Where it does not -- the Batch 2 form
            surfaces and both dialogs -- the row says so explicitly rather
            than borrowing an Owl surface's direction from another row.
        """
        seeded = self._seed()
        lang = self.env['res.lang'].sudo()._activate_lang('ar_001') \
            or self.env['res.lang'].sudo()._activate_lang('ar_SY')
        self.assertTrue(
            lang, 'no Arabic locale is available in this build, so the RTL '
                  'check cannot be performed; do not record it as passed')
        self.assertEqual(lang.direction, 'rtl')
        self.user.sudo().write({'lang': lang.code})
        self.env.flush_all()

        overflows, measured, connector_roots = [], {}, {}
        clipping = []
        rows, unproved = [], []
        with self._browser() as browser:
            # TD-016: RTL is measured at every required width, not only at
            # desktop. A mirrored layout fails by pushing content off the
            # OPPOSITE edge, and the narrow viewports are where it does it.
            for label, width in WIDTHS.items():
                self._viewport(browser, width)
                for name, path, wait, criterion, after, setup_step in (
                    self._reachable_surfaces(seeded)
                ):
                    # The guided setup resumes where the server says it left off, so
                    # selecting a step to photograph means moving that resume point.
                    if setup_step:
                        self._set_setup_step(seeded['store'], setup_step)
                    self._open(browser, path, wait, after)
                    self._shoot(browser, '%s-rtl-%dpx' % (name, width),
                                criterion + ' (RTL, SC 1.3.2 / §10)')
                    metrics = json.loads(self._eval(browser, OVERFLOW_JS))
                    measured['%s@%dpx' % (name, width)] = metrics
                    if metrics['connector_direction']:
                        connector_roots[name] = metrics['connector_direction']
                    surface_overflow = max(
                        0,
                        metrics['doc_scroll_width'] - metrics['inner_width'] - 1,
                    )
                    if surface_overflow:
                        overflows.append({
                            'surface': name, 'width': width,
                            'doc_scroll_width': metrics['doc_scroll_width'],
                            'inner_width': metrics['inner_width']})
                    row_clipping = self._clipping_defects(name, width, metrics)
                    clipping.extend(row_clipping)

                    # The intended surface, proved present while it is the one
                    # on screen. Batch 2 surfaces have a surface-specific
                    # marker; everything else is proved by the selector the
                    # capture itself waited for -- and where a post-open
                    # ACTION was run, that action's own wait selector is the
                    # honest one. Four surfaces in this set are reached by
                    # pressing a control, and one of them (the S7 diff)
                    # replaces the form it was opened from, so `wait` names a
                    # screen that is deliberately no longer there.
                    intended = BATCH2_SURFACE_SELECTORS.get(name) or (
                        after[1] if after else wait)
                    presence = json.loads(self._eval(
                        browser, SURFACE_PRESENT_JS % json.dumps(intended)))
                    owl_roots = [
                        entry for entry in metrics.get('connector_roots') or []
                        if entry['owl'] and entry['visible']
                    ]
                    marked_roots = [
                        entry for entry in metrics.get('connector_roots') or []
                        if not entry['owl'] and entry['visible']
                    ]
                    row = {
                        'surface': name,
                        'width': width,
                        'viewport': '%s (%dpx)' % (label, width),
                        'intended_selector': intended,
                        'intended_visible': presence['visible'],
                        'odoo_rtl_class': metrics['odoo_rtl_class'],
                        'rtl_stylesheets': metrics['rtl_stylesheets'],
                        'owl_roots': owl_roots,
                        'marked_roots': marked_roots,
                        'connector_owns_a_directional_root': bool(owl_roots),
                        'page_horizontal_overflow': surface_overflow,
                        'measured_surface_count': len(metrics['surfaces']),
                        'clipping': row_clipping,
                    }
                    reasons = []
                    if not presence['visible']:
                        reasons.append(
                            'the intended surface %r is not visible, so this '
                            'row is about some other screen' % intended)
                    if not metrics['odoo_rtl_class']:
                        reasons.append(
                            'Odoo applied no `.o_rtl` class on this page')
                    if not metrics['rtl_stylesheets']:
                        reasons.append(
                            'Odoo served no rtlcss bundle for this page')
                    wrong_owl = [
                        entry for entry in owl_roots
                        if entry['direction'] != 'rtl'
                    ]
                    if wrong_owl:
                        reasons.append(
                            'connector Owl root(s) did not resolve '
                            'right-to-left: %s' % json.dumps(wrong_owl))
                    row['verdict'] = 'PASS' if not reasons else 'FAIL'
                    row['unproved_because'] = reasons
                    rows.append(row)
                    if reasons:
                        unproved.append(row)
        self._record(
            'rtl',
            {'lang': lang.code,
             'note': 'Odoo 19 backend sets no `dir` on <html>/<body>; its RTL '
                     'mechanism is rtlcss bundle flipping. The connector '
                     'stylesheets use logical properties, which resolve '
                     'against `direction`, so the meaningful measurement on '
                     'an Owl surface is the connector surface root. The '
                     'Batch 2 surfaces are ordinary Odoo form views: the '
                     'connector owns their arch and not their chrome, Odoo '
                     'mirrors them through the flipped bundle, and no layer '
                     'of this repository sets `direction` on them. Their '
                     'marked roots are measured for direction and RECORDED; '
                     'what is ASSERTED for those rows is the signal that '
                     'actually carries RTL for them -- `.o_rtl`, a served '
                     'rtlcss bundle, and a mirrored layout that clips '
                     'nothing -- taken while that exact surface was visible.',
             'widths': WIDTHS,
             'per_surface_rows': rows,
             'per_surface_unproved': unproved,
             'batch2_surfaces': list(BATCH2_CHANGED_SURFACES),
             'measured': measured, 'overflows': overflows,
             'clipping': clipping},
            'DESIGN SYSTEM §10 RTL check at every required width (V-8), '
            'proved per surface row; TD-016 per-surface clipping')

        self.assertTrue(measured, 'no surface was measured')
        # EVERY ROW CARRIES ITS OWN PROOF. `any(...)` over the run used to
        # stand in for this, which let one surface's evidence acquit another's.
        self.assertFalse(
            unproved,
            'these RTL rows are recorded against a surface with nothing '
            'measured, while that surface was on screen, to show the page was '
            'actually right-to-left:\n%s'
            % json.dumps(unproved, indent=2)[:6000])
        # The Batch 2 surfaces are named explicitly: a row that silently
        # stopped being produced would otherwise pass by being absent.
        for surface in BATCH2_CHANGED_SURFACES:
            surface_rows = [row for row in rows if row['surface'] == surface]
            self.assertEqual(
                len(surface_rows), len(WIDTHS),
                'the RTL matrix produced %d rows for %s, not one per required '
                'width' % (len(surface_rows), surface))
            for row in surface_rows:
                self.assertGreaterEqual(
                    len(row['marked_roots']), 1,
                    'no connector-owned root was visible on %s at %dpx in '
                    'RTL, so the mirrored layout of the surface this row '
                    'names was never measured: %s'
                    % (surface, row['width'], json.dumps(row)[:1500]))
        # And the connector's own Owl surfaces mirror, which is the part this
        # repository owns and the part logical properties depend on.
        self.assertTrue(
            connector_roots,
            'no connector Owl surface was reached, so the one direction this '
            'repository controls was never measured',
        )
        wrong = {k: v for k, v in connector_roots.items() if v != 'rtl'}
        self.assertFalse(
            wrong,
            'these connector surface roots did not resolve right-to-left, so '
            'every logical property in their stylesheet resolved LTR-ward: %s'
            % wrong)
        self.assertFalse(
            overflows,
            'these surfaces overflow horizontally in RTL:\n%s'
            % json.dumps(overflows, indent=2))
        self.assertFalse(
            clipping,
            'these connector surfaces clip or displace their own content '
            'when mirrored:\n%s' % json.dumps(clipping, indent=2))

    # ------------------------------------------------------------------
    # D. Reduced motion
    # ------------------------------------------------------------------

    def test_reduced_motion_removes_every_transition(self):
        """Rendered under the media query, not read out of the stylesheet.

        Every connector transition is written behind
        `prefers-reduced-motion: no-preference`, so the reduced-motion default
        should be no animation at all. This emulates the media feature and
        reads the COMPUTED durations back: a rule that was written correctly
        but never applied is indistinguishable from one that was not written,
        until something renders it.
        """
        seeded = self._seed()
        moving, matched = [], {}
        with self._browser() as browser:
            self._viewport(browser, WIDTHS['desktop'])
            self._emulate_reduced_motion(browser, True)
            for name, path, wait, criterion, after, setup_step in (
                    self._reachable_surfaces(seeded)):
                # The guided setup resumes where the server says it left off, so
                # selecting a step to photograph means moving that resume point.
                if setup_step:
                    self._set_setup_step(seeded['store'], setup_step)
                self._open(browser, path, wait, after)
                payload = json.loads(self._eval(browser, MOTION_JS))
                matched[name] = payload['reduced_motion_matches']
                for entry in payload['moving']:
                    moving.append({'surface': name, **entry})
                self._shoot(browser, '%s-reduced-motion-1366px' % name,
                            criterion + ' (prefers-reduced-motion: reduce; '
                                        'SC 2.3.3)')
        self._record('reduced-motion',
                     {'media_query_matched': matched, 'still_moving': moving},
                     'DESIGN SYSTEM §8 reduced motion (V-7); WCAG 2.2 SC 2.3.3')

        self.assertTrue(all(matched.values()),
                        'the reduced-motion media query did not reach the '
                        'page, so this measured nothing: %s' % matched)
        # Connector-owned elements only. Upstream Odoo chrome is not this
        # repository's to fix, and failing on it would make the check useless.
        ours = [m for m in moving
                if 'sc-' in m['selector'] or 'o_sc_' in m['selector']]
        self.assertFalse(
            ours,
            'these connector elements still animate under '
            'prefers-reduced-motion: reduce:\n%s' % json.dumps(ours, indent=2))

    # ------------------------------------------------------------------
    # E. Keyboard and visible focus
    # ------------------------------------------------------------------

    def test_every_actionable_control_shows_a_visible_focus_indicator(self):
        """`:focus-visible` FORCED, then the rendered indicator measured.

        A tour cannot assert this: in headless Chromium a script-focused
        button never matches `:focus-visible`, because the pseudo-class tracks
        real input modality. `CSS.forcePseudoState` takes the heuristic out of
        the question, so what is measured is the indicator the STYLESHEET
        defines, which is the thing under test.
        """
        seeded = self._seed()
        without, small, results = [], [], []
        with self._browser() as browser:
            browser._websocket_request('DOM.enable')
            browser._websocket_request('CSS.enable')
            self._viewport(browser, WIDTHS['desktop'])
            for name, path, wait, criterion, after, setup_step in (
                    self._reachable_surfaces(seeded)):
                # The guided setup resumes where the server says it left off, so
                # selecting a step to photograph means moving that resume point.
                if setup_step:
                    self._set_setup_step(seeded['store'], setup_step)
                self._open(browser, path, wait, after)
                controls = json.loads(self._eval(browser, FOCUSABLES_JS))
                for control in controls:
                    node = browser._websocket_request(
                        'DOM.getDocument', params={'depth': 0})
                    root_id = node['root']['nodeId']
                    found = browser._websocket_request(
                        'DOM.querySelector',
                        params={'nodeId': root_id,
                                'selector': control['selector']})
                    node_id = found.get('nodeId')
                    if not node_id:
                        continue
                    browser._websocket_request(
                        'CSS.forcePseudoState',
                        params={'nodeId': node_id,
                                'forcedPseudoClasses': ['focus', 'focus-visible']})
                    measured = json.loads(self._eval(
                        browser, _focus_indicator_js(control['selector'])))
                    browser._websocket_request(
                        'CSS.forcePseudoState',
                        params={'nodeId': node_id, 'forcedPseudoClasses': []})
                    if measured.get('error'):
                        continue
                    entry = {'surface': name, **control, **measured}
                    results.append(entry)
                    if not measured['has_indicator']:
                        without.append(entry)
                    # SC 2.5.8 target size, checked while we are here.
                    if control['width'] < 24 or control['height'] < 24:
                        small.append(entry)
                if controls:
                    self._shoot(browser, '%s-focus-1366px' % name,
                                criterion + ' (focus visible; SC 2.4.7)')
        self._record('focus-visible',
                     {'measured': results, 'without_indicator': without,
                      'below_24px_target': small},
                     'WCAG 2.2 SC 2.4.7 Focus Visible; SC 2.5.8 Target Size')

        self.assertTrue(results, 'no focusable control was measured at all')
        # Filter on the element's REAL classes, not on `selector`: the probe
        # attribute is itself named `data-sc-focus-probe`, so matching "sc-"
        # against the selector matched every control on the page, including
        # Odoo's own search input.
        ours = [e for e in without
                if 'sc-' in e.get('classes', '') or 'o_sc_' in e.get('classes', '')]
        self.assertFalse(
            ours,
            'these connector controls render no focus indicator when focused '
            '(SC 2.4.7):\n%s' % json.dumps(ours, indent=2)[:4000])

    # ------------------------------------------------------------------
    # F. Contrast
    # ------------------------------------------------------------------

    def test_measured_contrast_meets_wcag_22_aa(self):
        """Ratios computed from RENDERED colour, against the AA thresholds.

        SC 1.4.3 Contrast (Minimum): >= 4.5:1 ordinary text, >= 3:1 large
        text. SC 1.4.11 Non-text Contrast: >= 3:1 for the boundary of a
        meaningful UI component.

        Backgrounds are resolved up the ancestor chain and alpha-composited
        before the ratio is taken. A table computed against `rgba(0,0,0,0)` is
        the usual way this measurement lies, and it always lies optimistically.
        """
        seeded = self._seed()
        rows, failures = [], []
        with self._browser() as browser:
            self._viewport(browser, WIDTHS['desktop'])
            for name, path, wait, criterion, after, setup_step in (
                    self._reachable_surfaces(seeded)):
                # The guided setup resumes where the server says it left off, so
                # selecting a step to photograph means moving that resume point.
                if setup_step:
                    self._set_setup_step(seeded['store'], setup_step)
                self._open(browser, path, wait, after)
                for entry in json.loads(self._eval(browser, CONTRAST_JS)):
                    entry['surface'] = name
                    entry['pass'] = entry['ratio'] >= entry['required']
                    rows.append(entry)
                    if not entry['pass']:
                        failures.append(entry)
        self._record(
            'contrast',
            {'thresholds': {'text': CONTRAST_TEXT,
                            'large_text': CONTRAST_LARGE_TEXT,
                            'non_text': CONTRAST_NON_TEXT},
             'criteria': ['WCAG 2.2 SC 1.4.3 Contrast (Minimum)',
                          'WCAG 2.2 SC 1.4.11 Non-text Contrast'],
             'method': 'rendered getComputedStyle colours, background '
                       'resolved up the ancestor chain and alpha-composited; '
                       'relative luminance per WCAG 2.2 definition',
             'measured': rows, 'failures': failures},
            'WCAG 2.2 SC 1.4.3 / SC 1.4.11')

        self.assertTrue(rows, 'no contrast pair was measured at all')
        # Connector-owned selectors only: the Odoo chrome around the surface
        # is not this repository's to restyle.
        ours = [f for f in failures
                if 'sc-' in f['selector'] or 'o_sc_' in f['selector']]
        self.assertFalse(
            ours,
            'these connector pairs are below their WCAG 2.2 AA threshold:\n%s'
            % json.dumps(ours, indent=2)[:4000])

    # ==================================================================
    # E. BATCH 1 UI COMPLETION (2026-07-30)
    #
    # The three dimensions the previous campaign never measured, on the
    # surfaces the Batch 1 correction changed: enlargement, sequential
    # keyboard traversal, and what a screen reader is told.
    # ==================================================================

    def _changed_surfaces(self, seeded):
        """The Batch 1 surfaces, resolved, with the set proved complete."""
        reachable = {
            entry[0]: entry for entry in self._reachable_surfaces(seeded)
        }
        missing = [
            name for name in CHANGED_SURFACES if name not in reachable
        ]
        self.assertFalse(
            missing,
            'these changed surfaces are not in the capture set, so the '
            'campaign would silently cover less than it claims: %s' % missing,
        )
        return [reachable[name] for name in CHANGED_SURFACES]

    def _zoom_viewport(self, browser, css_width, height=900):
        """Emulate browser zoom the way a browser does it.

        Enlargement is a LAYOUT event: the CSS viewport narrows and every CSS
        pixel is painted larger. `deviceScaleFactor` alone changes only the
        painting, so a "200% zoom" test built on it measures nothing that
        SC 1.4.4 or SC 1.4.10 is about. The caller passes the CSS width that
        results from the zoom, and this sets the matching device scale so the
        rendering is genuinely enlarged rather than merely reflowed.
        """
        browser._websocket_request('Emulation.setDeviceMetricsOverride', params={
            'width': css_width, 'height': height,
            'deviceScaleFactor': ZOOM_FACTOR, 'mobile': css_width <= 480,
        })

    def _tab(self, browser):
        """One REAL Tab press, at the browser's input layer.

        A dispatched `KeyboardEvent` does not move focus: sequential focus
        navigation is the browser's own behaviour and is not driven by DOM
        events. `Input.dispatchKeyEvent` is, which is the difference between
        testing the tab order and testing a loop that walks the DOM in source
        order and calls it the tab order.
        """
        self._key(browser, 'Tab', vk=9)

    def test_the_changed_surfaces_reflow_at_two_hundred_percent_zoom(self):
        """Every Batch 1 surface, enlarged, in both directions, measured.

        WHY THIS IS A SEPARATE TEST AND NOT A FOURTH WIDTH. Zoom is not a
        narrower device: the viewport narrows AND the type gets larger, so the
        same layout has less room for more ink. A surface that fits 390px at
        100% can fail 683px at 200%, because at 200% the 683px holds the
        content of a 341px column at normal size. That is the case SC 1.4.4
        and SC 1.4.10 exist for and the one this campaign had no measurement
        of at all.

        THE 320px FLOOR. SC 1.4.10 specifies reflow at 320 CSS px, and no
        success criterion applies below it, so the mobile row is measured at
        the floor rather than at 195px -- a width no browser lays out for and
        no criterion requires.

        Reduced motion is carried as a column and measured in one LTR pass:
        it cannot change layout, and the computed transition and animation
        durations it CAN change are asserted by
        `test_reduced_motion_removes_every_transition`. Recording it without
        varying it would be a column that means nothing.
        """
        seeded = self._seed()
        rtl_lang = self.env['res.lang'].sudo()._activate_lang('ar_001') \
            or self.env['res.lang'].sudo()._activate_lang('ar_SY')
        self.assertTrue(
            rtl_lang, 'no Arabic locale is available in this build, so the '
                      'RTL half of the zoom matrix cannot be performed; do '
                      'not record it as passed')
        rows, failures = [], []
        for direction, code in (('ltr', 'en_US'), ('rtl', rtl_lang.code)):
            self.user.sudo().write({'lang': code})
            self.env.flush_all()
            motions = ('no-preference', 'reduce') if direction == 'ltr' \
                else ('no-preference',)
            with self._browser() as browser:
                for motion in motions:
                    self._emulate_reduced_motion(browser, motion == 'reduce')
                    for label, device_width in WIDTHS.items():
                        css_width = max(device_width // ZOOM_FACTOR,
                                        REFLOW_FLOOR_PX)
                        self._zoom_viewport(browser, css_width)
                        for (name, path, wait, criterion, after,
                             setup_step) in self._changed_surfaces(seeded):
                            if setup_step:
                                self._set_setup_step(seeded['store'],
                                                     setup_step)
                            self._open(browser, path, wait, after)
                            metrics = json.loads(
                                self._eval(browser, OVERFLOW_JS))
                            last = json.loads(
                                self._eval(browser, LAST_CONTROL_JS))
                            defects = self._clipping_defects(
                                name, css_width, metrics)
                            page_overflow = max(
                                0,
                                metrics['doc_scroll_width']
                                - metrics['inner_width'] - 1,
                            )
                            if page_overflow:
                                defects.append({
                                    'kind': 'page_scrolls_horizontally',
                                    'surface': name,
                                    'overflow': page_overflow,
                                })
                            if last.get('error'):
                                defects.append({
                                    'kind': 'no_actionable_control',
                                    'surface': name, 'why': last['error'],
                                })
                            elif not last['reachable']:
                                defects.append({
                                    'kind': 'final_control_unreachable',
                                    'surface': name,
                                    'control': last['selector'],
                                    'rect': last['rect'],
                                    'viewport': last['viewport'],
                                })
                            row = {
                                'surface': name,
                                'selector': wait,
                                'device_width': device_width,
                                'css_viewport_width': css_width,
                                'viewport': '%s (%dpx device)'
                                            % (label, device_width),
                                'direction': direction,
                                # PROOF the direction took effect, not just
                                # the value we asked for. `connector_direction`
                                # is null on a surface with no `o_sc_*` root
                                # (the inventory forms and both dialogs), so
                                # Odoo's own RTL signals are carried too --
                                # otherwise an RTL row for those surfaces
                                # would be a label with nothing behind it.
                                'measured_direction':
                                    metrics.get('connector_direction'),
                                'odoo_rtl_class': metrics.get('odoo_rtl_class'),
                                'rtl_stylesheets':
                                    metrics.get('rtl_stylesheets'),
                                'zoom': '%d%%' % (ZOOM_FACTOR * 100),
                                'motion': motion,
                                'connector_surfaces': [
                                    {'cls': surface['cls'],
                                     'scroll_width': surface['scroll_width'],
                                     'client_width': surface['client_width'],
                                     'self_overflow': surface['self_overflow'],
                                     'unhandled_self_overflow':
                                         surface['unhandled_self_overflow'],
                                     'vertical_overflow':
                                         surface['vertical_overflow'],
                                     'vertical_reachable_by':
                                         surface['vertical_reachable_by'],
                                     'unreachable_vertical':
                                         surface['unreachable_vertical'],
                                     'clipped_by': surface['clipped_by'],
                                     'clipped_silently':
                                         surface['clipped_silently']}
                                    for surface in metrics['surfaces']
                                ],
                                'page': {
                                    'doc_scroll_width':
                                        metrics['doc_scroll_width'],
                                    'inner_width': metrics['inner_width'],
                                    'horizontal_overflow': page_overflow,
                                },
                                'final_control': last,
                                'defects': defects,
                                'verdict': 'PASS' if not defects else 'FAIL',
                            }
                            rows.append(row)
                            if defects:
                                failures.append(row)
                            self._shoot(
                                browser,
                                '%s-%s-zoom200-%dpx-css%d' % (
                                    name, direction, device_width, css_width),
                                criterion + ' (200%% zoom, %s, %s motion; '
                                            'SC 1.4.4 / SC 1.4.10)'
                                % (direction.upper(), motion))
        self.user.sudo().write({'lang': 'en_US'})
        self.env.flush_all()
        self._record(
            'changed-surfaces-zoom-matrix',
            {'zoom': '%d%%' % (ZOOM_FACTOR * 100),
             'reflow_floor_px': REFLOW_FLOOR_PX,
             'device_widths': WIDTHS,
             'surfaces': list(CHANGED_SURFACES),
             'batch1_surfaces': list(BATCH1_CHANGED_SURFACES),
             'batch2_surfaces': list(BATCH2_CHANGED_SURFACES),
             'criteria': ['WCAG 2.2 SC 1.4.4 Resize Text',
                          'WCAG 2.2 SC 1.4.10 Reflow',
                          'DESIGN SYSTEM §10 responsive'],
             'rows': rows, 'failures': failures},
            'Batch 1 and Batch 2 surfaces at 200% zoom, LTR and RTL; '
            'SC 1.4.4 / 1.4.10')
        self.assertEqual(
            len(rows),
            len(CHANGED_SURFACES) * len(WIDTHS) * 3,
            'the zoom matrix did not measure every planned combination',
        )
        # An RTL row that cannot show the page was in RTL is a label, not
        # evidence. Odoo's backend sets no `dir` on <html>, so the signals
        # are its flipped bundles and `.o_rtl`; the connector root's computed
        # `direction` is the third and exists only where there is one.
        unproved = [
            {'surface': row['surface'],
             'css_viewport_width': row['css_viewport_width'],
             'measured_direction': row['measured_direction'],
             'odoo_rtl_class': row['odoo_rtl_class'],
             'rtl_stylesheets': row['rtl_stylesheets']}
            for row in rows
            if row['direction'] == 'rtl'
            and row['measured_direction'] != 'rtl'
            and not row['odoo_rtl_class']
            and not row['rtl_stylesheets']
        ]
        self.assertFalse(
            unproved,
            'these rows are recorded as RTL with nothing measured to show '
            'the page rendered right-to-left:\n%s'
            % json.dumps(unproved, indent=2)[:3000])
        self.assertFalse(
            failures,
            'these changed surfaces are not usable at 200%% zoom:\n%s'
            % json.dumps(failures, indent=2)[:6000])

    def test_keyboard_alone_reaches_the_final_control_on_every_changed_surface(self):
        """Sequential focus navigation, driven at the browser input layer.

        `focusStep` in the tours proves a control CAN take focus when it is
        focused. That is not the same claim: a control can be focusable and
        still be unreachable by Tab, and focus can be lost to the document
        part way along, which strands a keyboard user in the middle of a
        surface with no way forward. Both are measured here by pressing Tab
        for real -- a dispatched `KeyboardEvent` does not move focus at all,
        so a test built on one would pass on a surface with no tab order.

        Recorded per surface: the traversal length, every element focus
        landed on, whether the final actionable control was reached, and
        whether focus was ever lost to `<body>` before it was.
        """
        seeded = self._seed()
        rows, failures = [], []
        with self._browser() as browser:
            self._viewport(browser, WIDTHS['desktop'])
            for (name, path, wait, criterion, after,
                 setup_step) in self._changed_surfaces(seeded):
                if setup_step:
                    self._set_setup_step(seeded['store'], setup_step)
                self._open(browser, path, wait, after)
                target = json.loads(self._eval(browser, LAST_CONTROL_JS))
                if target.get('error'):
                    failures.append({'surface': name, 'why': target['error']})
                    continue
                # Start from the document, exactly where a keyboard user
                # arrives, rather than from somewhere convenient.
                self._eval(browser, 'document.activeElement.blur(); true')
                visited, reached, lost = [], False, 0
                for _step in range(MAX_TAB_PRESSES):
                    self._tab(browser)
                    seen = json.loads(self._eval(browser, ACTIVE_ELEMENT_JS))
                    visited.append(seen)
                    if seen['is_body']:
                        # Wrapping past the end of the document is normal;
                        # landing on the body BEFORE the target has been
                        # reached is focus loss.
                        lost += 1
                        if lost > 1:
                            break
                        continue
                    if seen['matches_target']:
                        reached = True
                        break
                row = {
                    'surface': name,
                    'selector': wait,
                    'viewport': 'desktop (1366px device)',
                    'direction': 'ltr',
                    'zoom': '100%',
                    'motion': 'no-preference',
                    'target': target['selector'],
                    'presses': len(visited),
                    'reached': reached,
                    'focus_lost_to_body_before_target': lost,
                    'path': [v['selector'] for v in visited],
                    'concealed': [
                        v for v in visited
                        if not v['is_body'] and not v['visible']
                    ],
                    'verdict': 'PASS' if reached else 'FAIL',
                }
                _logger.info(
                    'CONNECTOR-KEYBOARD %s target=%s presses=%d reached=%s '
                    'lost=%d path=%s',
                    name, target['selector'], len(visited), reached, lost,
                    ' > '.join(v['selector'] for v in visited[-12:]))
                rows.append(row)
                if not reached:
                    failures.append(row)
                elif row['concealed']:
                    # Focus that lands on something the user cannot see is
                    # SC 2.4.11's failure, and it is silent.
                    row['verdict'] = 'FAIL'
                    failures.append(row)
        self._record(
            'changed-surfaces-keyboard-traversal',
            {'max_presses': MAX_TAB_PRESSES,
             'method': 'CDP Input.dispatchKeyEvent Tab; real sequential focus '
                       'navigation, not a DOM-order walk',
             'criteria': ['WCAG 2.2 SC 2.1.1 Keyboard',
                          'WCAG 2.2 SC 2.4.3 Focus Order',
                          'WCAG 2.2 SC 2.4.11 Focus Not Obscured'],
             'surfaces': list(CHANGED_SURFACES),
             'batch1_surfaces': list(BATCH1_CHANGED_SURFACES),
             'batch2_surfaces': list(BATCH2_CHANGED_SURFACES),
             'rows': rows, 'failures': failures},
            'Batch 1 and Batch 2 surfaces traversed by keyboard alone; '
            'SC 2.1.1 / 2.4.3')
        self.assertEqual(
            len(rows), len(CHANGED_SURFACES),
            'the keyboard traversal did not cover every changed surface',
        )
        self.assertFalse(
            failures,
            'keyboard-only navigation fails on these surfaces:\n%s'
            % json.dumps(failures, indent=2)[:6000])

    def test_live_regions_announce_what_changes_and_note_stays_static(self):
        """What a screen reader is TOLD, measured rather than declared.

        Three claims, each falsifiable:

        1. The credential step's guidance band is `role="status"` -- a polite
           live region -- and it EARNS that role: its text really does change
           when the operator switches authentication path, so a document
           role would announce nothing at the moment the guidance silently
           became different guidance. Both halves are measured; a live region
           whose content never changes is noise, and a changing region with a
           document role is silence.
        2. The withdrawal dialog's `role="note"` band earns ITS role the
           opposite way: the text is identical before and after the operator
           fills the dialog in, so it is document structure and not a live
           region. WAI-ARIA 1.2 lists the live-region roles as alert, log,
           marquee, status and timer; `note` is deliberately not among them.
           Odoo's own view validator warns about the `alert-*` class without
           a live-region role, and this is the recorded answer: the class is
           presentational, the copy is static, and promoting it to `status`
           would announce a sentence nothing changed about.
        3. A refused submission is ANNOUNCED and ATTRIBUTED: the empty
           required field carries `aria-invalid`, and the refusal reaches a
           live region rather than only a red border.
        """
        seeded = self._seed()
        findings = {}
        with self._browser() as browser:
            self._viewport(browser, WIDTHS['desktop'])

            # 1. A live region that earns the role.
            self._set_setup_step(seeded['store'], 'credential')
            self._open(browser, self._setup_surface_path(), '.o_sc_setup')
            findings['credential_default'] = json.loads(
                self._eval(browser, LIVE_REGION_JS % json.dumps('.o_sc_setup')))
            self._eval(browser, CREDENTIAL_OFFLINE_JS, timeout=90.0)
            findings['credential_offline'] = json.loads(
                self._eval(browser, LIVE_REGION_JS % json.dumps('.o_sc_setup')))

            # 2. The `note` band, which lives on the SINGLE-PAIR dialog,
            # before and after the operator fills the dialog in.
            dialog = '.modal:not(.o_inactive_modal)'
            pair_path = ('/odoo/action-shopify_connector_inventory.'
                         'action_shopify_connector_inventory_first_push/%d'
                         % seeded['level'].id)
            self._open(browser, pair_path, '.o_form_view',
                       (_open_dialog_js('Withdraw First Push'),
                        '%s .o_form_view' % dialog))
            findings['pair_dialog_opened'] = json.loads(
                self._eval(browser, LIVE_REGION_JS % json.dumps(dialog)))
            self._eval(browser, TYPE_REASON_JS, timeout=90.0)
            findings['pair_dialog_filled'] = json.loads(
                self._eval(browser, LIVE_REGION_JS % json.dumps(dialog)))
            self._dismiss_dialogs(browser)

            # 3. The refusal, on the mapping-level dialog.
            path = ('/odoo/action-shopify_connector_inventory.'
                    'action_shopify_connector_location_mapping/%d'
                    % seeded['mapping'].id)
            self._open(browser, path, '.o_form_view',
                       (_open_dialog_js('Withdraw First Pushes'),
                        '%s .o_form_view' % dialog))
            findings['dialog_opened'] = json.loads(
                self._eval(browser, LIVE_REGION_JS % json.dumps(dialog)))
            findings['refusal'] = json.loads(
                self._eval(browser, INVALID_SUBMIT_JS, timeout=90.0))
            self._dismiss_dialogs(browser)

        self._record(
            'batch1-aria-semantics',
            {'criteria': ['WAI-ARIA 1.2 live regions',
                          'WCAG 2.2 SC 4.1.3 Status Messages',
                          'WCAG 2.2 SC 3.3.1 Error Identification'],
             'host_framework_limitation': {
                 'what': 'Odoo 19 marks an invalid field with the class '
                         '`o_field_invalid` and emits no `aria-invalid` '
                         'anywhere in web/static/src at the pinned commit '
                         '30bde9ff.',
                 'consequence': 'The invalid state itself is conveyed '
                                'visually; the REFUSAL is conveyed to '
                                'assistive technology by Odoo\'s '
                                'notification, which is `role="alert" '
                                'aria-live="assertive"` and names the field.',
                 'ownership': 'Odoo chrome, not connector arch. Not fixable '
                              'from this repository without patching core, '
                              'and disclosed rather than asserted away.',
             },
             'findings': findings},
            'Batch 1 alert/note semantics and announced validation states')

        # 1. The credential guidance is a live region AND its text changes.
        default_status = [
            region for region in findings['credential_default']['regions']
            if region['role'] == 'status'
        ]
        offline_status = [
            region for region in findings['credential_offline']['regions']
            if region['role'] == 'status'
        ]
        self.assertTrue(
            default_status,
            'the credential step renders no polite live region, so switching '
            'authentication path announces nothing')
        self.assertTrue(offline_status)
        self.assertNotEqual(
            ' '.join(sorted(r['text'] for r in default_status)),
            ' '.join(sorted(r['text'] for r in offline_status)),
            'the guidance did not change between the two authentication '
            'paths, so `role="status"` is announcing a sentence that never '
            'varies')

        # 2. The `note` band is static, which is why it is not a live region.
        def note_text(key):
            return ' '.join(sorted(
                region['text'] for region in findings[key]['regions']
                if region['role'] == 'note'))

        self.assertTrue(
            note_text('pair_dialog_opened'),
            'the single-pair withdrawal dialog renders no `role="note"` '
            'band, so this assertion is measuring nothing')
        self.assertEqual(
            note_text('pair_dialog_opened'), note_text('pair_dialog_filled'),
            'the `note` band changed while the dialog was open, so it IS a '
            'live region and a document role silences it')
        self.assertFalse(
            [region for region in findings['pair_dialog_opened']['regions']
             if region['role'] == 'note' and region['aria_live']],
            'a `note` element declares `aria-live`, which contradicts the '
            'document role it was given')
        # Every connector-owned alert band in the dialog carries a role.
        self.assertFalse(
            findings['dialog_opened']['roleless_alerts'],
            'these alert bands carry no role, so a screen reader is given no '
            'reason to read them: %s'
            % json.dumps(findings['dialog_opened']['roleless_alerts']))

        # 3. The refusal is ANNOUNCED and ATTRIBUTED.
        #
        # `aria-invalid` is deliberately NOT required here, and the reason is
        # recorded rather than assumed: Odoo 19 at the pinned commit does not
        # emit that attribute anywhere in `web/static/src` -- the invalid
        # state is `.o_field_invalid`, a class, on chrome this repository
        # does not own and cannot change without patching core. Asserting it
        # would fail forever for something outside the connector, and quietly
        # dropping the requirement would be worse. So it is MEASURED, carried
        # in the artifact as a disclosed limitation of the host framework,
        # and what the connector's own arch decides -- that the field is
        # required at all, and therefore that Odoo refuses before the request
        # is sent and names it -- is what is asserted.
        refusal = findings['refusal']
        self.assertTrue(
            refusal['invalid_shown'],
            'submitting with the mandatory reason empty marked no field '
            'invalid, so the operator is not told WHICH field is wrong')
        named = [
            field for field in refusal['invalid_fields']
            if field['field'] == 'reason'
        ]
        self.assertTrue(
            named,
            'the refusal did not attribute itself to `reason`: %s'
            % json.dumps(refusal['invalid_fields']))
        announced = [
            region for region in refusal['announced']
            if region['role'] in ('alert', 'status') or region['aria_live']
        ]
        self.assertTrue(
            announced,
            'the refusal reached no live region, so a screen reader user is '
            'told nothing happened: %s' % json.dumps(refusal))
        self.assertTrue(
            any('reason' in region['text'].lower() for region in announced),
            'the announcement does not name the field that was refused, so '
            'it says only that something was wrong: %s'
            % json.dumps(announced))

    # ------------------------------------------------------------------
    # Batch 2 evidence closure (2026-07-31)
    # ------------------------------------------------------------------

    def _batch2_surfaces(self, seeded):
        """The six Batch 2 surfaces, resolved, with the set proved complete."""
        reachable = {
            entry[0]: entry for entry in self._reachable_surfaces(seeded)
        }
        missing = [
            name for name in BATCH2_CHANGED_SURFACES if name not in reachable
        ]
        self.assertFalse(
            missing,
            'these Batch 2 surfaces are not in the capture set, so this '
            'evidence would cover less than it names: %s' % missing,
        )
        return [reachable[name] for name in BATCH2_CHANGED_SURFACES]

    def test_every_batch2_surface_yields_a_connector_owned_measurement(self):
        """No Batch 2 surface may be counted as covered while measuring zero.

        THE DEFECT THIS CLOSES. The overflow instrument names its measured
        roots explicitly, and until this correction it knew three Owl surfaces
        and a generic `.modal-body`. Four of the six Batch 2 surfaces are
        ordinary Odoo form views and matched none of them, so they produced NO
        connector-owned measurement at any width -- and both dialogs matched
        only through Odoo's own modal chrome, which is the same string for
        every dialog, so their rows could not say which screen they were
        about. Nothing failed, because nothing was measured; the campaign
        reported six covered surfaces and had evidence for two of them.

        So every named surface must yield at least one VISIBLE measured root
        that belongs to it, at every required width. A surface that renders
        nothing, renders somebody else's form, or loses its marker class is a
        failing row here rather than a quietly absent one.

        The page-level rule (§10) and the dialog's own reachability are kept
        rather than replaced: the document must not scroll sideways, the modal
        BODY is still measured for the two dialogs, and the final actionable
        control -- which for a dialog lives in the FOOTER, outside the body --
        must still be reachable.
        """
        seeded = self._seed()
        rows, failures = [], []
        with self._browser() as browser:
            for label, width in WIDTHS.items():
                self._viewport(browser, width)
                for (name, path, wait, criterion, after,
                     setup_step) in self._batch2_surfaces(seeded):
                    if setup_step:
                        self._set_setup_step(seeded['store'], setup_step)
                    self._open(browser, path, wait, after)
                    intended = BATCH2_SURFACE_SELECTORS[name]
                    presence = json.loads(self._eval(
                        browser, SURFACE_PRESENT_JS % json.dumps(intended)))
                    metrics = json.loads(self._eval(browser, OVERFLOW_JS))
                    last = json.loads(self._eval(browser, LAST_CONTROL_JS))

                    expected = set(BATCH2_SURFACE_ROOTS[name])
                    measured = [
                        surface['cls'] for surface in metrics['surfaces']
                    ]
                    own = [
                        {'cls': surface['cls'],
                         'classes': surface['classes'],
                         'markers': surface['markers'],
                         'scroll_width': surface['scroll_width'],
                         'client_width': surface['client_width'],
                         'clipped_by': surface['clipped_by'],
                         'clipped_silently': surface['clipped_silently']}
                        for surface in metrics['surfaces']
                        if expected & set(surface['markers'])
                    ]
                    page_overflow = max(
                        0,
                        metrics['doc_scroll_width']
                        - metrics['inner_width'] - 1,
                    )
                    defects = self._clipping_defects(name, width, metrics)
                    if not own:
                        defects.append({
                            'kind': 'no_connector_owned_measurement',
                            'surface': name, 'width': width,
                            'expected_markers': sorted(expected),
                            'measured_roots': measured,
                            'measured_markers': sorted({
                                marker
                                for surface in metrics['surfaces']
                                for marker in surface['markers']
                            }),
                        })
                    if not presence['visible']:
                        defects.append({
                            'kind': 'intended_surface_not_visible',
                            'surface': name, 'width': width,
                            'selector': intended, 'presence': presence,
                        })
                    if page_overflow:
                        defects.append({
                            'kind': 'page_scrolls_horizontally',
                            'surface': name, 'width': width,
                            'overflow': page_overflow,
                        })
                    if name.endswith('-dialog') and 'modal-body' not in measured:
                        defects.append({
                            'kind': 'modal_body_not_measured',
                            'surface': name, 'width': width,
                            'measured_roots': measured,
                        })
                    if last.get('error'):
                        defects.append({
                            'kind': 'no_actionable_control',
                            'surface': name, 'width': width,
                            'why': last['error'],
                        })
                    elif not last['reachable']:
                        defects.append({
                            'kind': 'final_control_unreachable',
                            'surface': name, 'width': width,
                            'control': last['selector'], 'rect': last['rect'],
                            'viewport': last['viewport'],
                        })
                    row = {
                        'surface': name,
                        'viewport': '%s (%dpx)' % (label, width),
                        'width': width,
                        'intended_selector': intended,
                        'intended_visible': presence['visible'],
                        'expected_markers': sorted(expected),
                        'connector_owned_roots_measured': own,
                        'all_measured_roots': measured,
                        'page_horizontal_overflow': page_overflow,
                        'final_control': last,
                        'defects': defects,
                        'verdict': 'PASS' if not defects else 'FAIL',
                    }
                    rows.append(row)
                    if defects:
                        failures.append(row)
                    self._shoot(
                        browser, '%s-clipping-%dpx' % (name, width),
                        criterion + ' (connector-owned clipping coverage; '
                                    'TD-016)')
        self._record(
            'batch2-clipping-coverage',
            {'surfaces': list(BATCH2_CHANGED_SURFACES),
             'expected_markers': BATCH2_SURFACE_ROOTS,
             'selectors': BATCH2_SURFACE_SELECTORS,
             'widths': WIDTHS,
             'rows': rows, 'failures': failures},
            'TD-016 connector-owned clipping measured on every Batch 2 '
            'surface, at every required width')
        self.assertEqual(
            len(rows), len(BATCH2_CHANGED_SURFACES) * len(WIDTHS),
            'the coverage matrix did not measure every planned combination')
        self.assertFalse(
            failures,
            'these Batch 2 surfaces produced no connector-owned clipping '
            'measurement, or clipped their own content:\n%s'
            % json.dumps(failures, indent=2)[:6000])

    def _arch_regions(self, model, xmlid):
        """Every ARIA/alert declaration in one surface's REAL arch.

        `get_view` returns the combined arch -- inherited views included --
        which is the complete declaration for a surface, including bands whose
        `invisible` is true for the fixture's record and notebook pages the
        browser has not rendered yet. The rendered inventory can only see what
        is on screen; this sees what was declared, and the two are asserted
        against each other rather than one standing in for the other.
        """
        from lxml import etree  # noqa: PLC0415

        view = self.env.ref(xmlid)
        arch = self.env[model].with_user(self.user).get_view(
            view.id, 'form')['arch']
        out = []
        for node in etree.fromstring(arch).iter():
            if not isinstance(node.tag, str):
                continue  # comments and processing instructions
            classes = (node.get('class') or '').split()
            alert_classes = [
                klass for klass in classes
                if klass.startswith('alert-') and klass != 'alert-link'
            ]
            role = node.get('role')
            live = node.get('aria-live')
            if not (role or live or alert_classes):
                continue
            out.append({
                'tag': node.tag,
                'role': role,
                'aria_live': live,
                'classes': classes,
                'alert_classes': alert_classes,
                'invisible': node.get('invisible'),
                'text': ' '.join(''.join(node.itertext()).split())[:400],
            })
        return out

    def test_batch2_live_regions_are_truthful(self):
        """What each Batch 2 band CLAIMS to be, against what it does.

        THE DEFECT THIS CLOSES. Four bands on three Batch 2 surfaces carried
        `role="status"` -- a polite ARIA live region, which promises a screen
        reader that this region will speak when its content CHANGES. All four
        were static instructional copy: the same sentence for every record,
        already on screen when the dialog or the record surface received
        focus, and unchanged by anything done on that surface. They had the
        role because they use an `alert-*` VISUAL class and Odoo's view
        validator asks for a live role when it sees one -- a presentational
        heuristic standing in for a semantic decision.

        WHAT IS ASSERTED, IN BOTH HALVES.

        Declared (the arch, inherited views included):
          * no band on any of the six surfaces claims a live-region role or
            `aria-live` unless it is adjudicated by name here, and every
            adjudication still matches something, so this cannot rot into a
            list of exemptions for bands that no longer exist;
          * every `alert-*` band carries SOME role, so none is styled urgent
            and left silent;
          * no `role="note"` carries `aria-live`, which would contradict it;
          * the four re-ruled bands are present, as `note`, with the sentence
            each one actually says -- so restoring the role, or keeping the
            role and rewriting the band, fails here.

        Rendered (a real browser, the real surfaces):
          * every surface renders its adjudicated bands, visible and
            non-empty -- a static note nobody can see is not readable;
          * no live region is rendered inside any connector-owned Batch 2
            root, which is the ruling made observable;
          * the notes survive a REAL production state change on the same
            visible surface: both dialogs are submitted with their mandatory
            choice empty, and the note text must be identical before and
            after while the REFUSAL reaches Odoo's own assertive live region
            and marks exactly one field -- the one the arch declared required
            (SC 3.3.1 / SC 4.1.3). Odoo 19 at the pin announces only
            "Missing required fields" and names no field; that is host
            chrome this repository does not own, so it is measured and
            disclosed in the artifact rather than asserted around;
          * the pending and superseded bands are proved to be a function of
            the LOADED RECORD and not of a live update: the pending band
            renders on a pending decision and is absent from a resolved one,
            and the superseded band appears only after the model's own
            `_supersede_stale_siblings` has actually retired the decision.
        """
        seeded = self._seed()
        findings = {'declared': {}, 'rendered': {}}

        # --- Declared -------------------------------------------------
        declared_live, roleless, live_note = [], [], []
        for surface in BATCH2_CHANGED_SURFACES:
            model, xmlid = BATCH2_SURFACE_VIEWS[surface]
            regions = self._arch_regions(model, xmlid)
            findings['declared'][surface] = regions
            for region in regions:
                if (region['role'] in ARIA_LIVE_REGION_ROLES
                        or region['aria_live']):
                    declared_live.append(dict(region, surface=surface))
                if region['alert_classes'] and not region['role']:
                    roleless.append(dict(region, surface=surface))
                if region['role'] == 'note' and region['aria_live']:
                    live_note.append(dict(region, surface=surface))

        adjudications = [
            {'surface': surface, 'role': role, 'fragment': fragment,
             'why': why, 'kind': kind}
            for kind, table in (
                ('retained', BATCH2_RETAINED_LIVE_REGIONS),
                ('foreign', BATCH2_FOREIGN_LIVE_REGIONS),
            )
            for surface, role, fragment, why in table
        ]

        def matches(entry, region):
            return (entry['surface'] == region['surface']
                    and entry['role'] == region['role']
                    and entry['fragment'] in region['text'])

        unadjudicated = [
            region for region in declared_live
            if not any(matches(entry, region) for entry in adjudications)
        ]
        stale = [
            entry for entry in adjudications
            if not any(matches(entry, region) for region in declared_live)
        ]
        findings['adjudications'] = adjudications
        findings['unadjudicated_live_regions'] = unadjudicated
        findings['stale_adjudications'] = stale

        # --- Rendered -------------------------------------------------
        note_texts, refusals = {}, {}
        dialog_surfaces = (
            'b2-tax-decision-dialog', 'b2-product-match-decision-dialog',
        )

        def inventory(browser, surface):
            root = BATCH2_LIVE_REGION_ROOTS[surface]
            payload = json.loads(
                self._eval(browser, LIVE_REGION_JS % json.dumps(root)))
            self.assertNotIn(
                'error', payload,
                'the connector-owned root %r was not on screen for %s, so '
                'nothing about that surface was inventoried'
                % (root, surface))
            return payload

        def notes(payload):
            return sorted(
                region['text'] for region in payload['regions']
                if region['role'] == 'note'
            )

        reachable = {
            entry[0]: entry for entry in self._reachable_surfaces(seeded)
        }
        with self._browser() as browser:
            self._viewport(browser, WIDTHS['desktop'])

            # The two dialogs, each driven to its own production refusal.
            for surface in dialog_surfaces:
                _n, path, wait, _c, after, _s = reachable[surface]
                self._open(browser, path, wait, after)
                before = inventory(browser, surface)
                findings['rendered']['%s:opened' % surface] = before
                refusal = json.loads(
                    self._eval(browser, INVALID_SUBMIT_JS, timeout=90.0))
                refusals[surface] = refusal
                after_refusal = inventory(browser, surface)
                findings['rendered']['%s:refused' % surface] = after_refusal
                note_texts[surface] = (notes(before), notes(after_refusal))
                self._dismiss_dialogs(browser)

            # The pending decision, and the same form on a decision that is
            # no longer pending: the band's presence is a property of the
            # RECORD, which is exactly why it is not a live region.
            for surface in ('b2-product-match-decision-pending',
                            'b2-product-match-decision-resolved'):
                _n, path, wait, _c, after, _s = reachable[surface]
                self._open(browser, path, wait, after)
                payload = inventory(browser, surface)
                findings['rendered'][surface] = payload
                note_texts[surface] = (notes(payload), notes(payload))

            # The superseded band, reached by actually superseding the
            # decision through the model's own path rather than by writing
            # the state this test wants to photograph.
            resolved = seeded.get('match_decision_resolved')
            self._block_match_import(
                seeded['store'], seeded['match_candidates'],
                resolved.shopify_product_gid, '2026-07-30T09:17:00Z')
            resolved.invalidate_recordset()
            self.env.flush_all()
            self.assertEqual(
                resolved.state, 'superseded',
                'the production supersession path did not retire the '
                'decision, so the superseded band cannot be measured here')
            _n, path, wait, _c, after, _s = (
                reachable['b2-product-match-decision-resolved'])
            self._open(browser, path, wait, after)
            superseded = inventory(browser, 'b2-product-match-decision-resolved')
            findings['rendered']['b2-superseded'] = superseded

            # The store form: inventory only. Nothing on it is editable, and
            # its only declared live regions belong to another module and are
            # not rendered for a healthy connected store.
            _n, path, wait, _c, after, _s = reachable['b2-store-form-controls']
            self._open(browser, path, wait, after)
            findings['rendered']['b2-store-form-controls'] = inventory(
                browser, 'b2-store-form-controls')

            # Store Settings LAST, because the drive here is a real field
            # edit: the form is left dirty on purpose, and navigating away
            # from a dirty form raises Odoo's own unsaved-changes dialog,
            # which would measure a confirmation prompt instead of a surface.
            surface = 'b2-store-settings-canonical'
            _n, path, wait, _c, after, _s = reachable[surface]
            self._open(browser, path, wait, after)
            before = inventory(browser, surface)
            findings['rendered']['%s:opened' % surface] = before
            toggled = self._eval(
                browser,
                _toggle_boolean_js(
                    ".o_field_widget[name='product_domain_enabled'] "
                    "input[type='checkbox']"),
                timeout=90.0)
            self.assertTrue(toggled, toggled)
            after_edit = inventory(browser, surface)
            findings['rendered']['%s:edited' % surface] = after_edit
            note_texts[surface] = (notes(before), notes(after_edit))

        self._record(
            'batch2-live-region-semantics',
            {'criteria': ['WAI-ARIA 1.2 §5.3.2 live regions',
                          'WCAG 2.2 SC 4.1.3 Status Messages',
                          'WCAG 2.2 SC 3.3.1 Error Identification'],
             'ruling': (
                 'A band that is on screen when the surface receives focus '
                 'and cannot change while it is on screen is document '
                 'structure, not a live region, whatever visual class it '
                 'uses. `role="note"` is the recorded answer; Odoo\'s '
                 '`alert-*`-needs-a-live-role view warning is a '
                 'presentational heuristic and is accepted rather than '
                 'obeyed, because obeying it declares a region with nothing '
                 'to announce.'),
             'host_framework_limitation': {
                 'what': 'Odoo 19 at the pinned commit 30bde9ff announces a '
                         'refused save as the bare string "Missing required '
                         'fields" -- `Record._displayInvalidFieldNotification` '
                         'in web/static/src/model/relational_model/record.js, '
                         'which no form controller overrides. The '
                         'announcement does not name the field.',
                 'consequence': 'The refusal IS announced, assertively, by '
                                'Odoo\'s own `role="alert" '
                                'aria-live="assertive"` notification. The '
                                'ATTRIBUTION is carried in the DOM instead: '
                                'exactly one field is marked invalid, and it '
                                'is the one the connector\'s arch declared '
                                'required.',
                 'ownership': 'Odoo chrome, not connector arch. Not fixable '
                              'from this repository without patching core. '
                              'Measured and disclosed here rather than '
                              'asserted around, and the assertions above say '
                              'only what is true: announced assertively, and '
                              'attributed to exactly one named field.',
             },
             'surfaces': list(BATCH2_CHANGED_SURFACES),
             'findings': findings,
             'note_texts_before_and_after': note_texts,
             'refusals': refusals},
            'Batch 2 status/note/alert inventory and semantic adjudication')

        # --- Declared assertions --------------------------------------
        self.assertTrue(
            findings['declared'],
            'no Batch 2 arch was read at all, so this proves nothing')
        self.assertFalse(
            unadjudicated,
            'these Batch 2 bands declare a live region that nobody has ruled '
            'on. A live region must be able to say what changes it '
            'announces:\n%s' % json.dumps(unadjudicated, indent=2)[:4000])
        self.assertFalse(
            stale,
            'these live-region adjudications match nothing in the arch any '
            'more, so this list has stopped describing the product:\n%s'
            % json.dumps(stale, indent=2)[:2000])
        self.assertFalse(
            roleless,
            'these Batch 2 bands are styled as alerts and carry no role, so '
            'a screen reader is given no reason to read them:\n%s'
            % json.dumps(roleless, indent=2)[:2000])
        self.assertFalse(
            live_note,
            'these `role="note"` bands declare `aria-live`, which contradicts '
            'the document role they were given:\n%s'
            % json.dumps(live_note, indent=2)[:2000])
        for surface, fragment in BATCH2_STATIC_NOTE_BANDS:
            hits = [
                region for region in findings['declared'][surface]
                if fragment in region['text']
            ]
            self.assertTrue(
                hits,
                'the re-ruled band %r is not declared on %s any more, so the '
                'ruling this test exists to hold has nothing to hold'
                % (fragment, surface))
            self.assertTrue(
                all(region['role'] == 'note' for region in hits),
                'the band %r on %s is not `role="note"`: %s'
                % (fragment, surface,
                   json.dumps([region['role'] for region in hits])))

        # --- Rendered assertions --------------------------------------
        rendered_live = []
        for key, payload in findings['rendered'].items():
            for region in payload['regions']:
                if (region['role'] in ARIA_LIVE_REGION_ROLES
                        or region['aria_live']):
                    rendered_live.append(dict(region, where=key))
            self.assertFalse(
                payload['roleless_alerts'],
                'alert bands with no role rendered on %s: %s'
                % (key, json.dumps(payload['roleless_alerts'])[:1000]))
        self.assertFalse(
            rendered_live,
            'these live regions rendered inside a connector-owned Batch 2 '
            'root. Every band on these surfaces is static, so any of them '
            'announcing itself is announcing nothing:\n%s'
            % json.dumps(rendered_live, indent=2)[:4000])

        # Every surface actually showed the reader something.
        for surface in BATCH2_CHANGED_SURFACES:
            if surface == 'b2-store-form-controls':
                # No note band is declared on it; the assertion above already
                # proves it renders no live region, and inventing one here
                # would be a test asserting a band that does not exist.
                continue
            keys = [
                key for key in findings['rendered']
                if key == surface or key.startswith('%s:' % surface)
            ]
            self.assertTrue(keys, 'no rendered inventory for %s' % surface)
            visible_notes = [
                region
                for key in keys
                for region in findings['rendered'][key]['regions']
                if region['role'] == 'note' and region['visible']
                and region['text']
            ]
            self.assertTrue(
                visible_notes,
                'no visible, non-empty `role="note"` band rendered on %s, so '
                '"the note stays static and readable" is measuring nothing'
                % surface)

        # The notes did not move while a real state change happened.
        for surface, (before_notes, after_notes) in note_texts.items():
            self.assertEqual(
                before_notes, after_notes,
                'the static bands on %s changed while a real production state '
                'change was driven on that same visible surface, so they ARE '
                'live regions and a document role silences them' % surface)

        # The pending band belongs to the record, not to a live update.
        pending_notes = [
            region['text'] for region in
            findings['rendered']['b2-product-match-decision-pending']['regions']
            if region['role'] == 'note'
        ]
        resolved_notes = [
            region['text'] for region in
            findings['rendered']['b2-product-match-decision-resolved']['regions']
            if region['role'] == 'note'
        ]
        superseded_notes = [
            region['text'] for region in
            findings['rendered']['b2-superseded']['regions']
            if region['role'] == 'note'
        ]
        self.assertTrue(
            any('waiting for a decision' in text for text in pending_notes),
            'the pending decision surface did not render its waiting band: %s'
            % json.dumps(pending_notes))
        self.assertFalse(
            any('waiting for a decision' in text for text in resolved_notes),
            'a decision that is no longer pending still renders the waiting '
            'band, so the band is not a function of the record after all: %s'
            % json.dumps(resolved_notes))
        self.assertTrue(
            any('Superseded' in text for text in superseded_notes),
            'the superseded band did not render on a genuinely superseded '
            'decision, so its semantics were never measured: %s'
            % json.dumps(superseded_notes))

        # And the refusals are still announced, and still attributed.
        for surface in dialog_surfaces:
            refusal = refusals[surface]
            self.assertTrue(
                refusal.get('invalid_shown'),
                'submitting %s with its mandatory choice empty marked no '
                'field invalid, so the operator is not told what is wrong: %s'
                % (surface, json.dumps(refusal)[:1000]))
            announced = [
                region for region in refusal['announced']
                if region['role'] in ('alert', 'status') or region['aria_live']
            ]
            self.assertTrue(
                announced,
                'the refusal on %s reached no live region: %s'
                % (surface, json.dumps(refusal)[:1000]))
            expected_field = {
                'b2-tax-decision-dialog': 'account_tax_id',
                'b2-product-match-decision-dialog': 'selected_template_id',
            }[surface]
            named = [
                field for field in refusal['invalid_fields']
                if field['field'] == expected_field
            ]
            self.assertTrue(
                named,
                'the refusal on %s did not attribute itself to %r: %s'
                % (surface, expected_field,
                   json.dumps(refusal['invalid_fields'])))
            # ATTRIBUTION IS PRECISE, not blanket. A form that marked every
            # field invalid would satisfy the assertion above while telling
            # the operator nothing about which one to fill in.
            #
            # Odoo marks the field WIDGET and its LABEL, and the label
            # carries no `name` of its own, so the raw list holds one unnamed
            # entry per refused field. That is host chrome; it stays in the
            # artifact rather than being filtered out of the record, and what
            # is asserted is that exactly one NAMED field is refused.
            named_fields = sorted({
                field['field'] for field in refusal['invalid_fields']
                if field['field']
            })
            self.assertEqual(
                named_fields, [expected_field],
                'the refusal on %s marked named fields other than the one it '
                'refused, so the attribution does not point anywhere: %s'
                % (surface, json.dumps(refusal['invalid_fields'])))
            self.assertTrue(
                any(region['aria_live'] == 'assertive'
                    or region['role'] == 'alert' for region in announced),
                'the refusal on %s was announced politely or not at all; a '
                'refused submission is not a status update: %s'
                % (surface, json.dumps(announced)[:1500]))


def odoo_http_port():
    from odoo.tools import config  # noqa: PLC0415
    return config['http_port']
