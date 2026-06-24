from dataclasses import dataclass, field


@dataclass
class SiteConfig:
    id: str
    start_url: str
    orientation: str
    workflows: list[str] = field(default_factory=list)
    policies: list[str] = field(default_factory=list)


_REGISTRY: dict[str, SiteConfig] = {
    "shopadmin": SiteConfig(
        id="shopadmin",
        start_url="http://localhost:5173/admin",
        orientation=(
            "This is an internal customer support portal for NorthShop. "
            "The order list page has a search input (filter by customer name or email) "
            "and a Status dropdown to filter by order status (All, pending, processing, "
            "shipped, delivered, refunded, cancelled). "
            "Clicking an order row opens its detail page, which shows the customer's "
            "name, email, order status, line items, and total. "
            "Order actions are accessed through an 'Actions' dropdown button on the detail page — "
            "click it to reveal the available options, which depend on the order's current status: "
            "  • 'Issue Refund' appears when the order is delivered and has no existing refund. "
            "    The refund form has three fields: a Category dropdown (Product defect, Changed mind, "
            "    Wrong item received, Damaged in transit, Other), a Details textarea for the reason, "
            "    and an optional Partial amount field (leave blank to refund the full order total). "
            "  • 'Cancel Order' appears when the order is pending or processing. "
            "    The cancel form has a Reason dropdown (Customer request, Out of stock, Payment issue, Other) "
            "    and a Notes textarea. "
            "There are no login screens or top-level navigation menus to deal with."
        ),
        workflows=[
            "Look up the status and details of a customer's order",
            "Search for orders by customer name, email, or filter the list by order status",
            "Issue a refund on an eligible order (delivered, within 30 days, not already refunded): "
            "open Actions → Issue Refund → select category → fill details → optionally enter partial amount → Confirm",
            "Cancel a pending or processing order: open Actions → Cancel Order → select reason → add notes → Confirm",
            "Escalate to a human agent when a request is outside the above workflows or the customer asks to speak with a person",
        ],
        policies=[
            "Always confirm the customer's order number before taking any action on an order.",
            "Only one refund may be issued per order, and the order must have status 'delivered'.",
            "Refund amounts follow a tiered policy based on reason category and order age (days since delivery):"
            " (1) FULL REFUND — reason is Product defect, Wrong item received, or Damaged in transit,"
            " AND order is 30 days old or less."
            " (2) 75% PARTIAL — same product-issue categories, AND order is 31–60 days old."
            " Enter 75% of the order total in the Partial amount field."
            " (3) 50% PARTIAL — reason is Changed mind or Other, AND order is 30 days old or less."
            " Enter 50% of the order total in the Partial amount field."
            " (4) NO REFUND — Changed mind / Other AND order is more than 30 days old. Explain the policy."
            " (5) ESCALATE — any product-issue claim on an order older than 60 days,"
            " or any refund request on an order over $500.",
            "When issuing a partial refund, always calculate and enter the exact dollar amount"
            " (do not leave the amount field blank — that issues a full refund).",
            "If an order is not eligible, explain clearly why (wrong status, outside window, already refunded)"
            " rather than attempting the action.",
            "Never promise an outcome you cannot execute through the portal.",
            "Do not disclose competitor pricing or internal business metrics.",
            "Escalate if the customer explicitly asks for a human, if suspected fraud is involved,"
            " or if you cannot resolve the issue after attempting the relevant workflow.",
        ],
    ),
}


def active_site(site_id: str | None = None) -> SiteConfig:
    """Return the SiteConfig for the given id (falls back to settings.active_site, then shopadmin)."""
    if site_id is None:
        from app.config import settings
        site_id = settings.active_site
    return _REGISTRY.get(site_id, _REGISTRY["shopadmin"])