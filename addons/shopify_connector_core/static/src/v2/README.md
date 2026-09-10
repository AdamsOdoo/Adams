# Inert V2 presentation slice

This directory contains the P03/P04 presentation boundary for the connector.
It is intentionally not referenced by the current addon manifest, views or
actions.  The presentational modules do not perform an RPC or change a record;
the isolated client-action controller contains the future wiring seam but is
not reachable until those assets and the client action are explicitly enabled.

## Entry points

- `connector_v2_components.js` is the stable import barrel.  Its implementation
  is split into `connector_v2_contracts.js` (pure envelopes, labels and
  nullable prop descriptors), `connector_v2_status.js` (status/state atoms),
  `connector_v2_overview.js` (overview, health and store selection),
  `connector_v2_attention.js` (attention selection/detail), and
  `connector_v2_run.js` (run evidence/timeline).  The barrel exports
  `Overview`, `AttentionWorkspace`, `RunTimeline`, `HealthBand`,
  `StoreSwitcher`, `StatusPill` and `StateMessage` at the original path.
- `connector_v2_components.xml` contains the matching Owl templates.
- `connector_v2_action.js` is the stable client-action import barrel.  The
  production shell is split into `connector_v2_action_contracts.js` (pure
  facade/action/error/fingerprint helpers) and
  `connector_v2_action_controller.js` (the one Odoo lifecycle/controller
  boundary).  The controller is still inert until its assets and client action
  are explicitly activated.
- `connector_v2.scss` owns the scoped root and imports cohesive style
  surfaces: `connector_v2_base.scss`, `connector_v2_health.scss`,
  `connector_v2_overview.scss`, `connector_v2_attention.scss`,
  `connector_v2_run.scss` and `connector_v2_responsive.scss`.
- `../../tests/v2/connector_v2_components.mount.test.js` is a real HOOT
  mount-test source.  It is intentionally not in an asset bundle yet.

All production JavaScript, XML and SCSS sources in this package stay below the
750-line review gate.  The barrels preserve stable import paths while the
implementation modules stay cohesive and dependency-directed; no generic
client framework or extra asset-order seam is introduced.  The architecture
test asserts that none of the presentational classes owns setup/state lifecycle
or a service registry.
Selection and focus remain controlled by the shell: page and section heading
IDs are instance-unique, rows expose `aria-current`, `aria-expanded`,
`aria-controls`, and the detail target is a programmatically focusable live
region even before an item is selected.  When the shell hides the list on a
small viewport it must focus the returned detail target after the server
selection is accepted, then restore focus to the triggering row on Back.

Every composed component accepts one `envelope` prop shaped like the V2 common
response envelope.  The server owns state, freshness and `allowed_actions`;
callbacks receive only server-returned objects or opaque references:

| Component | Explicit callbacks |
| --- | --- |
| `Overview` | `onStoreChange`, `onAction`, `onOpenAttention`, `onOpenWorkflow`, `onOpenRun` |
| `AttentionWorkspace` | `onSelect`, `onAction`, `onPage`, `onBack`, `onOpenRun` |
| `RunTimeline` | `onAction`, `onOpenRecord` |
| `HealthBand` | `onAction` |
| `StoreSwitcher` | `onSelect`, `onManage` |

## Future wiring checklist

The eventual P03/P04 integration owner must, in one bounded shell change:

1. add the SCSS, XML and JS paths to the core backend asset bundle;
2. register the shell/client action in Odoo without adding a browser router;
3. pass the server-owned response envelope from the application facade;
4. bind each callback to an allowlisted Odoo action or versioned command;
5. keep native list/form actions for high-density domain records;
6. add HOOT mount tests to the declared unit-test bundle and browser coverage at
   375, 768, 1366 and 1440 pixels plus RTL;
7. run the Odoo-shell compatibility gate before enabling the menu.

The integration must not add `orm`, `rpc`, transport, direct remote calls or a
global client-side store to these components.  The existing manifest remains
the source of truth until that gate is accepted.
