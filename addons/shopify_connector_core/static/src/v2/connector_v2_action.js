/** @odoo-module **/

/*
 * Stable client-action import surface. Keep this path unchanged for existing
 * tests and later asset wiring; the controller and pure contracts are split
 * into focused modules behind it.
 */

export {
    ACTION_SERVICE_KEYS,
    FACADE_MODEL,
    POLL_INTERVAL_MS,
    ROLE_LABELS,
    RPC_METHODS,
    V2_VIEWS,
    initialStoreId,
    initialStoreName,
    isActiveRunEnvelope,
    isRecord,
    localeDirection,
    makeEnvelope,
    nativeActionMatches,
    normalizeRpcError,
    nonEmptyString,
    positiveStoreId,
    responseData,
    responseFingerprint,
    serverActionTarget,
    serverAllowsAction,
} from "./connector_v2_action_contracts";

export { ShopifyConnectorV2Action } from "./connector_v2_action_controller";
export {
    RECOVERY_ACTION_KEYS,
    RECOVERY_COMMAND,
} from "./connector_v2_action_recovery";
