/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

/**
 * These two models only ever open inside a read-mostly popup (a metaobject value or a
 * field row). The popup's own dialog already shows everything there is to see, so the
 * "expand to full screen" affordance just adds a confusing extra navigation step.
 * Scoped by resModel so no other dialog in the database is affected.
 */
const NO_EXPAND_MODELS = ["shopify.metaobject.entry.value.ts", "shopify.metaobject.field.ts"];

patch(FormViewDialog.prototype, {
    setup() {
        super.setup();
        if (NO_EXPAND_MODELS.includes(this.props.resModel)) {
            this.onExpandCallback = undefined;
        }
    },
});
