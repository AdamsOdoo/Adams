"""GraphQL queries for Shopify Payouts (Shopify Payments)."""

FETCH_PAYOUTS = """
query FetchPayouts($first: Int!, $after: String) {
    shopifyPaymentsAccount {
        payouts(first: $first, after: $after) {
            edges {
                cursor
                node {
                    id
                    legacyResourceId
                    status
                    net {
                        amount
                        currencyCode
                    }
                    gross {
                        amount
                        currencyCode
                    }
                    transactionFee {
                        amount
                        currencyCode
                    }
                    summary {
                        adjustmentsFee {
                            amount
                        }
                        adjustmentsGross {
                            amount
                        }
                        chargesFee {
                            amount
                        }
                        chargesGross {
                            amount
                        }
                        refundsFee {
                            amount
                        }
                        refundsGross {
                            amount
                        }
                    }
                    issuedAt
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
}
"""

FETCH_PAYOUT_TRANSACTIONS = """
query FetchPayoutTransactions($payoutId: ID!, $first: Int!, $after: String) {
    shopifyPaymentsAccount {
        payoutTransactions(payoutId: $payoutId, first: $first, after: $after) {
            edges {
                cursor
                node {
                    id
                    type
                    sourceType
                    amount {
                        amount
                        currencyCode
                    }
                    fee {
                        amount
                        currencyCode
                    }
                    net {
                        amount
                        currencyCode
                    }
                    sourceOrderTransactionId
                    processedAt
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
}
"""
