"""
Tax calculation service for GST
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from collections import defaultdict

from app.db.models.quote import QuoteItem
from app.lib.gst_constants import GST_RATES


def calculate_item_tax(
    price: Decimal,
    quantity: int,
    gst_rate: Optional[Decimal]
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calculate tax for a single quote item.

    Args:
        price: Item price
        quantity: Item quantity
        gst_rate: GST rate percentage (5.00, 12.00, 18.00, 28.00) or None

    Returns:
        Tuple of (item_total, tax_amount, item_total_with_tax)
        If gst_rate is None, tax_amount will be 0
    """
    item_total = price * Decimal(quantity)

    if gst_rate is None or gst_rate == 0:
        tax_amount = Decimal("0.00")
    else:
        tax_amount = item_total * (gst_rate / Decimal("100.00"))

    item_total_with_tax = item_total + tax_amount

    return item_total, tax_amount, item_total_with_tax


def calculate_quote_totals(
    items: List[QuoteItem]
) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal], Optional[Dict[str, Decimal]]]:
    """
    Calculate totals for a quote including tax.

    Args:
        items: List of quote items

    Returns:
        Tuple of (subtotal, total_tax, total, tax_breakdown)
        Returns None values if any item requires custom pricing
    """
    # Check if any item requires custom pricing
    has_custom_pricing = any(
        item.requires_custom_price or
        item.price is None or
        item.price == 0 or
        item.price == Decimal("0.00")
        for item in items
    )

    if has_custom_pricing:
        return None, None, None, None

    subtotal = Decimal("0.00")
    total_tax = Decimal("0.00")
    tax_breakdown = defaultdict(Decimal)

    for item in items:
        if item.item_total is not None:
            subtotal += item.item_total
        else:
            # Calculate if not already calculated
            item_total = item.price * Decimal(item.quantity)
            subtotal += item_total

        if item.tax_amount is not None:
            total_tax += item.tax_amount
            if item.gst_rate is not None:
                rate_key = str(int(item.gst_rate))
                tax_breakdown[rate_key] += item.tax_amount
        elif item.gst_rate is not None and item.gst_rate > 0:
            # Calculate tax if not already calculated
            item_total = item.item_total or (
                item.price * Decimal(item.quantity))
            tax_amount = item_total * (item.gst_rate / Decimal("100.00"))
            total_tax += tax_amount
            rate_key = str(int(item.gst_rate))
            tax_breakdown[rate_key] += tax_amount

    total = subtotal + total_tax

    # Convert defaultdict to regular dict, convert Decimal values to strings for JSON serialization
    tax_breakdown_dict = {
        k: float(v) for k, v in tax_breakdown.items()
    } if tax_breakdown else None

    return subtotal, total_tax, total, tax_breakdown_dict


def get_tax_breakdown(items: List[QuoteItem]) -> Dict[str, Decimal]:
    """
    Group tax amounts by GST rate.

    Args:
        items: List of quote items

    Returns:
        Dictionary mapping GST rate (as string) to total tax amount
        Example: {"5": 100.00, "18": 250.00}
    """
    tax_breakdown = defaultdict(Decimal)

    for item in items:
        if item.tax_amount is not None and item.tax_amount > 0:
            if item.gst_rate is not None:
                rate_key = str(int(item.gst_rate))
                tax_breakdown[rate_key] += item.tax_amount

    return dict(tax_breakdown)
