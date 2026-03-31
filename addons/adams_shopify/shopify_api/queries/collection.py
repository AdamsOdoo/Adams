FETCH_COLLECTIONS = """
query FetchCollections($first: Int!, $after: String) {
  collections(first: $first, after: $after) {
    edges {
      cursor
      node {
        id
        title
        handle
        descriptionHtml
        sortOrder
        productsCount {
          count
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

COLLECTION_CREATE_MUTATION = """
mutation collectionCreate($input: CollectionInput!) {
  collectionCreate(input: $input) {
    collection {
      id
      title
      handle
    }
    userErrors {
      field
      message
    }
  }
}
"""
