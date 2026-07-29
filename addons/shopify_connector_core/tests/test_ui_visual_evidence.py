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
  const root = document.querySelector(
    ".o_sc_dashboard, .o_sc_export_diff, .o_sc_setup"
  );

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

    const ownRect = own ? own.node.getBoundingClientRect() : null;
    surfaces.push({
      cls: name(el),
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

    def _eval(self, browser, expression):
        # `_websocket_request` returns the CDP RESULT PAYLOAD, not the whole
        # message (see `ChromeBrowser.take_screenshot`, which reads
        # `f.result()['data']` directly). So for `Runtime.evaluate` the shape
        # is {'result': {'type', 'value'}, 'exceptionDetails': ...} -- one
        # level shallower than the raw protocol message.
        res = browser._websocket_request('Runtime.evaluate', params={
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

    def _open(self, browser, path, wait_for='.o_list_view, .o_form_view, '
                                            '.o_sc_dashboard, .o_sc_export_diff',
              after=None):
        from odoo.tests.common import HOST  # noqa: PLC0415
        url = 'http://%s:%s%s' % (HOST, odoo_http_port(), path)
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
                    self._eval(browser, action_js)
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
        self.env.flush_all()
        return {
            'store': store, 'mapping': mapping, 'level': level,
            'template_binding': tbinding, 'variant_binding': vbinding,
            'preview': preview,
        }

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
        if 'shopify.connector.location' in self.env:
            for index in range(1, 7):
                gid = 'gid://shopify/Location/VISUAL%d' % index
                if not self.env['shopify.connector.location'].sudo().search(
                    [('store_id', '=', store.id),
                     ('shopify_location_gid', '=', gid)], limit=1,
                ):
                    self.env['shopify.connector.location'].sudo().create({
                        'store_id': store.id,
                        'shopify_location_gid': gid,
                        'name': 'Visual evidence warehouse %d' % index,
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
        it carries all twelve steps, the action row exists, and no error band
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
  steps: document.querySelectorAll(".sc_setup_step").length,
  has_actions: !!document.querySelector(".sc_setup__actions"),
  has_error: !!document.querySelector(".sc_setup__panel") ? false : true,
  heading: (document.querySelector(".sc_setup__heading") || {}).textContent
    ? document.querySelector(".sc_setup__heading").textContent.trim()
      .replace(/\s+/g, " ").slice(0, 60)
    : null,
}))()
"""))
                self.assertEqual(
                    payload['steps'], 12,
                    '%s rendered %d steps, so it is not the wizard'
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
        """
        import re

        addons = pathlib.Path(__file__).resolve().parents[2]
        found = set()
        for pattern in ('shopify_connector_*/static/src/**/*.xml',
                        'shopify_connector_*/static/src/**/*.scss'):
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
                                'escapes_right',
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
  return JSON.stringify({
    error: null,
    position: getComputedStyle(bar).position,
    surface_direction: surface ? getComputedStyle(surface).direction : null,
    bar: {top: rect.top, bottom: rect.bottom, left: rect.left,
          right: rect.right, height: rect.height},
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
  const scroller = (() => {
    let node = document.querySelector(".o_sc_setup");
    while (node) {
      const cs = getComputedStyle(node);
      if (/auto|scroll/.test(cs.overflowY) &&
          node.scrollHeight > node.clientHeight + 4) {
        return node;
      }
      node = node.parentElement;
    }
    return document.scrollingElement;
  })();
  const before = scroller.scrollTop;
  scroller.scrollTop = Math.floor(
    (scroller.scrollHeight - scroller.clientHeight) / 2
  );
  return JSON.stringify({
    scroller: scroller.className || scroller.tagName,
    scrollable: scroller.scrollHeight - scroller.clientHeight,
    from: before,
    to: scroller.scrollTop,
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
            {'measured': measured, 'overlaps': overlaps},
            'WCAG 2.2 SC 2.4.11 Focus Not Obscured (Minimum)')
        self.assertTrue(measured, 'no focus-clearance case was measured')
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
                    if metrics['doc_scroll_width'] > metrics['inner_width'] + 1:
                        overflows.append({
                            'surface': name, 'width': width,
                            'doc_scroll_width': metrics['doc_scroll_width'],
                            'inner_width': metrics['inner_width']})
                    clipping.extend(
                        self._clipping_defects(name, width, metrics)
                    )
        self._record(
            'rtl',
            {'lang': lang.code,
             'note': 'Odoo 19 backend sets no `dir` on <html>/<body>; its RTL '
                     'mechanism is rtlcss bundle flipping. The connector '
                     'stylesheets use logical properties, which resolve '
                     'against `direction`, so the meaningful measurement is '
                     'the connector surface root.',
             'widths': WIDTHS,
             'measured': measured, 'overflows': overflows,
             'clipping': clipping},
            'DESIGN SYSTEM §10 RTL check at every required width (V-8); '
            'TD-016 per-surface clipping')

        self.assertTrue(measured, 'no surface was measured')
        # Odoo really did switch to RTL: its own flipped bundles were served.
        self.assertTrue(
            any(m['rtl_stylesheets'] for m in measured.values()),
            'Odoo served no rtlcss bundle, so the session was not actually in '
            'an RTL locale and this measured nothing',
        )
        self.assertTrue(
            any(m['odoo_rtl_class'] for m in measured.values()),
            'Odoo did not apply its own `.o_rtl` class, so the locale did not '
            'reach the web client',
        )
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


def odoo_http_port():
    from odoo.tools import config  # noqa: PLC0415
    return config['http_port']
