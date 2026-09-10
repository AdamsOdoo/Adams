/** @odoo-module **/

import { describe, expect, test } from "@odoo/hoot";
import {
    AttentionWorkspace,
    HealthBand,
    Overview,
    RunTimeline,
    StateMessage,
    StatusPill,
    StoreSwitcher,
} from "@shopify_connector_core/v2/connector_v2_components";

describe("V2 presentation boundary", () => {
    test("composed classes do not own lifecycle state or a transport service", () => {
        const components = [
            Overview,
            AttentionWorkspace,
            RunTimeline,
            HealthBand,
            StoreSwitcher,
            StatusPill,
            StateMessage,
        ];

        for (const component of components) {
            expect(Object.prototype.hasOwnProperty.call(component.prototype, "setup")).toBe(
                false
            );
            expect(Object.prototype.hasOwnProperty.call(component.prototype, "willStart")).toBe(
                false
            );
            expect(Object.prototype.hasOwnProperty.call(component, "router")).toBe(false);
            expect(Object.prototype.hasOwnProperty.call(component, "store")).toBe(false);
            expect(component.template).toInclude("shopify_connector_core.v2.");
        }

        expect(Overview.components.StoreSwitcher).toBe(StoreSwitcher);
        expect(Overview.components.HealthBand).toBe(HealthBand);
        expect(AttentionWorkspace.components.StatusPill).toBe(StatusPill);
        expect(RunTimeline.components.StateMessage).toBe(StateMessage);
    });
});
