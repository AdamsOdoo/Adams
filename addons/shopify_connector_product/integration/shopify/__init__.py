"""Read-only product gateway contracts for the P06 migration."""

from .read_gateway import (
    PRODUCT_READ_OPERATION,
    PRODUCT_SCAN_OPERATION,
    ProductDTO,
    ProductOptionDTO,
    ProductOptionValueDTO,
    ProductReadGateway,
    ProductSummaryDTO,
    SelectedOptionDTO,
    VariantDTO,
)

__all__ = [
    "PRODUCT_READ_OPERATION",
    "PRODUCT_SCAN_OPERATION",
    "ProductDTO",
    "ProductOptionDTO",
    "ProductOptionValueDTO",
    "ProductReadGateway",
    "ProductSummaryDTO",
    "SelectedOptionDTO",
    "VariantDTO",
]
