/** @odoo-module **/

/*
 * P16 contract tests stay independent of the web client and ORM.  They pin
 * the presentation boundary: six semantic phases, bounded state handling,
 * write-only credential/error treatment, and opaque command envelopes.
 */

import { describe, expect, test } from "@odoo/hoot";
import {
    P16_READ_ONLY_SETTING_FIELDS,
    P16_READ_METHODS,
    P16_ROLE_LABELS,
    P16_SETUP_PHASES,
    commandEnvelope,
    fieldIsReadOnly,
    normalizeEnvelope,
    normalizeResponseState,
    phaseForStep,
    safeErrorMessage,
    setupPhaseRows,
    serverActionTarget,
} from "@shopify_connector_core/p16/shopify_connector_p16_contract";

describe("P16 administrator presentation contracts", () => {
    test("reuses canonical V2 read, role, and native-target vocabulary", () => {
        expect(P16_READ_METHODS.attentionDetail).toBe("get_attention_detail_v1");
        expect(P16_ROLE_LABELS.reviewer).toBe("Reviewer");
        const target = {
            type: "ir.actions.act_window",
            res_model: "shopify.connector.store",
        };
        expect(serverActionTarget({ key: "manage_stores", target })).toBe(target);
        expect(serverActionTarget({ key: "manage_stores", target: { type: "ir.actions.act_url" } })).toBe(null);
    });

    test("keeps the twelve setup steps in six named phases", () => {
        expect(P16_SETUP_PHASES).toHaveLength(6);
        expect(P16_SETUP_PHASES.map((phase) => phase.key)).toEqual([
            "store_credential",
            "connection_scopes",
            "workflows",
            "locations",
            "authority_protections",
            "readiness_activation",
        ]);
        expect(phaseForStep("credential").key).toBe("store_credential");
        expect(phaseForStep("review").key).toBe("readiness_activation");
        expect(setupPhaseRows([
            { step_key: "welcome", state: "completed" },
            { step_key: "review", state: "pending" },
        ])).toHaveLength(6);
    });

    test("normalizes unknown response states to a closed terminal state", () => {
        expect(normalizeResponseState("accepted")).toBe("success");
        expect(normalizeResponseState("blocked")).toBe("terminal_error");
        expect(normalizeResponseState("made_up", "empty")).toBe("empty");
        expect(normalizeEnvelope({ status: "conflict", message: "refresh" }).state).toBe("conflict");
    });

    test("never presents credential or authorization-bearing error text", () => {
        const safe = "The store is not ready; refresh the evidence.";
        expect(safeErrorMessage(safe)).toBe(safe);
        expect(safeErrorMessage("access_token=shpat_secret")).toInclude("safe explanation");
        expect(safeErrorMessage("Authorization header rejected")).toInclude("safe explanation");
    });

    test("keeps safety fields output-only and create envelopes store-less", () => {
        expect(P16_READ_ONLY_SETTING_FIELDS.has("notification_default_enabled")).toBe(true);
        expect(fieldIsReadOnly({ key: "fulfillment_operating_mode" })).toBe(true);
        expect(fieldIsReadOnly({ key: "product_domain_enabled" })).toBe(false);
        const command = commandEnvelope({
            commandName: "create_store_v1",
            companyId: 4,
            actorUid: 9,
            expectedGeneration: 0,
            storeId: null,
            payload: { name: "North", shop_domain: "north.myshopify.com" },
        });
        expect(command.store_id).toBe(undefined);
        expect(command.payload.access_token).toBe(undefined);
        expect(command.contract_version).toBe(1);
        expect(command.actor_uid).toBe(9);
    });
});
