/** @odoo-module **/

/*
 * Stable presentation import surface.
 *
 * Keep this barrel path unchanged for existing tests and future consumers;
 * implementation ownership lives in cohesive contract/domain modules.
 */

export {
    RESPONSE_STATES,
    V2ResponseStates,
    NULLABLE_BOOLEAN,
    NULLABLE_FUNCTION,
    NULLABLE_OBJECT,
    NULLABLE_STRING,
    actionFor,
    allowedStore,
    callback,
    dataObject,
    envelopeState,
    eventKindLabel,
    formatAge,
    isRecord,
    localeDirection,
    nonEmptyString,
    operationLabel,
    ownerRoleLabel,
    readEnvelope,
    safeText,
    stateCopy,
    stateMeta,
    storeOptions,
    triggerTypeLabel,
    workflowLabel,
} from "./connector_v2_contracts";

export { StateMessage, StatusPill } from "./connector_v2_status";
export { HealthBand, Overview, StoreSwitcher } from "./connector_v2_overview";
export { AttentionWorkspace } from "./connector_v2_attention";
export { RunTimeline } from "./connector_v2_run";
