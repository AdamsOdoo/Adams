FETCH_LOCATIONS = """
query FetchLocations($first: Int!, $after: String) {
  locations(first: $first, after: $after) {
    edges {
      cursor
      node {
        id
        name
        address {
          address1
          city
          countryCode
        }
        isActive
        isPrimary
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""
