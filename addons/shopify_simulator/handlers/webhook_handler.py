# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handlers for webhook subscription CRUD queries and mutations.

Covers:
- WEBHOOK_LIST_QUERY                — list all subscriptions
- webhookSubscriptionCreate         — register a new webhook
- webhookSubscriptionDelete         — remove a webhook
"""
import logging

from .base_handler import paginate_records, build_mutation_response

_logger = logging.getLogger(__name__)


def handle_webhook_list(env, config, variables):
    """WEBHOOK_LIST_QUERY — paginated list of webhook subscriptions.

    The connector sends: {'first': 50}
    """
    first = variables.get('first', 50)
    after = variables.get('after')

    subs = env['sim.shopify.webhook.subscription'].search([
        ('config_id', '=', config.id),
    ], order='id asc')

    return {'webhookSubscriptions': paginate_records(subs, first, after)}


def handle_webhook_create(env, config, variables):
    """webhookSubscriptionCreate mutation.

    The connector sends:
    {
      'topic': 'PRODUCTS_CREATE',   # GraphQL enum
      'url': 'https://....'
    }
    """
    topic = variables.get('topic', '')
    callback_url = variables.get('url', '')

    if not topic:
        return build_mutation_response('webhookSubscriptionCreate', {
            'webhookSubscription': None,
        }, [
            {'field': ['topic'], 'message': 'Topic is required'},
        ])

    if not callback_url:
        return build_mutation_response('webhookSubscriptionCreate', {
            'webhookSubscription': None,
        }, [
            {'field': ['url'], 'message': 'Callback URL is required'},
        ])

    # Check for duplicate topic
    existing = env['sim.shopify.webhook.subscription'].search([
        ('config_id', '=', config.id),
        ('topic', '=', topic),
    ], limit=1)
    if existing:
        # Shopify returns the existing subscription (updates callback_url)
        existing.write({'callback_url': callback_url})
        return build_mutation_response('webhookSubscriptionCreate', {
            'webhookSubscription': existing._to_graphql_node(),
        })

    sub = env['sim.shopify.webhook.subscription'].create({
        'config_id': config.id,
        'topic': topic,
        'callback_url': callback_url,
    })

    return build_mutation_response('webhookSubscriptionCreate', {
        'webhookSubscription': sub._to_graphql_node(),
    })


def handle_webhook_delete(env, config, variables):
    """webhookSubscriptionDelete mutation.

    The connector sends: {'id': 'gid://shopify/WebhookSubscription/...'}
    """
    sub_gid = variables.get('id', '')

    sub = env['sim.shopify.webhook.subscription'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', sub_gid),
    ], limit=1)

    if not sub:
        return build_mutation_response('webhookSubscriptionDelete', {
            'deletedWebhookSubscriptionId': None,
        }, [
            {'field': ['id'],
             'message': f'Webhook subscription not found: {sub_gid}'},
        ])

    deleted_gid = sub.shopify_gid
    sub.unlink()

    return build_mutation_response('webhookSubscriptionDelete', {
        'deletedWebhookSubscriptionId': deleted_gid,
    })
