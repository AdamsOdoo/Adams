/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { imageUrl } from "@web/core/utils/urls";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

/**
 * Task: T8887 - The dropdown of a Collection Items card, as Shopify shows it: the product, how
 * many of its variants the collection holds, and which. Like on Shopify it only shows them;
 * variants are changed on the source.
 */
export class CollectionItemVariantsPopover extends Component {
    static template = "shopify.CollectionItemVariantsPopover";
    static props = {
        name: String,
        summary: String,
        imageSrc: String,
        variants: Array,
        close: Function,
    };
}

export class CollectionItemVariants extends Component {
    static template = "shopify.CollectionItemVariants";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ open: false });
        this.popover = usePopover(CollectionItemVariantsPopover, {
            position: "bottom-start",
            onClose: () => (this.state.open = false),
        });
    }

    get summary() {
        return this.props.record.data.collection_variant_summary;
    }

    get context() {
        // The card is a listing; the collection it sits in is the form's own record.
        return { collection_id: this.props.record.model.root.resId };
    }

    async toggle(ev) {
        if (this.popover.isOpen) {
            this.popover.close();
            return;
        }
        const target = ev.currentTarget;
        const variants = await this.orm.call("mk.listing", "get_collection_item_variants",
            [[this.props.record.resId]], { context: this.context });
        this.popover.open(target, {
            name: this.props.record.data.name,
            summary: this.summary,
            imageSrc: imageUrl("mk.listing", this.props.record.resId, "collection_image_256"),
            variants,
        });
        this.state.open = true;
    }
}

registry.category("view_widgets").add("shopify_collection_item_variants", {
    component: CollectionItemVariants,
});
