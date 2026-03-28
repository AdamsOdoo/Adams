WEBHOOK_CREATE_MUTATION = """
mutation WebhookCreate($topic: WebhookSubscriptionTopic!, $url: URL!) {
  webhookSubscriptionCreate(
    topic: $topic,
    webhookSubscription: {
      callbackUrl: $url,
      format: JSON
    }
  ) {
    webhookSubscription {
      id
      topic
      endpoint {
        __typename
        ... on WebhookHttpEndpoint {
          callbackUrl
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

WEBHOOK_LIST_QUERY = """
query WebhookList($first: Int!) {
  webhookSubscriptions(first: $first) {
    edges {
      node {
        id
        topic
        endpoint {
          __typename
          ... on WebhookHttpEndpoint {
            callbackUrl
          }
        }
        createdAt
      }
    }
  }
}
"""

WEBHOOK_DELETE_MUTATION = """
mutation WebhookDelete($id: ID!) {
  webhookSubscriptionDelete(id: $id) {
    deletedWebhookSubscriptionId
    userErrors {
      field
      message
    }
  }
}
"""
