# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handler for SHOP_QUERY."""


def handle_shop_query(env, config, variables):
    """Return simulated shop info matching Shopify's shop query shape."""
    return {
        'shop': {
            'name': config.shop_name or 'Simulator Store',
            'email': config.shop_email or '',
            'myshopifyDomain': config.myshopify_domain or 'simulator.myshopify.com',
            'plan': {
                'displayName': config.plan_display_name or 'Development',
                'partnerDevelopment': True,
                'shopifyPlus': False,
            },
            'currencyCode': config.currency_code or 'USD',
            'timezoneAbbreviation': config.timezone or 'EST',
        },
    }
