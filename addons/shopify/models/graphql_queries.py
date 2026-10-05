FETCH_FULFILLMENT = """
query fetchFulfillmentOrders($orderId: ID!, $fulfillmentCursor: String, $lineItemCursor: String) {
  order(id: $orderId) {
    id
    name
    fulfillmentOrders(first: 100, after: $fulfillmentCursor) {
      edges {
        node {
          id
          status
          lineItems(first: 100, after: $lineItemCursor) {
            edges {
              node {
                id
                totalQuantity
                remainingQuantity
                lineItem {
                  id
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
          assignedLocation {
            location {
              id
            }
          }
          deliveryMethod {
            methodType
          }
          destination{
            location{
              id
            }
          }
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

UPDATE_PICKUP_STATUS = """
mutation FulfillmentOrderLineItemsPreparedForPickup($fulfillmentOrderId: ID!) {
  fulfillmentOrderLineItemsPreparedForPickup(input: {
    lineItemsByFulfillmentOrder: [
      {
        fulfillmentOrderId: $fulfillmentOrderId
      }
    ]
  }) {
    userErrors {
      field
      message
    }
  }
}
"""

CANCEL_ORDER = """
mutation orderCancel($notifyCustomer: Boolean, $orderId: ID!, $reason: OrderCancelReason!, $refundMethod: OrderCancelRefundMethodInput, $restock: Boolean!, $staffNote: String) {
  orderCancel(notifyCustomer: $notifyCustomer, orderId: $orderId, reason: $reason, refundMethod: $refundMethod, restock: $restock, staffNote: $staffNote) {
    job {
      id
    }
    orderCancelUserErrors {
      message
      field
    }
  }
}
"""

PRICE_UPDATE = """
mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants {
      id
      legacyResourceId
      price
    }
    userErrors {
      field
      message
    }
  }
}
"""

GET_SPECIFIC_PRODUCT_DATA = """
query GetProductData($productId: ID!) {
  product(id: $productId) {
    id
    title
    description
    descriptionHtml
    productType
    category {
      id
      name
      fullName      
    }
    tags
    variants(first: 250) {
      nodes {
        id
        barcode
        sku
        price
        taxable
        title
        selectedOptions {
          name
          value
        }
        inventoryItem {
          id
          tracked
          countryCodeOfOrigin
          harmonizedSystemCode
          measurement {
            weight {
              unit
              value
            }
          }
        }
        inventoryPolicy
        media(first: 2) {
          nodes {
            id
            alt
            mediaContentType
            preview {
              image {
                id
                url
              }
            }
          }
        }
        resourcePublicationsV2(first: 20) {
          nodes {
            isPublished
            publishDate

            publication {
              id

              catalog {
                ... on AppCatalog {
                  apps(first: 10) {
                    nodes {
                      title
                    }
                  }
                }
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
        createdAt
        updatedAt
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
    options {
      name
      values
    }
    resourcePublications(first: 20) {
      nodes {
        isPublished
        publication {
          id
          catalog {
            ... on AppCatalog {
              apps(first: 10) {
                nodes {
                  title
                }
              }
            }
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
    media(first: 250) {
      nodes {
        id
        alt
        mediaContentType
        preview {
          image {
            id
            url
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
    createdAt
    updatedAt
  }
}
"""

GET_SPECIFIC_PRODUCTS_BY_IDS = """
query GetSpecificProductsByIds($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on Product {
      id
      title
      description
      descriptionHtml
      productType
      category {
        id
        name
        fullName      
      }
      tags
      variants(first: 250) {
        nodes {
          id
          barcode
          sku
          price
          taxable
          title
          selectedOptions {
            name
            value
          }
          inventoryItem {
            id
            tracked
            countryCodeOfOrigin
            harmonizedSystemCode
            measurement {
              weight {
                unit
                value
              }
            }
          }
          inventoryPolicy
          media(first: 2) {
            nodes {
              id
              alt
              mediaContentType
              preview {
                image {
                  id
                  url
                }
              }
            }
          }
          resourcePublicationsV2(first: 20) {
            nodes {
              isPublished
              publishDate

              publication {
                id

                catalog {
                  ... on AppCatalog {
                    apps(first: 10) {
                      nodes {
                        title
                      }
                    }
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
          createdAt
          updatedAt
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
      options {
        name
        values
      }
      resourcePublications(first: 20) {
        nodes {
          isPublished
          publication {
            id
            catalog {
              ... on AppCatalog {
                apps(first: 10) {
                  nodes {
                    title
                  }
                }
              }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
      media(first: 250) {
        nodes {
          id
          alt
          mediaContentType
          preview {
            image {
              id
              url
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
      createdAt
      updatedAt
    }
  }
}
"""

GET_MULTIPLE_PRODUCTS = """
query GetMultipleProducts($productsCursor: String, $queryFilter: String) {
  products(first: 250, after: $productsCursor, query: $queryFilter) {
     edges {
      node {
        id
        title
        description
        descriptionHtml
        productType
        category {
          id
          name
          fullName
        }
        tags
        variants(first: 12) {
          nodes {
            id
            barcode
            sku
            price
            taxable
            title
            selectedOptions {
              name
              value
            }
            inventoryItem {
              id
              tracked
              countryCodeOfOrigin
              harmonizedSystemCode
              measurement {
                weight {
                  unit
                  value
                }
              }
            }
            inventoryPolicy
            media(first: 1) {
              nodes {
                id
                alt
                mediaContentType
                preview {
                  image {
                    id
                    url
                  }
                }
              }
            }
            resourcePublicationsV2(first: 2) {
              nodes {
                isPublished
                publishDate
                publication {
                  id
                  catalog {
                    ... on AppCatalog {
                      apps(first: 2) {
                        nodes {
                          title
                        }
                      }
                    }
                  }
                }
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
            createdAt
            updatedAt
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
        variantsCount{
          count
        }
        options {
          name
          values
        }
        resourcePublications(first: 2) {
          nodes {
            isPublished
            publication {
              id
              catalog {
                ... on AppCatalog {
                  apps(first: 2) {
                    nodes {
                      title
                    }
                  }
                }
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
        resourcePublicationsCount{
          count
        }
        media(first: 3) {
          nodes {
            id
            alt
            mediaContentType
            preview {
              image {
                id
                url
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
        mediaCount{
          count
        }
        createdAt
        updatedAt
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

GET_PRODUCT_VARIANT_AFTER_CURSOR = """
query GetVariantsOfProduct($productId: ID!, $cursor: String, $first: Int) {
  product(id: $productId) {
    variants(first: $first, after: $cursor) {
      nodes {
        id
        barcode
        sku
        price
        taxable
        title
        selectedOptions {
          name
          value
        }
        inventoryItem {
          id
          tracked
          countryCodeOfOrigin
          harmonizedSystemCode
          measurement {
            weight {
              unit
              value
            }
          }
        }
        inventoryPolicy
        media(first: 1) {
          nodes {
            id
            alt
            mediaContentType
            preview {
              image {
                id
                url
              }
            }
          }
        }
        resourcePublicationsV2(first: 3) {
          nodes {
            isPublished
            publishDate
            publication {
              id
              catalog {
                ... on AppCatalog {
                  apps(first: 3) {
                    nodes {
                      title
                    }
                  }
                }
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
        createdAt
        updatedAt
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""

GET_PRODUCT_PUBLICATION_AFTER_CURSOR = """
query GetProductPublication($productId: ID!, $cursor: String, $first: Int) {
  product(id: $productId) {
     resourcePublications(first: $first, after: $cursor) {
      nodes {
        isPublished
        publication {
          id
          catalog {
            ... on AppCatalog {
              apps(first: 100) {
                nodes {
                  title
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

GET_VARIANT_PUBLICATION_AFTER_CURSOR = """
query GetVariantPublicationsAfterCursor($variantId: ID!, $cursor: String, $first: Int) {
  productVariant(id: $variantId) {
    resourcePublicationsV2(first: $first, after: $cursor) {
      nodes {
        isPublished
        publishDate
        publication {
          id
          catalog {
            ... on AppCatalog {
              apps(first: 5) {
                nodes {
                  title
                }
              }
            }
          }
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

GET_PRODUCT_IMAGE_AFTER_CURSOR = """
query GetProductImages($productId: ID!, $cursor: String, $first: Int) {
  product(id: $productId) {
    media(first: $first, after: $cursor) {
      nodes {
        id
        alt
        mediaContentType
        preview {
          image {
            id
            url
          }
        }
      }
    }
  }
}
"""

GET_ALL_PRODUCT_PUBLICATIONS = """
query GetAllPublications {
  catalogs(first: 250){
    edges{
      node{
        publication {
          id
            catalog {
              ... on AppCatalog {
                apps(first: 250) {
                  nodes {
                    title
                  }
                }
              }
            }
          }
      }
    }
  }
}
"""

GET_PRODUCT_VARIANT = """query getProductVariant($variantId: ID!) {
  productVariant(id: $variantId) {
    id
    sku
    barcode
  }
}"""

STORE_CURRENCY = """
query shopCurrency{
    shop {
      currencyCode
    }
}
"""

ALL_LOCATIONS = """
query GetAllLocations($cursor: String) {
  locations(first: 250, after: $cursor, includeInactive: false, includeLegacy: true) {
    nodes {
      id
      name
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

GET_PRIMARY_LOCATION = """
query GetPrimaryLocation {
  location {
    id
    isActive
  }
}
"""

PUBLISH_PRODUCT = """
mutation publishProductToMultiplePublication($productId: ID!, $input: [PublicationInput!]!) {
  publishablePublish(
    id: $productId
    input: $input
  ) {
    userErrors {
      field
      message
    }
  }
}
"""

UNPUBLISH_PRODUCT = """
mutation UnpublishProductFromPublication($productId: ID!, $input: [PublicationInput!]!) {
  publishableUnpublish(
    id: $productId
    input: $input
  ) {
    userErrors {
      field
      message
    }
  }
}
"""

PUBLISH_PRODUCT_VARIANT = """
mutation publishVariantToMultiplePublication($variantId: ID!, $input: [PublicationInput!]!) {
  publishablePublish(
    id: $variantId
    input: $input
  ) {
    userErrors {
      field
      message
    }
  }
}
"""

UNPUBLISH_PRODUCT_VARIANT = """
mutation unpublishVariantFromPublication($variantId: ID!, $input: [PublicationInput!]!) {
  publishableUnpublish(
    id: $variantId
    input: $input
  ) {
    userErrors {
      field
      message
    }
  }
}
"""

UPDATE_PRODUCT_DATA = """
mutation updateProductData($input: ProductSetInput!, $synchronous: Boolean!, $identifier: ProductSetIdentifiers) {
  productSet(input: $input,synchronous: $synchronous,identifier: $identifier) {
    product {
    id
    title
    description
    descriptionHtml
    productType
    category {
      id
      name
      fullName      
    }
    tags
    variants(first: 250) {
      nodes {
        id
        barcode
        sku
        price
        taxable
        title
        selectedOptions {
          name
          value
        }
        inventoryItem {
          id
          tracked
          countryCodeOfOrigin
          harmonizedSystemCode
          measurement {
            weight {
              unit
              value
            }
          }
        }
        inventoryPolicy
        media(first: 2) {
          nodes {
            id
            alt
            mediaContentType
            preview {
              image {
                url
              }
            }
          }
        }
        resourcePublicationsV2(first: 20) {
          nodes {
            isPublished
            publishDate
            publication {
              id
              catalog {
                ... on AppCatalog {
                  apps(first: 10) {
                    nodes {
                      title
                    }
                  }
                }
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
        createdAt
        updatedAt
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
     options {
      id
      name
      values
    }
    resourcePublications(first: 100) {
      nodes { 
        isPublished
        publication {
            id
            catalog {
              ... on AppCatalog {
                apps(first: 100) {
                  nodes {
                    title
                  }
                }
              }
            }
          }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
    media(first: 250) {
          nodes {
            id
            alt
            mediaContentType
            preview {
              image {
                url
              }
            }
          }
        }
    createdAt
    updatedAt
    }
    userErrors {
      code
      field
      message
    }
  }
}
"""

GET_PRODUCT_MEDIA_BATCH = """
query GetProductMediaBatch($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on Product {
      id
      media(first: 250) {
        nodes {
          status
          mediaErrors {
            code
            details
          }
          ... on MediaImage {
            id
            alt
            mediaContentType
            image {
              url
            }
          }
          ... on Video {
            id
            alt
            mediaContentType
          }
          ... on ExternalVideo {
            id
            alt
            mediaContentType
          }
          ... on Model3d {
            id
            alt
            mediaContentType
          }
        }
      }
    }
  }
}
"""

ADD_UPDATE_VARIANT_MEDIA = """
mutation UpdateVariantWithMedia($productId: ID!, $variants: [ProductVariantsBulkInput!]!, $media:[CreateMediaInput!]) {
  productVariantsBulkUpdate(
    productId: $productId,
    variants: $variants,
    media: $media
  ) {
    productVariants {
      id
      media(first: 250) {
        nodes {
          id
          alt
          mediaContentType
          preview{
            image{
              url
              altText  
            }
          }
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

GET_ORDERS_BY_ID = """
query GetOrdersById($orderId: ID!) {
  order(id: $orderId) {
      id
      note
      name
      processedAt
      cancelledAt
      sourceName
      tags
      cancelReason
      displayFinancialStatus
      displayFulfillmentStatus
      paymentGatewayNames
      currencyCode
      presentmentCurrencyCode
      taxesIncluded
      
      metafields(first:250){
        nodes{
            id
            namespace
            key
            type
            value
            jsonValue
        }
        pageInfo{
            endCursor
            hasNextPage
        }
      }
      
      totalPriceSet{
        presentmentMoney{
            amount
        }
        shopMoney{
            amount
        }
      }

      billingAddress {
        name
        firstName
        lastName
        address1
        address2
        city
        phone
        company
        country
        countryCodeV2
        province
        provinceCode
        zip
      }

      shippingAddress {
        name
        firstName
        lastName
        address1
        address2
        city
        phone
        company
        country
        countryCodeV2
        province
        provinceCode
        zip
      }

      customer {
        note
        tags
        defaultEmailAddress{
            emailAddress
        }
        defaultPhoneNumber {
            phoneNumber
        }
        firstName
        lastName
        defaultAddress {
            name
            firstName
            lastName
            address1
            address2
            city
            phone
            company
            country
            countryCodeV2
            province
            provinceCode
            zip
        }
      }

      taxLines {
        title
        rate
        priceSet {
          presentmentMoney {
            amount
          }
          shopMoney {
            amount
          }
        }
      }

      lineItems(first: 250) {
          nodes {
            id
            name
            title
            quantity
            currentQuantity
            sku
            isGiftCard
            requiresShipping
            originalUnitPriceSet{
                presentmentMoney{
                    amount
                }
                shopMoney{
                    amount
                }
            }
            taxLines {
                title
                rate
                priceSet {
                    presentmentMoney {
                        amount
                        }
                    shopMoney {
                        amount
                        }
                    }
            }

            duties {
                id
                taxLines {
                    rate
                    title
                    priceSet {
                        presentmentMoney {
                            amount
                        }
                        shopMoney {
                            amount
                        }
                    }
                }
                price{
                   presentmentMoney {
                    amount
                  }
                  shopMoney {
                    amount
                  }
                }
            }

            discountAllocations {
              allocatedAmountSet {
                    presentmentMoney {
                        amount
                    }
                    shopMoney {
                        amount
                    }
              }
            }

            product {
              id
            }

            variant {
              id
              sku
              barcode
            }
          }

        pageInfo{
            hasNextPage
            endCursor
        }
      }

      fulfillments(first: 200){
        id
        status
        location{
            id
            name
        }
        trackingInfo{
            number
            company
        }
        fulfillmentLineItems(first: 150){
                nodes{
                    id
                    lineItem{
                        id
                        isGiftCard
                        }
                    quantity
            }
            pageInfo{
                hasNextPage
                endCursor
        }
        }
      }

      shippingLines(first: 250) {
          nodes {
            id
            title
            originalPriceSet{
                presentmentMoney{
                    amount
                }
                shopMoney{
                    amount
                }
            }
            discountAllocations{
                allocatedAmountSet{
                    presentmentMoney{
                        amount
                    }
                    shopMoney{
                        amount
                    }
                }
            }
            taxLines {
                title
                rate
                priceSet {
                    presentmentMoney {
                        amount
                    }
                    shopMoney {
                        amount
                    }
                }
            }
        }
        pageInfo{
            hasNextPage
            endCursor
        }
      }

      transactions(first:10) {
        kind
        status
        gateway
        id
        paymentId
        amountSet {
          presentmentMoney {
            amount
          }
          shopMoney {
            amount
          }
        }
      }

      refunds(first:10){
        id
        note
        createdAt
        refundLineItems(first: 200){
            nodes{
                id
                quantity
                lineItem{
                    id
                }
            }
            pageInfo{
                hasNextPage
                endCursor
            }
        }
        refundShippingLines(first :1){
            nodes{
                taxAmountSet{
                    presentmentMoney{
                        amount
                    }
                    shopMoney{
                        amount
                    }
                }
        subtotalAmountSet{
            presentmentMoney{
                amount
            }
            shopMoney{
                amount
            }
        }        
            }
        pageInfo{
            hasNextPage
            endCursor
        }
        }
        orderAdjustments(first: 200){
            nodes{
                reason
                id
                amountSet{
                    presentmentMoney{
                        amount
                    }
                    shopMoney{
                        amount
                    }
                }
                taxAmountSet {
                    presentmentMoney{
                        amount
                    }
                    shopMoney{
                        amount
                    }
                }
            }
            pageInfo{
                hasNextPage
                endCursor
        }
        }
        transactions(first: 10){
                nodes{
                    status
                    amountSet {
                        presentmentMoney {
                            amount
                            }
                        shopMoney {
                            amount
                        }
                    }
            }
             pageInfo {
                hasNextPage
                endCursor
            }
        }
      }

      returns(first: 10) {
        nodes {
        id
        name
        status
        totalQuantity
        decline {
          note
          reason
        }
        returnLineItems(first: 25) {
          nodes {
            __typename
            ... on ReturnLineItemType {
              id
              quantity
              refundableQuantity
              refundedQuantity
              returnReasonDefinition {
                id
                name
                handle
              }
              returnReasonNote
              customerNote
            }
            ... on ReturnLineItem {
              fulfillmentLineItem {
                id
                quantity
                lineItem {
                  id
                  sku
                  title
                  variant {
                    id
                  }
                }
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
        refunds(first: 10) {
          nodes {
            id
          }
        }
        reverseFulfillmentOrders(first: 4) {
          nodes {
            id
            status
            lineItems(first: 20) {
              nodes {
                id
                fulfillmentLineItem {
                  id
                }
                totalQuantity
                dispositions {
                  quantity
                  type
                  location {
                    id
                    name
                  }
                }
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      }

      risk{
         assessments {
          riskLevel
          provider {
            title
          }
          facts {
            description
            sentiment
          }
        }
        recommendation
      }
    }
  }
"""

GET_ORDERS_BY_IDS = """
query GetOrdersByIds($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on Order {
        id
        note
        name
        processedAt
        cancelledAt
        sourceName
        tags
        cancelReason
        displayFinancialStatus
        displayFulfillmentStatus
        paymentGatewayNames
        currencyCode
        presentmentCurrencyCode
        taxesIncluded
      
        metafields(first:250){
          nodes{
              id
              namespace
              key
              type
              value
              jsonValue
          }
          pageInfo{
              endCursor
              hasNextPage
          }
        }
      
        totalPriceSet{
          presentmentMoney{
              amount
          }
          shopMoney{
              amount
          }
        }

        billingAddress {
          name
          firstName
          lastName
          address1
          address2
          city
          phone
          company
          country
          countryCodeV2
          province
          provinceCode
          zip
        }

        shippingAddress {
          name
          firstName
          lastName
          address1
          address2
          city
          phone
          company
          country
          countryCodeV2
          province
          provinceCode
          zip
        }

        customer {
          note
          tags
          defaultEmailAddress{
              emailAddress
          }
          defaultPhoneNumber {
              phoneNumber
          }
          firstName
          lastName
          defaultAddress {
              name
              firstName
              lastName
              address1
              address2
              city
              phone
              company
              country
              countryCodeV2
              province
              provinceCode
              zip
          }
        }

        taxLines {
          title
          rate
          priceSet {
            presentmentMoney {
              amount
            }
            shopMoney {
              amount
            }
          }
        }

        lineItems(first: 250) {
            nodes {
              id
              name
              title
              quantity
              currentQuantity
              sku
              isGiftCard
              requiresShipping
              originalUnitPriceSet{
                  presentmentMoney{
                      amount
                  }
                  shopMoney{
                      amount
                  }
              }
              taxLines {
                  title
                  rate
                  priceSet {
                      presentmentMoney {
                          amount
                          }
                      shopMoney {
                          amount
                          }
                      }
              }

              duties {
                  id
                  taxLines {
                      rate
                      title
                      priceSet {
                          presentmentMoney {
                              amount
                          }
                          shopMoney {
                              amount
                          }
                      }
                  }
                  price{
                     presentmentMoney {
                      amount
                    }
                    shopMoney {
                      amount
                    }
                  }
              }

              discountAllocations {
                allocatedAmountSet {
                      presentmentMoney {
                          amount
                      }
                      shopMoney {
                          amount
                      }
                }
              }

              product {
                id
              }

              variant {
                id
                sku
                barcode
              }
            }

          pageInfo{
              hasNextPage
              endCursor
          }
        }

        fulfillments(first: 200){
          id
          status
          location{
              id
              name
          }
          trackingInfo{
              number
              company
          }
          fulfillmentLineItems(first: 150){
                  nodes{
                      id
                      lineItem{
                          id
                          isGiftCard
                          }
                      quantity
              }
              pageInfo{
                  hasNextPage
                  endCursor
          }
          }
        }

        shippingLines(first: 250) {
            nodes {
              id
              title
              originalPriceSet{
                  presentmentMoney{
                      amount
                  }
                  shopMoney{
                      amount
                  }
              }
              discountAllocations{
                  allocatedAmountSet{
                      presentmentMoney{
                          amount
                      }
                      shopMoney{
                          amount
                      }
                  }
              }
              taxLines {
                  title
                  rate
                  priceSet {
                      presentmentMoney {
                          amount
                      }
                      shopMoney {
                          amount
                      }
                  }
              }
          }
          pageInfo{
              hasNextPage
              endCursor
          }
        }

        transactions(first:10) {
          kind
          status
          gateway
          id
          paymentId
          amountSet {
            presentmentMoney {
              amount
            }
            shopMoney {
              amount
            }
          }
        }

        refunds(first:10){
          id
          note
          createdAt
          refundLineItems(first: 200){
              nodes{
                  id
                  quantity
                  lineItem{
                      id
                  }
              }
              pageInfo{
                  hasNextPage
                  endCursor
              }
          }
          refundShippingLines(first :1){
              nodes{
                  taxAmountSet{
                      presentmentMoney{
                          amount
                      }
                      shopMoney{
                          amount
                      }
                  }
          subtotalAmountSet{
              presentmentMoney{
                  amount
              }
              shopMoney{
                  amount
              }
          }        
              }
          pageInfo{
              hasNextPage
              endCursor
          }
          }
          orderAdjustments(first: 200){
              nodes{
                  reason
                  id
                  amountSet{
                      presentmentMoney{
                          amount
                      }
                      shopMoney{
                          amount
                      }
                  }
                  taxAmountSet {
                      presentmentMoney{
                          amount
                      }
                      shopMoney{
                          amount
                      }
                  }
              }
              pageInfo{
                  hasNextPage
                  endCursor
          }
          }
          transactions(first: 10){
                  nodes{
                      status
                      amountSet {
                          presentmentMoney {
                              amount
                              }
                          shopMoney {
                              amount
                          }
                      }
              }
               pageInfo {
                  hasNextPage
                  endCursor
              }
          }
        }

        returns(first: 10) {
          nodes {
          id
          name
          status
          totalQuantity
          decline {
            note
            reason
          }
          returnLineItems(first: 25) {
            nodes {
              __typename
              ... on ReturnLineItemType {
                id
                quantity
                refundableQuantity
                refundedQuantity
                returnReasonDefinition {
                  id
                  name
                  handle
                }
                returnReasonNote
                customerNote
              }
              ... on ReturnLineItem {
                fulfillmentLineItem {
                  id
                  quantity
                  lineItem {
                    id
                    sku
                    title
                    variant {
                      id
                    }
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
          refunds(first: 10) {
            nodes {
              id
            }
          }
          reverseFulfillmentOrders(first: 4) {
            nodes {
              id
              status
              lineItems(first: 20) {
                nodes {
                  id
                  fulfillmentLineItem {
                    id
                  }
                  totalQuantity
                  dispositions {
                    quantity
                    type
                    location {
                      id
                      name
                    }
                  }
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
        }

        risk{
           assessments {
            riskLevel
            provider {
              title
            }
            facts {
              description
              sentiment
            }
          }
          recommendation
        }
    }
  }
}
"""

GET_ORDERS_BY_DATE = """
query GetOrdersByDate(
    $ordersCursor: String,
    $queryFilter: String!) {

  orders(first: 250, after: $ordersCursor, query: $queryFilter) {
    edges {
      node {
      id
      note
      name
      processedAt
      cancelledAt
      sourceName
      tags
      cancelReason
      displayFinancialStatus
      displayFulfillmentStatus
      paymentGatewayNames
      currencyCode
      presentmentCurrencyCode
      taxesIncluded
      
      metafields(first:250){
        nodes{
            id
            namespace
            key
            type
            value
            jsonValue
        }
        pageInfo{
            endCursor
            hasNextPage
        }
      }

      totalPriceSet{
        presentmentMoney{
            amount
        }
        shopMoney{
            amount
        }
      }

      billingAddress {
        name
        firstName
        lastName
        address1
        address2
        city
        phone
        company
        country
        countryCodeV2
        province
        provinceCode
        zip
      }

      shippingAddress {
        name
        firstName
        lastName
        address1
        address2
        city
        phone
        company
        country
        countryCodeV2
        province
        provinceCode
        zip
      }

      customer {
        note
        tags
        defaultEmailAddress{
            emailAddress
        }
        defaultPhoneNumber {
            phoneNumber
        }
        firstName
        lastName
        defaultAddress {
            name
            firstName
            lastName
            address1
            address2
            city
            phone
            company
            country
            countryCodeV2
            province
            provinceCode
            zip
        }
      }

      taxLines {
        title
        rate
        priceSet {
          presentmentMoney {
            amount
          }
          shopMoney {
            amount
          }
        }
      }

      lineItems(first: 1) {
          nodes {
            id
            name
            title
            quantity
            currentQuantity
            sku
            isGiftCard
            requiresShipping
            originalUnitPriceSet{
                presentmentMoney{
                    amount
                }
                shopMoney{
                    amount
                }
            }
            taxLines {
                title
                rate
                priceSet {
                    presentmentMoney {
                        amount
                        }
                    shopMoney {
                        amount
                        }
                    }
            }

            duties {
                id
                taxLines {
                    rate
                    title
                    priceSet {
                        presentmentMoney {
                            amount
                        }
                        shopMoney {
                            amount
                        }
                    }
                }
                price{
                   presentmentMoney {
                    amount
                  }
                  shopMoney {
                    amount
                  }
                }
            }

            discountAllocations {
              allocatedAmountSet {
                    presentmentMoney {
                        amount
                    }
                    shopMoney {
                        amount
                    }
              }
            }

            product {
              id
            }

            variant {
              id
              sku
              barcode
            }
          }

        pageInfo{
            hasNextPage
            endCursor
        }
      }

      fulfillments(first: 50){
        id
        status
        location{
            id
            name
        }
        trackingInfo{
            number
            company
        }
        fulfillmentLineItems(first: 10){
                nodes{
                    id
                    lineItem{
                        id
                        isGiftCard
                        }
                    quantity
            }
            pageInfo{
                hasNextPage
                endCursor
        }
        }
      }

      shippingLines(first: 10) {
          nodes {
            id
            title
            originalPriceSet{
                presentmentMoney{
                    amount
                }
                shopMoney{
                    amount
                }
            }
            discountAllocations{
                allocatedAmountSet{
                    presentmentMoney{
                        amount
                    }
                    shopMoney{
                        amount
                    }
                }
            }
            taxLines {
                title
                rate
                priceSet {
                    presentmentMoney {
                        amount
                    }
                    shopMoney {
                        amount
                    }
                }
            }
        }
        pageInfo{
            hasNextPage
            endCursor
        }
      }

      transactions(first:10) {
        kind
        status
        gateway
        id
        paymentId
        amountSet {
          presentmentMoney {
            amount
          }
          shopMoney {
            amount
          }
        }
      }

      refunds(first:10){
        id
        note
        createdAt
        refundLineItems(first: 10){
            nodes{
                id
                quantity
                lineItem{
                    id
                }
            }
            pageInfo{
                hasNextPage
                endCursor
            }
        }
        refundShippingLines(first :10){
            nodes{
                taxAmountSet{
                    presentmentMoney{
                        amount
                    }
                    shopMoney{
                        amount
                    }
                }
        subtotalAmountSet{
            presentmentMoney{
                amount
            }
            shopMoney{
                amount
            }
        }        
            }
        pageInfo{
            hasNextPage
            endCursor
        }
        }
        orderAdjustments(first: 10){
            nodes{
                reason
                id
                amountSet{
                    presentmentMoney{
                        amount
                    }
                    shopMoney{
                        amount
                    }
                }
                taxAmountSet {
                    presentmentMoney{
                        amount
                    }
                    shopMoney{
                        amount
                    }
                }
            }
            pageInfo{
                hasNextPage
                endCursor
        }
        }
        transactions(first: 10){
                nodes{
                    status
                    amountSet {
                        presentmentMoney {
                            amount
                            }
                        shopMoney {
                            amount
                        }
                    }
            }
             pageInfo {
                hasNextPage
                endCursor
            }
        }
      }

      risk{
         assessments {
          riskLevel
          provider {
            title
          }
          facts {
            description
            sentiment
          }
        }
        recommendation
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

REFUND_ORDER = """
mutation RefundLineItem($input: RefundInput!, $idempotencyKey: String!) {
  refundCreate(input: $input) @idempotent(key: $idempotencyKey) {
   refund {
      id
      createdAt
      note
      duties{
        amountSet{
            presentmentMoney{
                amount
                currencyCode
            }
            shopMoney{
                amount
                currencyCode
            }
        }
      }
      orderAdjustments(first:200){
            nodes{
                reason
                id
                amountSet{
                    presentmentMoney{
                        amount
                    }
                    shopMoney{
                        amount
                    }
                }
                taxAmountSet {
                    presentmentMoney{
                        amount
                    }
                    shopMoney{
                        amount
                    }
                }
            }
        }

      refundLineItems(first: 200) {
        nodes {
          id
          lineItem{
            id
          }
          quantity
          restockType
        }
      }
      refundShippingLines(first: 200){ 
        nodes{
            id
            shippingLine{
                id
                code
            }
            subtotalAmountSet{
                presentmentMoney{
                    amount
                    currencyCode
                }
                shopMoney{
                    amount
                    currencyCode
                }
            }
        }
      }
      transactions(first: 200){
            nodes{
                 amountSet {
          presentmentMoney {
            amount
          }
          shopMoney {
            amount
          }
        }
            }
        }
    }
    order{
        displayFinancialStatus
        taxesIncluded
    }
    userErrors {
      field
      message
    }
  }
  }
"""

GET_TRANSACTION_BY_ORDER_ID = """
query GetTransactionByOrderId($orderId: ID!) {
  order(id: $orderId) {
    id
    transactions {
        kind
        status
        gateway
        id
        parentTransaction {
          id
        }
        paymentId
        amountSet {
          presentmentMoney {
            amount
            currencyCode
          }
          shopMoney {
            amount
            currencyCode
          }
        }
      }
  }
}
"""

GET_ORDER_REFUNDS = """
query GetOrdersRefund($orderId: ID!) {
  order(id: $orderId) {
    id
    name
    taxesIncluded
    refunds {
      id
      note
      createdAt

      refundLineItems(first: 200) {
        nodes {
          id
          quantity
          lineItem {
            id
          }
        }
      }

      refundShippingLines(first: 200) {
        nodes {
          shippingLine {
            code
          }
          subtotalAmountSet {
            presentmentMoney {
              amount
            }
            shopMoney {
              amount
            }
          }
        }
      }

      orderAdjustments(first: 200) {
        nodes {
          reason
          id
          amountSet {
            presentmentMoney {
              amount
            }
            shopMoney {
              amount
            }
          }
          taxAmountSet {
            presentmentMoney {
              amount
            }
            shopMoney {
              amount
            }
          }
        }
      }

      transactions(first: 200) {
        nodes {
          gateway
          id
          kind
          status
          amountSet {
            presentmentMoney {
              amount
            }
            shopMoney {
              amount
            }
          }
        }
      }
    }
  }
}
"""

GET_ORDER_LINE_AFTER_CURSOR = """
query GetOrderLinesAfterCursor($id: ID!, $cursor: String, $first: Int) {
  order(id: $id) {
  id
  lineItems(first: $first, after: $cursor) {
    nodes{
        id
        name
        title
        quantity
        sku
        isGiftCard
        requiresShipping
        originalUnitPriceSet{
            presentmentMoney{
                amount
                }
            shopMoney{
                amount
                }
            }
        taxLines {
            title
            rate
            priceSet {
                presentmentMoney {
                    amount
                }
                shopMoney {
                    amount
                }
            }
        }

        duties {
            id
            taxLines {
                rate
                title
                priceSet {
                    presentmentMoney {
                        amount
                    }
                    shopMoney {
                        amount
                    }
                }
            }
            price{
                presentmentMoney {
                amount
                }
                shopMoney {
                amount
                }
            }
        }

        discountAllocations {
            allocatedAmountSet {
                presentmentMoney {
                    amount
                }
                shopMoney {
                    amount
                }
            }
        }

        product {
            id
        }

        variant {
            id
            sku
            barcode
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

GET_FULFILLMENT_LINE_ITEMS_AFTER_CURSOR = """
query GetFulfillmentLinesAfterCursor($id: ID!, $cursor: String, $first: Int) {
  fulfillment(id: $id) {
  id
  fulfillmentLineItems(first: $first, after: $cursor) {
    nodes{
        id
        quantity
        lineItem{
            id
            isGiftCard
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

GET_SHIPPING_LINES_AFTER_CURSOR = """
query GetShippingLinesAfterCursor($id: ID!, $cursor: String, $first: Int) {
  order(id: $id) {
  id
  shippingLines(first: $first, after: $cursor) {
    nodes {
        id
        title
        originalPriceSet{
            presentmentMoney{
                amount
                }
            shopMoney{
                amount
                }
            }
        discountAllocations{
            allocatedAmountSet{
                    presentmentMoney{
                        amount
                    }
                    shopMoney{
                        amount
                    }
                }
            }
        taxLines {
            title
            rate
            priceSet {
                presentmentMoney {
                    amount
                    }
                shopMoney {
                    amount
                    }
                }
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

GET_REFUND_LINE_ITEMS_AFTER_CURSOR = """
query GetRefundLineItemsAfterCursor($id: ID!, $cursor: String, $first: Int) {
  refund(id: $id) {
  id
    refundLineItems(first: $first, after: $cursor) {
        nodes{
            id
            quantity
            lineItem{
                id
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

GET_REFUND_SHIPPING_LINES_AFTER_CURSOR = """
query GetRefundShippingLinesAfterCursor($id: ID!, $cursor: String, $first: Int) {
  refund(id: $id) {
  id
    refundShippingLines(first: $first, after: $cursor) {
        nodes{
            taxAmountSet{
                presentmentMoney{
                    amount
                }
                shopMoney{
                    amount
                }
            }
            subtotalAmountSet{
                presentmentMoney{
                    amount
                }
                shopMoney{
                    amount
                }
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

GET_ORDER_ADJUSTMENTS_AFTER_CURSOR = """
query GetOrderAdjustmentsAfterCursor($id: ID!, $cursor: String, $first: Int) {
  refund(id: $id) {
  id
    orderAdjustments(first: $first, after: $cursor) {
        nodes{
            reason
            id
            amountSet{
                presentmentMoney{
                    amount
                }
                shopMoney{
                    amount
                }
            }
            taxAmountSet {
                presentmentMoney{
                    amount
                }
                shopMoney{
                    amount
                }
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

GET_CUSTOMERS = """
query GetCustomer($customerID: ID!) {
  customer(id: $customerID){
    id
    firstName
    lastName
    createdAt
    updatedAt
    defaultEmailAddress{
            emailAddress
    }
    defaultPhoneNumber{
        phoneNumber
    }
    state
    note
    tags
    defaultAddress{
        phone
        address1
        address2
        firstName
        lastName
        company
        country
        countryCodeV2
        province
        provinceCode
        country
        zip
    }
    metafields(first:250)
    {
        nodes{
            id
            namespace
            key
            type
            value
            jsonValue
        }
        pageInfo{
          hasNextPage
          endCursor
        }
    }
  }
}
"""

GET_CUSTOMERS_BY_IDS = """
query GetCustomersByIds($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on Customer {
      id
      firstName
      lastName
      createdAt
      updatedAt
      defaultEmailAddress{
              emailAddress
      }
      defaultPhoneNumber{
          phoneNumber
      }
      state
      note
      tags
      defaultAddress{
          phone
          address1
          address2
          firstName
          lastName
          company
          country
          countryCodeV2
          province
          provinceCode
          country
          zip
      }
      metafields(first:250)
      {
          nodes{
              id
              namespace
              key
              type
              value
              jsonValue
          }
          pageInfo{
            hasNextPage
            endCursor
          }
      }
    }
  }
}
"""

GET_MULTIPLE_CUSTOMERS = """
query CustomersByDate($customersCursor: String, $query: String!) {
  customers(query: $query, first: 200, after: $customersCursor) {
    edges {
      node {
        id
        firstName
        lastName
        defaultEmailAddress{
            emailAddress
        }
        defaultPhoneNumber {
         phoneNumber 
         }
        createdAt
        updatedAt
        state
        note
        tags
        defaultAddress {
          phone
          address1
          address2
          firstName
          lastName
          company
          country
          countryCodeV2
          province
          provinceCode
          zip
        }
        metafields(first:250)
        {
          nodes{
            id
            namespace
            key
            type
            value
            jsonValue
          }
           pageInfo{
             hasNextPage
             endCursor
           }
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

MARK_ORDER_AS_PAID = """
mutation orderMarkAsPaid($input: OrderMarkAsPaidInput!) {
  orderMarkAsPaid(input: $input) {
    order {
      displayFinancialStatus
    }
    userErrors {
      field
      message
    }
  }
}
"""

SHOPIFY_ACCESS_SCOPES = """
query GetAccessScopes
{
  appInstallation {
    accessScopes {
      handle
    }
  }
}
"""

INVENTORY_BULK_TOGGLE_ACTIVATION = """
mutation inventoryBulkToggleActivation($inventoryItemId: ID!, $inventoryItemUpdates: [InventoryBulkToggleActivationInput!]!) {
  inventoryBulkToggleActivation(
    inventoryItemId: $inventoryItemId
    inventoryItemUpdates: $inventoryItemUpdates
  ) {
    inventoryItem {
      id
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

INVENTORY_SET_QUANTITIES = """
mutation inventorySetQuantities($input: InventorySetQuantitiesInput!, $idempotencyKey: String!) {
  inventorySetQuantities(input: $input) @idempotent(key: $idempotencyKey) {
    userErrors {
      field
      message
    }
  }
}
"""

ORDER_RISK = """
query GetOrderRisk($id: ID!) {
  order(id:$id) {
    risk {
        recommendation
        assessments {
            riskLevel
            provider {
                title
            }
            facts {
                description
                sentiment
            }
        }      
    }
  }
}
"""

GET_TRANSACTIONS_FOR_PAYOUT = """
query GetTransactionsForPayout($payoutQuery: String!) {
  shopifyPaymentsAccount {
    balanceTransactions(first: 250, query: $payoutQuery) {
        edges{
            node {
                id
                type
                amount {
                    amount
                    currencyCode
                }
                net {
                    amount
                }
                fee{
                    amount
                }
                associatedPayout {
                    id
                    status
                }
                sourceType
                transactionDate
                associatedOrder {
                    id
                }
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

GET_PAYOUTS_BY_DATE_RANGE = """
query GetPayoutsByDateRange($queryFilter: String!) {
  shopifyPaymentsAccount {
    payouts(first: 200, query: $queryFilter) {
        edges{
            node {
                id
                legacyResourceId
                issuedAt
                net {
                amount
                currencyCode
                }
                summary{
                    chargesFee{
                        amount
                    }
                    refundsFee{
                        amount
                    }
                    adjustmentsFee{
                        amount
                    }
                }
                status
                transactionType
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

GET_VARIANT_PUBLICATIONS = """
query GetVariantPublications($queryFilter: String!) {
  productVariants(first: 200, query: $queryFilter) {
    nodes {
      id
      resourcePublicationsV2(first: 20) {
        nodes {
          publication {
            id
          }
          isPublished
        }
      }
    }
  }
}
"""

GET_PRODUCT_PUBLICATIONS = """
query GetProductsPublicationDetails($queryFilter: String!) {
  products(first: 250, query: $queryFilter) {
    nodes {
      id
      productType
      category {
        id
        name
        fullName
      }
      resourcePublications(first:100) {
      nodes {
        isPublished
        publication {
          id
          catalog {
            ... on AppCatalog {
              apps(first: 1) {
                nodes {
                  title
                }
              }
            }
          }
        }
      }
    }
    }
  }
}
"""

CREATE_SHOPIFY_WEBHOOK = """
mutation webhookSubscriptionCreate($topic: WebhookSubscriptionTopic!, $webhookSubscription: WebhookSubscriptionInput!) {
  webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
    webhookSubscription {
      id
      format
      topic
      uri
    }
    userErrors {
      field
      message
    }
  }
}
"""

DELETE_SHOPIFY_SUBSCRIPTION = """
mutation webhookSubscriptionDelete($id: ID!) {
  webhookSubscriptionDelete(id: $id) {
    deletedWebhookSubscriptionId
    userErrors {
      field
      message
    }
  }
}
"""

GRAPHQL_QUERY_FIND_WEBHOOKS = """
query GetWebhooks($count: Int!) {
  webhookSubscriptions(first: $count) {
    edges {
      node {
        id
        topic
        uri
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

GET_WEHBOOK_SUBSCRIPTION = """
query GetWebhookSubscription($id: ID!) {
  webhookSubscription(id: $id) {
    id
    topic
    uri
  }
}
"""

GET_WEBHOOK_SUBSCRIPTION_USING_URI_AND_TOPIC = """
query webhookSubscriptionsByUriAndTopic($uri: String!, $topic: [WebhookSubscriptionTopic!]) {
  webhookSubscriptions(first: 250, uri: $uri, topics: $topic) {
    edges {
      node {
        id
        topic
        uri
      }
    }
  }
}
"""

CREATE_FULFILLMENT = """
mutation fulfillmentCreate($fulfillment: FulfillmentInput!, $message: String) {
  fulfillmentCreate(fulfillment: $fulfillment, message: $message) {
    fulfillment {
      id
      fulfillmentOrders(first:10){
        nodes{
          id
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

CHANGE_LOCATION_OF_FULFILLMENT_ORDER = """
mutation fulfillmentOrderMove($id: ID!, $newLocationId: ID!) {
  fulfillmentOrderMove(id: $id, newLocationId: $newLocationId) {
   movedFulfillmentOrder {
        id
        status
      }
      originalFulfillmentOrder {
        id
        status
      }
    userErrors {
      field
      message
    }
  }
}
"""

GET_INVENTORY_LOCATION_WISE = """
query GetMultipleLocationInventoryLevels(
 $locationIds: [ID!]!
 $inventoryQuery: String!) {
 nodes(ids: $locationIds) {
   ... on Location {
     id
     name
     inventoryLevels(first: 250, query: $inventoryQuery) {
       nodes {
         item { id sku }
         location { id name }
         quantities(names: ["available"]) { name quantity }
       }
       pageInfo {
         hasNextPage
         endCursor
       }
     }
   }
 }
}
"""

GET_INVENTORY_LOCATION_WISE_AFTER_CURSOR = """
query GetMultipleLocationInventoryLevels($id: ID!, $cursor: String, $queryFilter: String) {
  location(id: $id) {
    id
    name
    inventoryLevels(first: 250, after: $cursor, query: $queryFilter) {
      nodes {
        item {
          id
          sku
        }
        location {
          id
          name
        }
        quantities(names: ["available"]) {
          name
          quantity
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

PUBLISH_COLLECTION = """
mutation publishCollection($id: ID!, $publications: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $publications) {
    publishable {
      __typename
      ... on Collection {
        updatedAt
        resourcePublications(first: 250) {
          nodes {
            publication {
              id
                channels (first: 10){
                nodes {
                  id
                  name
                }
              }
            }
            isPublished
          }
          pageInfo {
            hasNextPage
            endCursor
          }
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

UNPUBLISH_COLLECTION = """
mutation collectionUnpublish($id: ID!, $publications: [PublicationInput!]!) {
  publishableUnpublish(id: $id, input: $publications) {
    publishable {
      __typename
      ... on Collection {
        updatedAt
        resourcePublications(first: 250) {
          nodes {
            publication {
              id
                channels (first: 10){
                nodes {
                  id
                  name
                }
              }
            }
            isPublished
          }
          pageInfo {
            hasNextPage
            endCursor
          }
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

GET_COLLECTION_PRODUCT_AFTER_CURSOR = """
query GetCollectionWithProducts($id: ID!, $cursor: String) {
  collection(id: $id) {
    id
    title
    products(first: 250, after: $cursor) {
      nodes {
        id
        title
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""

JOB_STATUS = """
query CheckJobStatus($jobId: ID!) {
  job(id: $jobId) {
    id
    done
  }
}
"""

GET_COLLECTION_PUBLICATION = """
query GetCollectionsByIds($ids: [ID!]!) {
  nodes(ids: $ids) {
    id
    ... on Collection {
      title
      id
      handle
      updatedAt
      descriptionHtml
      sortOrder
      templateSuffix
      image {
        url
      }
      resourcePublications(first: 250) {
        nodes {
          publication {
            id
            channels(first: 10) {
              nodes {
                id
                name
              }
            }
          }
          isPublished
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
      products(first: 250) {
        edges {
          node {
            id
            title
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}
"""

FETCH_METAFIELD_DEFINITIONS = """
query MetafieldDefinitions($ownerType: MetafieldOwnerType!, $first: Int, $metafieldResourceCursor: String ) {
  metafieldDefinitions(ownerType: $ownerType, first: $first,  after: $metafieldResourceCursor) {
    nodes {
      name
      namespace
      key
      type {
        name
      }
      validations {
        name
        value
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

FETCH_PRODUCT_AND_VARIANT_METAFIELDS = """
query ProductWithAllMetafields($productId: ID!) {
  product(id: $productId) {
    id
    metafields(first: 250) {
      edges {
        node {
          id
          namespace
          key
          type
          value
          jsonValue
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
    variants(first: 250) {
      nodes {
        id
        title
        metafields(first: 250) { 
          edges {
            node {
              id
              namespace
              key
              type
              value
              jsonValue
            }
          }
        pageInfo {
            hasNextPage
            endCursor
        }
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

GET_REMAINING_PRODUCT_METAFIELD = """
query GetProductMetafields($productId: ID! $cursor: String $first: Int) {
  product(id: $productId) {
    metafields(first: $first, after: $cursor) {
      edges {
        node {
          id
          namespace
          key
          type
          value
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

GET_REMAINING_PRODUCT_VARIANT_METAFIELD = """
query GetVariantMetafields($variantId: ID! $cursor: String $first: Int) {
  productVariant(id: $variantId) {
    metafields(first: $first, after: $cursor) {
      edges {
        node {
          id
          namespace
          key
          type
          value
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

UPDATE_RESOURCE_METAFIELDS = """
mutation SetMetafields($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields {
      id
      key
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

DELETE_SPECIFIC_METAFIELD_VALUE = """
mutation DeleteSpecificMetafieldValue($metafields: [MetafieldIdentifierInput!]!) {
  metafieldsDelete(metafields: $metafields) {
    deletedMetafields { 
      key 
      namespace 
      ownerId 
    }
    userErrors { 
      field 
      message 
    }
  }
}
"""

GET_PRODUCTS_BY_IDS = """
query GetProductsByIds($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on Product {
     id
    title
    description
    descriptionHtml
    productType
    category {
      id
      name
      fullName      
    }
    tags
    variants(first: 250) {
      nodes {
        id
        barcode
        sku
        price
        taxable
        title
        selectedOptions {
          name
          value
        }
        inventoryItem {
          id
          tracked
          measurement {
            weight {
              unit
              value
            }
          }
        }
        inventoryPolicy
        media(first: 2) {
          nodes {
            id
            alt
            mediaContentType
            preview {
              image {
                id
                url
              }
            }
          }
        }
        createdAt
        updatedAt
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
    options {
      name
      values
    }
    resourcePublications(first: 100) {
      nodes { 
        isPublished
        publication {
            id
            catalog {
              ... on AppCatalog {
                apps(first: 100) {
                  nodes {
                    title
                  }
                }
              }
            }
          }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
    media(first: 250) {
      nodes {
        id
        alt
        mediaContentType
        preview {
          image {
            id
            url
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
    createdAt
    updatedAt
    }
  }
}
"""

GET_REMAINING_ORDER_METAFIELD = """
query GetOrderMetafields($id: ID!, $cursor: String, $first: Int) {
  order(id: $id) {
    id
    metafields(first: $first, after: $cursor) {
      nodes {
        id
        namespace
        key
        type
        value
        jsonValue
      }
      pageInfo {
        endCursor
        hasNextPage
      }
    }
  }
}
"""

GET_REMAINING_CUSTOMER_METAFIELD = """
query GetCustomerMetafields($id: ID!, $cursor: String, $first: Int) {
  customer(id: $id) {
    id
    metafields(first: $first, after: $cursor) {
      nodes {
        id
        namespace
        key
        type
        value
        jsonValue
      }
      pageInfo {
        endCursor
        hasNextPage
      }
    }
  }
}
"""

GET_IMPORT_CATALOGS = """
query GetImportCatalogs($cursor: String, $query: String) {
  catalogs(first: 20, after: $cursor, query: $query) {
    nodes {
      __typename
      id
      title
      status
      priceList {
        id
        name
        currency
        parent {
          adjustment {
            value
            type
          }
          settings {
            compareAtMode
          }
        }
        prices(first: 50) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            originType
            variant {
              legacyResourceId
              product {
                legacyResourceId
              }
            }
            price {
              amount
              currencyCode
            }
            compareAtPrice {
              amount
              currencyCode
            }
            quantityPriceBreaks(first: 30) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                id
                minimumQuantity
                price {
                  amount
                  currencyCode
                }
              }
            }
          }
        }
        quantityRules(first: 250) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            minimum
            maximum
            increment
            originType
            isDefault
            productVariant {
              legacyResourceId
              product {
                legacyResourceId
              }
            }
          }
        }
      }
      publication {
        id
        autoPublish
        includedProducts(first: 250, query: "status:active,draft") {
          nodes {
            legacyResourceId
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
      ... on MarketCatalog {
        markets(first: 25) {
          nodes {
            id
            name
            status
            type
          }
        }
      }
      ... on CompanyLocationCatalog {
        companyLocations(first: 25) {
          nodes {
            id
            name
            company{
                id
                name
            }
          }
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

GET_CATALOG_PRICES_PAGE = """
query getCatalogPrices($id: ID!, $cursor: String) {
  priceList(id: $id) {
    id
    prices(first: 250, after: $cursor) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        originType
        variant {
          legacyResourceId
          product {
              legacyResourceId
            }
        }
        quantityPriceBreaks(first: 30) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              id
              minimumQuantity
              price {
                amount
                currencyCode
              }
            }
          }
        price {
          amount
          currencyCode
        }
        compareAtPrice {
          amount
          currencyCode
        }
      }
    }
  }
}
"""

GET_INCLUDED_PRODUCTS_PAGE = """
query GetPublicationIncludedProductsPage($id: ID!, $cursor: String) {
  publication(id: $id) {
    id
    includedProducts(first: 250, after: $cursor, query: "status:active,draft") {
      nodes {
        legacyResourceId
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""

GET_CATALOG_QUANTITY_RULES_PAGE = """
query getCatalogQuantityRules($id: ID!, $cursor: String) {
  priceList(id: $id) {
    id
    quantityRules(first: 250, after: $cursor) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        minimum
        maximum
        increment
        originType
        isDefault
        productVariant {
          legacyResourceId
          product {
            legacyResourceId
          }
        }
      }
    }
  }
}
"""

GET_CATALOG_MARKETS_PAGE = """
query GetCatalogMarkets($id: ID!, $cursor: String) {
  catalog(id: $id) {
    id
    __typename
    ... on MarketCatalog {
      markets(first: 20, after: $cursor) {
        nodes {
            status
            type
            id
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}
"""

UPDATE_CATALOG = """
mutation catalogUpdate($id: ID!, $input: CatalogUpdateInput!) {
  catalogUpdate(id: $id, input: $input) {
    catalog {
      id
      title
      status
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

UPDATE_PUBLICATION = """
mutation publicationUpdate($id: ID!, $input: PublicationUpdateInput!) {
  publicationUpdate(id: $id, input: $input) {
    publication {
      id
      autoPublish
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

UPDATE_PRICE_LIST = """
mutation priceListUpdate($id: ID!, $input: PriceListUpdateInput!) {
  priceListUpdate(id: $id, input: $input) {
    priceList {
      id
      parent {
        adjustment {
          value
          type
        }
        settings {
          compareAtMode
        }
      }
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

QUANTITY_PRICING_BY_VARIANT_UPDATE = """
mutation quantityPricingByVariantUpdate($priceListId: ID!, $input: QuantityPricingByVariantUpdateInput!) {
  quantityPricingByVariantUpdate(priceListId: $priceListId, input: $input) {
    productVariants {
      id
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

QUANTITY_RULES_DELETE = """
mutation quantityRulesDelete($priceListId: ID!, $variantIds: [ID!]!) {
  quantityRulesDelete(priceListId: $priceListId, variantIds: $variantIds) {
    deletedQuantityRulesVariantIds
    userErrors {
      field
      message
      code
    }
  }
}
"""

# ----------------------------------------------------------------------------
# Returns (Shopify Admin GraphQL — Return API)
# Reference: https://shopify.dev/docs/api/admin-graphql/latest/objects/Return
# Field selections below are tailored to the shopify.return.ts and
# shopify.return.line.ts models defined in this module. Update both
# the model and the query if more fields are needed.
# ----------------------------------------------------------------------------

LIST_ORDER_RETURNS_BY_DATE = """
query teqstarsListOrderReturns($searchQuery: String!, $pageSize: Int!, $afterCursor: String) {
  orders(first: $pageSize, query: $searchQuery, after: $afterCursor) {
    nodes {
      id
      name
      returns(first: 50) {
        nodes {
          id
          name
          status
          totalQuantity
          decline { note reason }
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

GET_ORDER_RETURNS_WITH_LINES_BY_DATE = """
query teqstarsOrderReturnsWithLines($searchQuery: String!, $afterCursor: String) {
  orders(first: 250, query: $searchQuery, after: $afterCursor) {
    nodes {
      id
      returns(first: 2) {
        nodes {
          id
          name
          status
          totalQuantity
          decline {
            note
            reason
          }
          returnLineItems(first: 25) {
            nodes {
              __typename
              ... on ReturnLineItemType {
                id
                quantity
                refundableQuantity
                refundedQuantity
                returnReasonNote
                customerNote
                returnReasonDefinition {
                  id
                  name
                  handle
                }
              }
              ... on ReturnLineItem {
                fulfillmentLineItem {
                  id
                  quantity
                  lineItem {
                    id
                    sku
                    title
                    variant {
                      id
                    }
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
          refunds(first: 3) {
            nodes {
              id
            }
          }
          reverseFulfillmentOrders(first: 2) {
            nodes {
              id
              status
              lineItems(first: 20) {
                nodes {
                  id
                  totalQuantity
                  fulfillmentLineItem {
                    id
                  }
                  dispositions {
                    quantity
                    type
                    location {
                      id
                      name
                    }
                  }
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
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

GET_ORDER_RETURNS_AFTER_CURSOR = """
query teqstarsOrderReturnsAfterCursor($id: ID!, $cursor: String) {
  order(id: $id) {
    id
    returns(first: 20, after: $cursor) {
      nodes {
        id
        name
        status
        totalQuantity
        decline {
          note
          reason
        }
        returnLineItems(first: 30) {
          nodes {
            __typename
            ... on ReturnLineItemType {
              id
              quantity
              refundableQuantity
              refundedQuantity
              returnReasonDefinition {
                id
                name
                handle
              }
              returnReasonNote
              customerNote
            }
            ... on ReturnLineItem {
              fulfillmentLineItem {
                id
                quantity
                lineItem {
                  id
                  sku
                  title
                  variant {
                    id
                  }
                }
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
        refunds(first: 10) {
          nodes {
            id
          }
        }
        reverseFulfillmentOrders(first: 20) {
          nodes {
            id
            status
            lineItems(first: 30) {
              nodes {
                id
                totalQuantity
                fulfillmentLineItem {
                  id
                }
                dispositions {
                  quantity
                  type
                  location {
                    id
                    name
                  }
                }
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
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

GET_RETURN_REVERSE_FULFILLMENT_ORDERS_AFTER_CURSOR = """
query teqstarsReturnRfoAfterCursor($id: ID!, $cursor: String) {
  return(id: $id) {
    id
    reverseFulfillmentOrders(first: 100, after: $cursor) {
      nodes {
        id
        status
        lineItems(first: 100) {
          nodes {
            id
            totalQuantity
            fulfillmentLineItem {
              id
            }
            dispositions {
              quantity
              type
              location {
                id
                name
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
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

GET_RFO_LINE_ITEMS_AFTER_CURSOR = """
query teqstarsRfoLineItemsAfterCursor($id: ID!, $cursor: String) {
  reverseFulfillmentOrder(id: $id) {
    id
    lineItems(first: 250, after: $cursor) {
      nodes {
        id
        totalQuantity
        fulfillmentLineItem {
          id
        }
        dispositions {
          quantity
          type
          location {
            id
            name
          }
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

GET_RETURN_LINE_ITEMS_AFTER_CURSOR = """
query teqstarsReturnLineItemsAfterCursor($id: ID!, $cursor: String) {
  return(id: $id) {
    id
    returnLineItems(first: 250, after: $cursor) {
      nodes {
        __typename
        ... on ReturnLineItemType {
          id
          quantity
          refundableQuantity
          refundedQuantity
          returnReasonDefinition {
            id
            name
            handle
          }
          returnReasonNote
          customerNote
        }
        ... on ReturnLineItem {
          fulfillmentLineItem {
            id
            quantity
            lineItem {
              id
              sku
              title
              variant {
                id
              }
            }
          }
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

GET_SHOPIFY_RETURN_DETAILS = """
query teqstarsGetReturn($returnId: ID!) {
  return(id: $returnId) {
    id
    name
    status
    totalQuantity
    order {
      id
      name
      taxesIncluded
      fulfillments(first: 100) {
        id
        location {
          id
          name
        }
        fulfillmentLineItems(first: 250) {
          edges {
            node {
              id
              lineItem {
                id
              }
            }
          }
        }
      }
    }
    decline {
      note
      reason
    }
    returnLineItems(first: 250) {
      nodes {
        __typename
        ... on ReturnLineItemType {
          id
          quantity
          refundableQuantity
          refundedQuantity
          returnReasonDefinition { 
            id 
            name 
            handle 
          }
          returnReasonNote
          customerNote
        }
        ... on ReturnLineItem {
          fulfillmentLineItem {
            id
            quantity
            lineItem {
              id
              sku
              title
              variant {
                id
              }
            }
          }
        }
      }
    }
    refunds(first: 250) {
      nodes {
        id
        note
        createdAt
        refundLineItems(first: 250) {
          nodes {
            id
            quantity
            lineItem { id }
          }
        }
        refundShippingLines(first: 250) {
          nodes {
            taxAmountSet {
              presentmentMoney { 
                amount 
              }
              shopMoney { 
                amount 
              }
            }
            subtotalAmountSet {
              presentmentMoney { 
                amount 
              }
              shopMoney { 
                amount 
              }
            }
          }
        }
        orderAdjustments(first: 250) {
          nodes {
            reason
            id
            amountSet {
              presentmentMoney { 
                amount 
              }
              shopMoney { 
                amount 
              }
            }
            taxAmountSet {
              presentmentMoney { 
                amount 
              }
              shopMoney { 
                amount 
              }
            }
          }
        }
        transactions(first: 250) {
          nodes {
            status
            amountSet {
              presentmentMoney { 
                amount 
              }
              shopMoney { 
                amount 
              }
            }
          }
        }
      }
    }

    reverseFulfillmentOrders(first: 10) {
      nodes {
        id
        status
         lineItems(first: 250) {
          nodes {
            id
            fulfillmentLineItem{
                id
            }
            totalQuantity
            dispositions {
              quantity
              type
              location {
                id
                name
              }
            }
          }
        }  
      }
    }
  }
}
"""

GET_RETURNABLE_FULFILLMENTS_FOR_ORDER = """
query teqstarsReturnableFulfillments($orderGid: ID!, $maxFulfillments: Int!) {
  returnableFulfillments(orderId: $orderGid, first: $maxFulfillments) {
    nodes {
      id
      fulfillment {
        id
        location {
          id
        }
      }
      returnableFulfillmentLineItems(first: 250) {
        nodes {
          quantity
          fulfillmentLineItem {
            id
            quantity
            lineItem {
              id
              sku
              title
              variant {
                id
              }
            }
          }
        }
      }
    }
  }
}
"""

RETURN_CREATE_FROM_ODOO = """
mutation teqstarsReturnCreate($returnInput: ReturnInput!) {
  returnCreate(returnInput: $returnInput) {
    return {
      id
      name
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""

RETURN_REQUEST_APPROVE_FROM_ODOO = """
mutation teqstarsReturnApproveRequest($input: ReturnApproveRequestInput!) {
  returnApproveRequest(input: $input) {
    return {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""

RETURN_REQUEST_DECLINE_FROM_ODOO = """
mutation teqstarsReturnDeclineRequest($input: ReturnDeclineRequestInput!) {
  returnDeclineRequest(input: $input) {
    return {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""

RETURN_PROCESS_FROM_ODOO = """
mutation teqstarsReturnProcess($input: ReturnProcessInput!) {
  returnProcess(input: $input) {
    return {
      id
      name
      status
      totalQuantity
      order { id name taxesIncluded }
      decline { note reason }
      returnLineItems(first: 250) {
        nodes {
          __typename
          ... on ReturnLineItemType {
            id
            quantity
            refundableQuantity
            refundedQuantity
            returnReasonDefinition { 
                id 
                name 
                handle 
            }
            returnReasonNote
            customerNote
          }
          ... on ReturnLineItem {
            fulfillmentLineItem {
              id
              quantity
              lineItem { 
              id 
              sku 
              title 
              variant { 
                id 
              } 
              }
            }
          }
        }
      }
      refunds(first: 250) {
        nodes {
          id
          note
          createdAt
          refundLineItems(first: 250) {
            nodes { id quantity lineItem { id } }
          }
          refundShippingLines(first: 250) {
            nodes {
              taxAmountSet { 
              presentmentMoney { 
                amount 
              } 
              shopMoney { 
                amount 
              } 
              }
              subtotalAmountSet { 
              presentmentMoney { 
                amount 
              } 
              shopMoney { 
                amount 
              } 
              }
            }
          }
          orderAdjustments(first: 250) {
            nodes {
              reason
              id
              amountSet { 
              presentmentMoney { 
                amount 
              } 
              shopMoney { 
                amount 
              }  
              }
              taxAmountSet { 
              presentmentMoney { 
                amount 
              } 
              shopMoney { 
                amount 
              } 
              }
            }
          }
          transactions(first: 250) {
            nodes {
              status
              amountSet { 
              presentmentMoney { 
                amount 
              } 
              shopMoney { 
                amount 
              } 
              }
            }
          }
        }
      }
      reverseFulfillmentOrders(first: 10) {
        nodes {
          id
          status
          lineItems(first: 250) {
            nodes {
              id
              fulfillmentLineItem { id }
              totalQuantity
              dispositions {
                quantity
                type
                location { 
                  id 
                  name 
                }
              }
            }
          }
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

RETURN_CLOSE_FROM_ODOO = """
mutation teqstarsReturnClose($id: ID!) {
  returnClose(id: $id) {
    return {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""

RETURN_CANCEL_FROM_ODOO = """
mutation teqstarsReturnCancel($id: ID!) {
  returnCancel(id: $id) {
    return {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""

FETCH_MULTIPLE_RETURN_DETAILS = """
query MultipleReturnsByIds($returnIds: [ID!]!) {
  nodes(ids: $returnIds) {
    __typename
    ... on Return {
      id
      name
      status
      totalQuantity

      order {
        id
        name
        taxesIncluded
        fulfillments(first: 100) {
          id
          location {
            id
            name
          }
          fulfillmentLineItems(first: 250) {
            edges {
              node {
                id
                lineItem {
                  id
                }
              }
            }
          }
        }
      }

      decline {
        note
        reason
      }

      returnLineItems(first: 250) {
        nodes {
          __typename
          ... on ReturnLineItemType {
            id
            quantity
            refundableQuantity
            refundedQuantity
            returnReasonDefinition { 
             id 
             name 
             handle 
            }          
            returnReasonNote
            customerNote
          }
          ... on ReturnLineItem {
            fulfillmentLineItem {
              id
              quantity
              lineItem {
                id
                sku
                title
                variant {
                  id
                }
              }
            }
          }
        }
      }

      refunds(first: 250) {
        nodes {
          id
          note
          createdAt

          refundLineItems(first: 250) {
            nodes {
              id
              quantity
              lineItem { id }
            }
          }

          refundShippingLines(first: 250) {
            nodes {
              taxAmountSet {
                presentmentMoney { amount }
                shopMoney { amount }
              }
              subtotalAmountSet {
                presentmentMoney { amount }
                shopMoney { amount }
              }
            }
          }

          orderAdjustments(first: 250) {
            nodes {
              reason
              id
              amountSet {
                presentmentMoney { amount }
                shopMoney { amount }
              }
              taxAmountSet {
                presentmentMoney { amount }
                shopMoney { amount }
              }
            }
          }

          transactions(first: 250) {
            nodes {
              status
              amountSet {
                presentmentMoney { amount }
                shopMoney { amount }
              }
            }
          }
        }
      }

      reverseFulfillmentOrders(first: 10) {
        nodes {
          id
          status
          lineItems(first: 250) {
            nodes {
              id
              fulfillmentLineItem {
                id
              }
              totalQuantity
              dispositions {
                quantity
                type
                location {
                  id
                  name
                }
              }
            }
          }  
        }
      }
    }
  }
}
"""

RETURN_REASON_DEFINITIONS = """
query teqstarsReturnReasonDefinitions($handles: [String!]) {
  returnReasonDefinitions(first: 250, handles: $handles) {
    edges {
      node {
        id
        name
        handle
        deleted
      }
    }
  }
}
"""

GET_MARK_AS_PAID_AUTHORIZE_CAPTURE_PAYMENT = """
mutation captureAuthorizedPayment($input: OrderCaptureInput!) {
  orderCapture(input: $input) {
    transaction {
      id
      kind
      status
      amountSet {
        presentmentMoney {
          amount
          currencyCode
        }
      }
      order {
        id
        displayFinancialStatus
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

GET_BULK_OPERATION_BY_ID = """
query getBulkOperationQueryStatus($id: ID!) {
  node(id: $id) {
    ... on BulkOperation {
      id
      status
      url
      errorCode
    }
  }
}
"""

STAGED_UPLOADS_CREATE = """
mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets {
      url
      resourceUrl
      parameters {
        name
        value
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

BULK_MUTATION_RUN = """
mutation bulkOperationRunMutation($mutation: String!, $stagedUploadPath: String!, $clientIdentifier: String) {
  bulkOperationRunMutation(mutation: $mutation, stagedUploadPath: $stagedUploadPath, clientIdentifier: $clientIdentifier) {
    bulkOperation {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""

BULK_OPERATION_PRODUCT_SET = """
mutation call($input: ProductSetInput!, $identifier: ProductSetIdentifiers) {
  productSet(input: $input, synchronous: true, identifier: $identifier) {
    product {
      id
      handle
      title
      status
      createdAt
      updatedAt
      variantsCount {
        count
      }
      variants(first: 100) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          sku
          barcode
          price
          taxable
          inventoryPolicy
          inventoryQuantity
          inventoryItem {
            id
            tracked
            countryCodeOfOrigin
            harmonizedSystemCode
            measurement {
              weight { unit value }
            }
          }
          createdAt
          updatedAt
        }
      }
    }
    userErrors { field message code }
  }
}
"""

BULK_OPERATION_UPDATE_SALES_CHANNEL = """
mutation updateChannels(
  $id: ID!,
  $publishInput: [PublicationInput!]!,
  ) {

  publish: publishablePublish(
    id: $id,
    input: $publishInput
  ) {
    publishable { ... on Product { id } }
    userErrors {
      field
      message
    }
  }
}
"""

BULK_OPERATION_UPDATE_SALES_CHANNEL_UNPUBLISH = """
mutation updateChannels($id: ID!, $unpublishInput: [PublicationInput!]!)
    {
        unpublish: publishableUnpublish(id: $id, input: $unpublishInput)
        {
            publishable { ... on Product { id } }
                userErrors {
                  field
                  message
                }
        }
    }
"""

# ----------------------------------------------------------------------------
# Collections (Shopify Admin GraphQL — 2026-07 sources model)
# Reference: https://shopify.dev/docs/api/admin-graphql/latest/objects/Collection
# Task: T8887 - Reads and writes go through `sources`: the deprecated `ruleSet` and
# `input:` shape cannot express multiple sources, exclusions or multi-value conditions.
# Import pages hold 50 collections: 100 goes over Shopify's 1000-point query cost limit.
# ----------------------------------------------------------------------------

GET_IMPORT_COLLECTIONS_WITH_SOURCES = """
query GetImportCollections($cursor: String) {
  collections(first: 50, after: $cursor) {
    edges {
      node {
        id
        title
        handle
        updatedAt
        descriptionHtml
        sortOrder
        templateSuffix
        image {
          url
        }
        resourcePublications(first: 20) {
          nodes {
            publication {
              id
              channels(first: 10) {
                nodes {
                  id
                  name
                }
              }
            }
          }
        }
        sources {
          __typename
          id
          ... on CollectionConditionsSource {
            targetType
            inclusion {
              matchType
              conditions {
                __typename
                id
                ... on CollectionSourceInclusionConditionProductCategory {
                  relation
                  matchType
                  values {
                    category {
                      id
                      name
                      fullName
                    }
                    includeDescendants
                  }
                }
                ... on CollectionSourceInclusionConditionProductStatus {
                  relation
                  matchType
                  values
                }
                ... on CollectionSourceInclusionConditionProductTag {
                  relation
                  matchType
                  values
                }
                ... on CollectionSourceInclusionConditionProductTitle {
                  relation
                  matchType
                  values
                }
                ... on CollectionSourceInclusionConditionProductType {
                  relation
                  matchType
                  values
                }
                ... on CollectionSourceInclusionConditionProductVendor {
                  relation
                  matchType
                  values
                }
                ... on CollectionSourceInclusionConditionVariantTitle {
                  relation
                  matchType
                  values
                }
                ... on CollectionSourceInclusionConditionVariantPrice {
                  relation
                  value {
                    amount
                    currencyCode
                  }
                }
                ... on CollectionSourceInclusionConditionVariantCompareAtPrice {
                  relation
                  value {
                    amount
                    currencyCode
                  }
                }
                ... on CollectionSourceInclusionConditionVariantWeight {
                  relation
                  value {
                    value
                    unit
                  }
                }
                ... on CollectionSourceInclusionConditionVariantInventory {
                  relation
                  value
                }
              }
              selections(first: 250) {
                nodes {
                  ... on CollectionInclusionProductSelection {
                    product {
                      id
                    }
                    variantIds
                  }
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
            exclusion {
              matchType
              conditions {
                __typename
                id
                ... on CollectionSourceExclusionConditionProductCategory {
                  relation
                  matchType
                  values {
                    category {
                      id
                      name
                      fullName
                    }
                    includeDescendants
                  }
                }
                ... on CollectionSourceExclusionConditionProductTag {
                  relation
                  matchType
                  values
                }
                ... on CollectionSourceExclusionConditionProductType {
                  relation
                  matchType
                  values
                }
                ... on CollectionSourceExclusionConditionProductVendor {
                  relation
                  matchType
                  values
                }
                ... on CollectionSourceExclusionConditionCollection {
                  matchType
                  values {
                    id
                    title
                  }
                }
              }
              selections(first: 250) {
                nodes {
                  ... on CollectionExclusionProductSelection {
                    product {
                      id
                    }
                  }
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
          }
          ... on CollectionSubCollectionsSource {
            collections {
              id
              title
            }
          }
        }
        products(first: 250) {
          edges {
            node {
              id
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
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

GET_COLLECTION_WITH_SOURCES = """
query GetCollectionById($id: ID!) {
  collection(id: $id) {
    id
    title
    handle
    updatedAt
    descriptionHtml
    sortOrder
    templateSuffix
    image {
      url
    }
    resourcePublications(first: 20) {
      nodes {
        publication {
          id
          channels(first: 10) {
            nodes {
              id
              name
            }
          }
        }
      }
    }
    sources {
      __typename
      id
      ... on CollectionConditionsSource {
        targetType
        inclusion {
          matchType
          conditions {
            __typename
            id
            ... on CollectionSourceInclusionConditionProductCategory {
              relation
              matchType
              values {
                category {
                  id
                  name
                  fullName
                }
                includeDescendants
              }
            }
            ... on CollectionSourceInclusionConditionProductStatus {
              relation
              matchType
              values
            }
            ... on CollectionSourceInclusionConditionProductTag {
              relation
              matchType
              values
            }
            ... on CollectionSourceInclusionConditionProductTitle {
              relation
              matchType
              values
            }
            ... on CollectionSourceInclusionConditionProductType {
              relation
              matchType
              values
            }
            ... on CollectionSourceInclusionConditionProductVendor {
              relation
              matchType
              values
            }
            ... on CollectionSourceInclusionConditionVariantTitle {
              relation
              matchType
              values
            }
            ... on CollectionSourceInclusionConditionVariantPrice {
              relation
              value {
                amount
                currencyCode
              }
            }
            ... on CollectionSourceInclusionConditionVariantCompareAtPrice {
              relation
              value {
                amount
                currencyCode
              }
            }
            ... on CollectionSourceInclusionConditionVariantWeight {
              relation
              value {
                value
                unit
              }
            }
            ... on CollectionSourceInclusionConditionVariantInventory {
              relation
              value
            }
          }
          selections(first: 250) {
            nodes {
              ... on CollectionInclusionProductSelection {
                product {
                  id
                }
                variantIds
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        exclusion {
          matchType
          conditions {
            __typename
            id
            ... on CollectionSourceExclusionConditionProductCategory {
              relation
              matchType
              values {
                category {
                  id
                  name
                  fullName
                }
                includeDescendants
              }
            }
            ... on CollectionSourceExclusionConditionProductTag {
              relation
              matchType
              values
            }
            ... on CollectionSourceExclusionConditionProductType {
              relation
              matchType
              values
            }
            ... on CollectionSourceExclusionConditionProductVendor {
              relation
              matchType
              values
            }
            ... on CollectionSourceExclusionConditionCollection {
              matchType
              values {
                id
                title
              }
            }
          }
          selections(first: 250) {
            nodes {
              ... on CollectionExclusionProductSelection {
                product {
                  id
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
      }
      ... on CollectionSubCollectionsSource {
        collections {
          id
          title
        }
      }
    }
    products(first: 250) {
      edges {
        node {
          id
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

EXPORT_COLLECTION_WITH_SOURCES = """
mutation ExportCollection($collection: CollectionCreateInput!) {
  collectionCreate(collection: $collection) {
    collection {
      id
      handle
      updatedAt
      image {
        url
      }
      resourcePublications(first: 20) {
        nodes {
          publication {
            id
            channels(first: 10) {
              nodes {
                id
                name
              }
            }
          }
        }
      }
      sources {
        __typename
        id
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

UPDATE_COLLECTION_WITH_SOURCES = """
mutation UpdateCollection($collection: CollectionUpdateInput!) {
  collectionUpdate(collection: $collection) {
    job {
      id
      done
    }
    collection {
      id
      handle
      updatedAt
      image {
        url
      }
      resourcePublications(first: 20) {
        nodes {
          publication {
            id
            channels(first: 10) {
              nodes {
                id
                name
              }
            }
          }
        }
      }
      sources {
        __typename
        id
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

CHECK_RECORDS_EXIST = """
query CheckRecordsExist($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on Product {
      id
    }
    ... on ProductVariant {
      id
    }
  }
}
"""

GET_COLLECTION_SOURCE_STATE = """
query GetCollectionSourceState($id: ID!) {
  collection(id: $id) {
    id
    sources {
      __typename
      id
      ... on CollectionConditionsSource {
        targetType
        inclusion {
          conditions {
            __typename
            id
          }
          selections(first: 250) {
            nodes {
              ... on CollectionInclusionProductSelection {
                product {
                  id
                }
                variantIds
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        exclusion {
          conditions {
            __typename
            id
          }
          selections(first: 250) {
            nodes {
              ... on CollectionExclusionProductSelection {
                product {
                  id
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
      }
      ... on CollectionSubCollectionsSource {
        collections {
          id
        }
      }
    }
  }
}
"""

GET_SOURCE_INCLUSION_SELECTIONS_AFTER_CURSOR = """
query GetSourceInclusionSelections($id: ID!, $cursor: String) {
  node(id: $id) {
    ... on CollectionConditionsSource {
      inclusion {
        selections(first: 250, after: $cursor) {
          nodes {
            ... on CollectionInclusionProductSelection {
              product {
                id
              }
              variantIds
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
  }
}
"""

GET_SOURCE_EXCLUSION_SELECTIONS_AFTER_CURSOR = """
query GetSourceExclusionSelections($id: ID!, $cursor: String) {
  node(id: $id) {
    ... on CollectionConditionsSource {
      exclusion {
        selections(first: 250, after: $cursor) {
          nodes {
            ... on CollectionExclusionProductSelection {
              product {
                id
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
  }
}
"""

GET_COLLECTION_PUBLICATION_STATE = """
query GetCollectionPublicationState($id: ID!) {
  collection(id: $id) {
    id
    updatedAt
    resourcePublications(first: 250) {
      nodes {
        publication {
          id
          channels(first: 10) {
            nodes {
              id
              name
            }
          }
        }
      }
    }
  }
}
"""

# ---------------------------------------------------------------------------
# METAOBJECTS
# ---------------------------------------------------------------------------

FETCH_METAOBJECT_DEFINITIONS = """
query MetaobjectDefinitions($first: Int, $metaobjectDefinitionCursor: String) {
  metaobjectDefinitions(first: $first, after: $metaobjectDefinitionCursor) {
    nodes {
      id
      type
      name
      displayNameKey
      access {
        admin
      }
      fieldDefinitions {
        key
        name
        required
        type {
          name
        }
        validations {
          name
          value
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

FETCH_METAOBJECT_ENTRIES = """
query Metaobjects($type: String!, $first: Int, $metaobjectCursor: String) {
  metaobjects(type: $type, first: $first, after: $metaobjectCursor) {
    nodes {
      id
      type
      handle
      displayName
      fields {
        key
        value
        type
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

GET_METAOBJECTS_BY_IDS = """
query MetaobjectsByIds($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on Metaobject {
      id
      type
      handle
      displayName
      fields {
        key
        value
        type
      }
    }
  }
}
"""

CREATE_METAOBJECT = """
mutation MetaobjectCreate($metaobject: MetaobjectCreateInput!) {
  metaobjectCreate(metaobject: $metaobject) {
    metaobject {
      id
      type
      handle
      displayName
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

UPDATE_METAOBJECT = """
mutation MetaobjectUpdate($id: ID!, $metaobject: MetaobjectUpdateInput!) {
  metaobjectUpdate(id: $id, metaobject: $metaobject) {
    metaobject {
      id
      type
      handle
      displayName
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

DELETE_METAOBJECT = """
mutation MetaobjectDelete($id: ID!) {
  metaobjectDelete(id: $id) {
    deletedId
    userErrors {
      field
      message
      code
    }
  }
}
"""

METAOBJECTS_BATCH_QUERY = """
query MetaobjectsBatch(%(var_decls)s) {
%(aliases)s
}
"""

METAOBJECT_BATCH_ALIAS = """
d%(index)s: metaobjects(type: $type%(index)s, first: %(first)s) {
  nodes {
    id
    type
    handle
    displayName
    fields {
      key
      value
      type
    }
  }
  pageInfo {
    hasNextPage
    endCursor
  }
}
"""

DELETE_DEF_MUTATION = """
mutation MetaobjectDefinitionDelete($id: ID!) {
  metaobjectDefinitionDelete(id: $id) {
    deletedId
    userErrors {
      field
      message
    }
  }
}
"""