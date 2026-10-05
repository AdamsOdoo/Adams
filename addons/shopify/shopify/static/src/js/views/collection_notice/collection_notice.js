/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

/**
 * Task: T8887 - The strip on top of a collection, telling the user to import from Shopify once
 * the upgrade has converted their collections. The migration raises the flag and the close
 * button clears it, so it shows once per database and never on a fresh install.
 */
export class CollectionNotice extends Component {
    static template = "shopify.CollectionNotice";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ visible: false });
        onWillStart(async () => {
            this.state.visible = this.instanceId
                ? await this.orm.call("shopify.collection.ts", "get_import_notice", [this.instanceId])
                : false;
        });
    }

    /** The notice belongs to one Shopify store, which the collection and both wizards carry. */
    get instanceId() {
        return this.props.record.data.mk_instance_id?.id || false;
    }

    /** Hidden right away, so the strip goes even if the write is slow. */
    async onDismiss() {
        this.state.visible = false;
        await this.orm.call("shopify.collection.ts", "dismiss_import_notice", [this.instanceId]);
    }
}

registry.category("view_widgets").add("shopify_collection_notice", {
    component: CollectionNotice,
});
