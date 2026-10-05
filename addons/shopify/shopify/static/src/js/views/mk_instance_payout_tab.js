/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { onRendered } from "@odoo/owl";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);

        // Use an instance property to track if the action was already performed
        // This replaces the need to mutate the read-only props context.
        this.payoutTabActivated = false;

        onRendered(() => {
            const context = this.props.context || {};
            const resModel = this.props.resModel;
            // Run logic only if context matches AND we haven't already activated the tab
            if (resModel === 'mk.instance' &&
                context.active_tab_payout === 'payout' &&
                !this.payoutTabActivated
            ) {
                const selector = '.nav-link[name="payout"], a[data-name="payout"]';

                // 1. Immediate check
                const existingTab = document.querySelector(selector);
                if (existingTab) {
                    if (!existingTab.classList.contains('active')) {
                        existingTab.click();
                    }
                    // Mark as activated instead of mutating props
                    this.payoutTabActivated = true;
                    return;
                }

                // 2. Mutation Observer (for lazy-loaded components in Odoo 19)
                const observer = new MutationObserver((mutations, obs) => {
                    const payoutTab = document.querySelector(selector);
                    if (payoutTab) {
                        if (!payoutTab.classList.contains('active')) {
                            payoutTab.click();
                        }
                        // Mark as activated instead of mutating props
                        this.payoutTabActivated = true;
                        obs.disconnect();
                    }
                });

                observer.observe(document.body, {childList: true, subtree: true});

                // Safety timeout to prevent performance issues and memory leaks
                setTimeout(() => observer.disconnect(), 2000);
            }
        });
    },
});