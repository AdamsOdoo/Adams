"""Dependency-free canonical fulfillment readback documents."""

ORDER_FULFILLMENTS_QUERY = (
    "query ConnectorOrderFulfillments($orderId: ID!) { order(id: $orderId) { id "
    "fulfillments(first: 250) { id status displayStatus trackingInfo { number url company } "
    "fulfillmentLineItems(first: 50) { pageInfo { hasNextPage endCursor } "
    "nodes { id quantity lineItem { id } } } } } }"
)
FULFILLMENT_NODE_QUERY = (
    "query ConnectorFulfillmentNode($id: ID!) { fulfillment(id: $id) { id status "
    "displayStatus trackingInfo { number url company } } }"
)

__all__ = ["FULFILLMENT_NODE_QUERY", "ORDER_FULFILLMENTS_QUERY"]
