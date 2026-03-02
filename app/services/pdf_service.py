"""
PDF generation service for quotes and invoices
"""
from typing import Optional, Union
from decimal import Decimal
from datetime import datetime
from io import BytesIO

from app.core.config import settings
from app.schemas.quote import QuoteDetailResponse, QuoteResponse
from app.schemas.order import OrderDetailResponse, OrderResponse

# Lazy import WeasyPrint to avoid blocking server startup if dependencies are missing
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    WEASYPRINT_AVAILABLE = False
    WEASYPRINT_ERROR = str(e)


def format_currency(amount: Optional[Decimal]) -> str:
    """Format decimal amount as currency string."""
    if amount is None:
        return "N/A"
    return f"₹{amount:,.2f}"


def format_date(date: Optional[datetime]) -> str:
    """Format datetime as readable date string."""
    if date is None:
        return "N/A"
    return date.strftime("%B %d, %Y")


def get_company_info() -> dict:
    """Get company information from settings with defaults."""
    return {
        "name": settings.COMPANY_NAME or "Sourcio",
        "address": settings.COMPANY_ADDRESS or "",
        "phone": settings.COMPANY_PHONE or "",
        "email": settings.COMPANY_EMAIL or "",
        "logo_url": settings.COMPANY_LOGO_URL,
        "terms": settings.COMPANY_TERMS_CONDITIONS or "",
    }


def generate_quote_html(quote: Union[QuoteDetailResponse, QuoteResponse]) -> str:
    """Generate HTML template for quote PDF."""
    company = get_company_info()

    # Determine customer email
    if isinstance(quote, QuoteDetailResponse):
        customer_email = quote.user.email
    else:
        customer_email = f"User ID: {quote.user_id}"

    # Build items table rows
    items_html = ""
    for item in quote.items:
        item_price = format_currency(
            item.price) if not item.requires_custom_price else "Custom"

        # Calculate item totals
        if item.requires_custom_price:
            item_subtotal = "Custom"
            item_gst_rate = "-"
            item_tax = "-"
            item_total = "Custom"
        else:
            # Use calculated values if available, otherwise calculate
            if item.item_total is not None:
                item_subtotal = format_currency(item.item_total)
            else:
                item_subtotal = format_currency(
                    item.price * Decimal(item.quantity))

            if item.gst_rate is not None and item.gst_rate > 0:
                item_gst_rate = f"{item.gst_rate}%"
                if item.tax_amount is not None:
                    item_tax = format_currency(item.tax_amount)
                else:
                    # Calculate tax if not available
                    item_total_val = item.item_total or (
                        item.price * Decimal(item.quantity))
                    item_tax = format_currency(
                        item_total_val * (item.gst_rate / Decimal("100.00")))

                if item.item_total_with_tax is not None:
                    item_total = format_currency(item.item_total_with_tax)
                else:
                    # Calculate total with tax if not available
                    item_total_val = item.item_total or (
                        item.price * Decimal(item.quantity))
                    item_tax_val = item_total_val * \
                        (item.gst_rate / Decimal("100.00"))
                    item_total = format_currency(item_total_val + item_tax_val)
            else:
                item_gst_rate = "-"
                item_tax = "-"
                if item.item_total is not None:
                    item_total = format_currency(item.item_total)
                else:
                    item_total = format_currency(
                        item.price * Decimal(item.quantity))

        items_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">
                <div>
                    <div style="font-weight: 600; color: #111827;">{item.product_name}</div>
                    {f'<div style="font-size: 0.875rem; color: #6b7280;">{item.variant_name}</div>' if item.variant_name else ''}
                </div>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: center;">{item.quantity}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right;">{item_price}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right;">{item_subtotal}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: center;">{item_gst_rate}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right;">{item_tax}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right; font-weight: 600;">{item_total}</td>
        </tr>
        """

    # Status badge color
    status_colors = {
        "draft": "#6b7280",
        "pending": "#f59e0b",
        "approved": "#10b981",
        "rejected": "#ef4444",
        "expired": "#9ca3af",
    }
    status_color = status_colors.get(quote.status.lower(), "#6b7280")

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Quote {quote.quote_number}</title>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                font-size: 12px;
                line-height: 1.6;
                color: #111827;
                margin: 0;
                padding: 0;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 2px solid #e5e7eb;
            }}
            .company-info {{
                flex: 1;
            }}
            .company-name {{
                font-size: 24px;
                font-weight: 700;
                color: #111827;
                margin-bottom: 8px;
            }}
            .company-details {{
                font-size: 11px;
                color: #6b7280;
                line-height: 1.8;
            }}
            .quote-info {{
                text-align: right;
            }}
            .quote-title {{
                font-size: 28px;
                font-weight: 700;
                color: #111827;
                margin-bottom: 8px;
            }}
            .quote-number {{
                font-size: 14px;
                color: #6b7280;
                margin-bottom: 4px;
            }}
            .status-badge {{
                display: inline-block;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                color: white;
                background-color: {status_color};
                margin-top: 8px;
            }}
            .customer-section {{
                margin-bottom: 30px;
                padding: 16px;
                background-color: #f9fafb;
                border-radius: 8px;
            }}
            .section-title {{
                font-size: 11px;
                font-weight: 600;
                color: #6b7280;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 8px;
            }}
            .customer-info {{
                font-size: 13px;
                color: #111827;
            }}
            .items-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            .items-table th {{
                background-color: #f9fafb;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: #6b7280;
                border-bottom: 2px solid #e5e7eb;
            }}
            .items-table th:last-child {{
                text-align: right;
            }}
            .totals-section {{
                margin-left: auto;
                width: 300px;
                margin-bottom: 30px;
            }}
            .total-row {{
                display: flex;
                justify-content: space-between;
                padding: 12px 0;
                border-bottom: 1px solid #e5e7eb;
            }}
            .total-row:last-child {{
                border-bottom: 2px solid #111827;
                font-weight: 700;
                font-size: 16px;
            }}
            .total-label {{
                color: #6b7280;
            }}
            .total-value {{
                color: #111827;
            }}
            .notes-section {{
                margin-bottom: 30px;
            }}
            .notes-box {{
                padding: 16px;
                background-color: #f9fafb;
                border-radius: 8px;
                margin-top: 8px;
            }}
            .notes-text {{
                font-size: 12px;
                color: #374151;
                white-space: pre-wrap;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
                font-size: 10px;
                color: #6b7280;
                text-align: center;
            }}
            .custom-pricing-notice {{
                background-color: #fef3c7;
                border: 1px solid #fbbf24;
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 20px;
                font-size: 11px;
                color: #92400e;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="company-info">
                {f'<img src="{company["logo_url"]}" alt="{company["name"]}" style="max-width: 150px; max-height: 60px; margin-bottom: 12px;" />' if company["logo_url"] else ''}
                <div class="company-name">{company["name"]}</div>
                <div class="company-details">
                    {f'<div>{company["address"]}</div>' if company["address"] else ''}
                    {f'<div>Phone: {company["phone"]}</div>' if company["phone"] else ''}
                    {f'<div>Email: {company["email"]}</div>' if company["email"] else ''}
                </div>
            </div>
            <div class="quote-info">
                <div class="quote-title">QUOTE</div>
                <div class="quote-number">{quote.quote_number}</div>
                <div style="font-size: 11px; color: #6b7280; margin-top: 4px;">
                    Date: {format_date(quote.created_at)}
                </div>
                {f'<div style="font-size: 11px; color: #6b7280; margin-top: 4px;">Expires: {format_date(quote.expires_at)}</div>' if quote.expires_at else ''}
                <div class="status-badge">{quote.status.upper()}</div>
            </div>
        </div>
        
        <div class="customer-section">
            <div class="section-title">Customer Information</div>
            <div class="customer-info">
                <div><strong>Email:</strong> {customer_email}</div>
            </div>
        </div>
        
        {f'<div class="custom-pricing-notice"><strong>⚠️ Custom Pricing:</strong> This quote includes items requiring custom pricing. Please contact us for final pricing.</div>' if quote.has_custom_pricing else ''}
        
        <div class="section-title" style="margin-bottom: 12px;">Quote Items</div>
        <table class="items-table">
            <thead>
                <tr>
                    <th>Product</th>
                    <th style="text-align: center;">Quantity</th>
                    <th style="text-align: right;">Unit Price</th>
                    <th style="text-align: right;">Subtotal</th>
                    <th style="text-align: center;">GST Rate</th>
                    <th style="text-align: right;">Tax</th>
                    <th style="text-align: right;">Total</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>
        
        <div style="display: flex; justify-content: flex-end;">
            <div class="totals-section">
                {f'<div class="total-row"><span class="total-label">Subtotal:</span><span class="total-value">{format_currency(quote.subtotal)}</span></div>' if quote.subtotal is not None else ''}
                {f'<div class="total-row"><span class="total-label">Total Tax (GST):</span><span class="total-value">{format_currency(quote.total_tax)}</span></div>' if quote.total_tax is not None and quote.total_tax > 0 else ''}
                <div class="total-row">
                    <span class="total-label">Grand Total:</span>
                    <span class="total-value">{format_currency(quote.total) if quote.total is not None else "Custom Pricing"}</span>
                </div>
            </div>
        </div>
        
        
        {company["terms"] and f'''
        <div class="notes-section">
            <div class="section-title">Terms & Conditions</div>
            <div class="notes-box">
                <div class="notes-text">{company["terms"]}</div>
            </div>
        </div>
        ''' or ''}
        
        <div class="footer">
            <div>This quote is valid until {format_date(quote.expires_at) if quote.expires_at else "further notice"}</div>
            <div style="margin-top: 8px;">Generated on {datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")}</div>
        </div>
    </body>
    </html>
    """

    return html_content


def generate_quote_pdf(quote: Union[QuoteDetailResponse, QuoteResponse]) -> BytesIO:
    """
    Generate PDF from quote data.

    Args:
        quote: Quote detail or response object

    Returns:
        BytesIO object containing PDF bytes

    Raises:
        RuntimeError: If WeasyPrint dependencies are not installed
    """
    if not WEASYPRINT_AVAILABLE:
        error_msg = (
            "WeasyPrint is not available. Please install system dependencies:\n"
            "On macOS: brew install cairo pango gdk-pixbuf libffi\n"
            "On Ubuntu/Debian: sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0\n"
            "On Fedora: sudo dnf install cairo pango gdk-pixbuf2 libffi\n"
            f"Original error: {WEASYPRINT_ERROR}"
        )
        raise RuntimeError(error_msg)

    html_content = generate_quote_html(quote)

    # Generate PDF
    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)

    return pdf_buffer


def generate_invoice_html(order: Union[OrderDetailResponse, OrderResponse]) -> str:
    """Generate HTML template for invoice PDF."""
    company = get_company_info()

    # Determine customer email and shipping address
    if isinstance(order, OrderDetailResponse):
        customer_email = order.user.email
        shipping_address = None
        if order.user.shipping_address1:
            address_parts = [
                order.user.shipping_address1,
                order.user.shipping_address2,
                f"{order.user.shipping_city}, {order.user.shipping_state} {order.user.shipping_pin}" if order.user.shipping_city else None,
                order.user.shipping_country
            ]
            shipping_address = "<br>".join([part for part in address_parts if part])
    else:
        customer_email = f"User ID: {order.user_id}"
        shipping_address = None

    # Build items table rows
    items_html = ""
    for item in order.items:
        item_price = format_currency(item.price)

        # Calculate item totals
        if item.item_total is not None:
            item_subtotal = format_currency(item.item_total)
        else:
            item_subtotal = format_currency(item.price * Decimal(item.quantity))

        if item.gst_rate is not None and item.gst_rate > 0:
            item_gst_rate = f"{item.gst_rate}%"
            if item.tax_amount is not None:
                item_tax = format_currency(item.tax_amount)
            else:
                # Calculate tax if not available
                item_total_val = item.item_total or (item.price * Decimal(item.quantity))
                item_tax = format_currency(item_total_val * (item.gst_rate / Decimal("100.00")))

            if item.item_total_with_tax is not None:
                item_total = format_currency(item.item_total_with_tax)
            else:
                # Calculate total with tax if not available
                item_total_val = item.item_total or (item.price * Decimal(item.quantity))
                item_tax_val = item_total_val * (item.gst_rate / Decimal("100.00"))
                item_total = format_currency(item_total_val + item_tax_val)
        else:
            item_gst_rate = "-"
            item_tax = "-"
            if item.item_total is not None:
                item_total = format_currency(item.item_total)
            else:
                item_total = format_currency(item.price * Decimal(item.quantity))

        items_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">
                <div>
                    <div style="font-weight: 600; color: #111827;">{item.product_name}</div>
                    {f'<div style="font-size: 0.875rem; color: #6b7280;">{item.variant_name}</div>' if item.variant_name else ''}
                </div>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: center;">{item.quantity}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right;">{item_price}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right;">{item_subtotal}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: center;">{item_gst_rate}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right;">{item_tax}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right; font-weight: 600;">{item_total}</td>
        </tr>
        """

    # Status badge color
    status_colors = {
        "pending": "#f59e0b",
        "processing": "#3b82f6",
        "shipped": "#8b5cf6",
        "delivered": "#10b981",
        "cancelled": "#ef4444",
    }
    status_color = status_colors.get(order.status.lower(), "#6b7280")

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Invoice {order.order_number}</title>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                font-size: 12px;
                line-height: 1.6;
                color: #111827;
                margin: 0;
                padding: 0;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 2px solid #e5e7eb;
            }}
            .company-info {{
                flex: 1;
            }}
            .company-name {{
                font-size: 24px;
                font-weight: 700;
                color: #111827;
                margin-bottom: 8px;
            }}
            .company-details {{
                font-size: 11px;
                color: #6b7280;
                line-height: 1.8;
            }}
            .invoice-info {{
                text-align: right;
            }}
            .invoice-title {{
                font-size: 28px;
                font-weight: 700;
                color: #111827;
                margin-bottom: 8px;
            }}
            .invoice-number {{
                font-size: 14px;
                color: #6b7280;
                margin-bottom: 4px;
            }}
            .status-badge {{
                display: inline-block;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                color: white;
                background-color: {status_color};
                margin-top: 8px;
            }}
            .customer-section {{
                margin-bottom: 30px;
                padding: 16px;
                background-color: #f9fafb;
                border-radius: 8px;
            }}
            .section-title {{
                font-size: 11px;
                font-weight: 600;
                color: #6b7280;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 8px;
            }}
            .customer-info {{
                font-size: 13px;
                color: #111827;
            }}
            .items-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            .items-table th {{
                background-color: #f9fafb;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: #6b7280;
                border-bottom: 2px solid #e5e7eb;
            }}
            .items-table th:last-child {{
                text-align: right;
            }}
            .totals-section {{
                margin-left: auto;
                width: 300px;
                margin-bottom: 30px;
            }}
            .total-row {{
                display: flex;
                justify-content: space-between;
                padding: 12px 0;
                border-bottom: 1px solid #e5e7eb;
            }}
            .total-row:last-child {{
                border-bottom: 2px solid #111827;
                font-weight: 700;
                font-size: 16px;
            }}
            .total-label {{
                color: #6b7280;
            }}
            .total-value {{
                color: #111827;
            }}
            .notes-section {{
                margin-bottom: 30px;
            }}
            .notes-box {{
                padding: 16px;
                background-color: #f9fafb;
                border-radius: 8px;
                margin-top: 8px;
            }}
            .notes-text {{
                font-size: 12px;
                color: #374151;
                white-space: pre-wrap;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
                font-size: 10px;
                color: #6b7280;
                text-align: center;
            }}
            .tax-breakdown {{
                margin-top: 8px;
                padding: 12px;
                background-color: #f9fafb;
                border-radius: 6px;
                font-size: 11px;
            }}
            .tax-breakdown-row {{
                display: flex;
                justify-content: space-between;
                padding: 4px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="company-info">
                {f'<img src="{company["logo_url"]}" alt="{company["name"]}" style="max-width: 150px; max-height: 60px; margin-bottom: 12px;" />' if company["logo_url"] else ''}
                <div class="company-name">{company["name"]}</div>
                <div class="company-details">
                    {f'<div>{company["address"]}</div>' if company["address"] else ''}
                    {f'<div>Phone: {company["phone"]}</div>' if company["phone"] else ''}
                    {f'<div>Email: {company["email"]}</div>' if company["email"] else ''}
                </div>
            </div>
            <div class="invoice-info">
                <div class="invoice-title">INVOICE</div>
                <div class="invoice-number">{order.order_number}</div>
                <div style="font-size: 11px; color: #6b7280; margin-top: 4px;">
                    Date: {format_date(order.created_at)}
                </div>
                <div class="status-badge">{order.status.upper()}</div>
            </div>
        </div>
        
        <div class="customer-section">
            <div class="section-title">Bill To</div>
            <div class="customer-info">
                <div><strong>Email:</strong> {customer_email}</div>
                {f'<div style="margin-top: 8px;"><strong>Order Number:</strong> {order.order_number}</div>' if order.order_number else ''}
                {f'<div style="margin-top: 12px;"><strong>Shipping Address:</strong><div style="margin-top: 4px; line-height: 1.6;">{shipping_address}</div></div>' if shipping_address else ''}
            </div>
        </div>
        
        <div class="section-title" style="margin-bottom: 12px;">Order Items</div>
        <table class="items-table">
            <thead>
                <tr>
                    <th>Product</th>
                    <th style="text-align: center;">Quantity</th>
                    <th style="text-align: right;">Unit Price</th>
                    <th style="text-align: right;">Subtotal</th>
                    <th style="text-align: center;">GST Rate</th>
                    <th style="text-align: right;">Tax</th>
                    <th style="text-align: right;">Total</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>
        
        <div style="display: flex; justify-content: flex-end;">
            <div class="totals-section">
                {f'<div class="total-row"><span class="total-label">Subtotal:</span><span class="total-value">{format_currency(order.subtotal)}</span></div>' if order.subtotal is not None else ''}
                {f'<div class="total-row"><span class="total-label">Total Tax (GST):</span><span class="total-value">{format_currency(order.total_tax)}</span></div>' if order.total_tax is not None and order.total_tax > 0 else ''}
                {order.tax_breakdown and len(order.tax_breakdown) > 0 and f'''
                <div class="tax-breakdown">
                    <div style="font-weight: 600; margin-bottom: 8px; color: #6b7280;">Tax Breakdown:</div>
                    {''.join([f'<div class="tax-breakdown-row"><span>GST {rate}%:</span><span>{format_currency(Decimal(str(amount)))}</span></div>' for rate, amount in order.tax_breakdown.items()])}
                </div>
                ''' or ''}
                <div class="total-row">
                    <span class="total-label">Grand Total:</span>
                    <span class="total-value">{format_currency(order.total) if order.total is not None else "N/A"}</span>
                </div>
            </div>
        </div>
        
        {order.notes and f'''
        <div class="notes-section">
            <div class="section-title">Notes</div>
            <div class="notes-box">
                <div class="notes-text">{order.notes}</div>
            </div>
        </div>
        ''' or ''}
        
        {company["terms"] and f'''
        <div class="notes-section">
            <div class="section-title">Terms & Conditions</div>
            <div class="notes-box">
                <div class="notes-text">{company["terms"]}</div>
            </div>
        </div>
        ''' or ''}
        
        <div class="footer">
            <div>Thank you for your business!</div>
            <div style="margin-top: 8px;">Generated on {datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")}</div>
        </div>
    </body>
    </html>
    """

    return html_content


def generate_invoice_pdf(order: Union[OrderDetailResponse, OrderResponse]) -> BytesIO:
    """
    Generate PDF invoice from order data.

    Args:
        order: Order detail or response object

    Returns:
        BytesIO object containing PDF bytes

    Raises:
        RuntimeError: If WeasyPrint dependencies are not installed
    """
    if not WEASYPRINT_AVAILABLE:
        error_msg = (
            "WeasyPrint is not available. Please install system dependencies:\n"
            "On macOS: brew install cairo pango gdk-pixbuf libffi\n"
            "On Ubuntu/Debian: sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0\n"
            "On Fedora: sudo dnf install cairo pango gdk-pixbuf2 libffi\n"
            f"Original error: {WEASYPRINT_ERROR}"
        )
        raise RuntimeError(error_msg)

    html_content = generate_invoice_html(order)

    # Generate PDF
    pdf_buffer = BytesIO()
    HTML(string=html_content).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)

    return pdf_buffer
