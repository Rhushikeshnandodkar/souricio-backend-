"""
GST (Goods and Services Tax) constants and validation utilities
"""

# Valid GST rates in India (as percentages)
GST_RATES = [5.00, 12.00, 18.00, 28.00]


def is_valid_gst_rate(rate: float) -> bool:
    """
    Check if a GST rate is valid.

    Args:
        rate: GST rate percentage to validate

    Returns:
        True if the rate is valid (5.00, 12.00, 18.00, or 28.00), False otherwise
    """
    return rate in GST_RATES
