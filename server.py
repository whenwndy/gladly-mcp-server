import json
import os
from pathlib import Path
from typing import Optional
from fastmcp import FastMCP
from pydantic import Field

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

_DATA_PATH = Path(__file__).parent / "data" / "gladly.json"
_db: dict = json.loads(_DATA_PATH.read_text())


def _match(record: dict, field: str, value: str) -> bool:
    """Case-insensitive substring match on a field."""
    return value.lower() in str(record.get(field, "")).lower()


def _match_any(record: dict, fields: list, value: str) -> bool:
    """Case-insensitive substring match across multiple fields."""
    return any(value.lower() in str(record.get(f, "")).lower() for f in fields)


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="gladly-kitsch",
    version="1.0.0",
    instructions=(
        "Mock Gladly CX platform for Kitsch beauty brand. "
        "Supports CX dashboard metrics, agent performance, backlog analysis, "
        "ticket lookup, CSAT reporting, issue trend analysis, and similar-case search "
        "to help support agents resolve issues faster. "
        "Key use cases: (1) CX Dashboard — backlog, agent stats, CSAT, trends. "
        "(2) Similar case lookup — find past tickets matching a described issue and return resolutions. "
        "(3) Resolution playbooks — step-by-step guidance for common issue types."
    ),
)


# ---------------------------------------------------------------------------
# Dashboard & Backlog
# ---------------------------------------------------------------------------

@mcp.tool()
def get_backlog_summary() -> dict:
    """Return the current CX backlog summary including total open tickets,
    unassigned count, age distribution, and breakdown by inbox.
    Use this as the top-level metric for the CX dashboard."""
    return _db["backlog_summary"]


@mcp.tool()
def get_backlog_by_inbox(
    inbox: Optional[str] = Field(default=None, description="Filter by inbox name (partial match), e.g. 'X Marketing', 'Escalations', 'Customer Service Main'"),
    aged_only: Optional[bool] = Field(default=None, description="If true, return only inboxes with tickets older than 14 days"),
) -> list[dict]:
    """Return backlog breakdown by inbox with age buckets (under 3d, 3-14d, 14-90d, 90d+).
    Use to identify which inboxes have aging or at-risk ticket volumes."""
    results = _db["backlog_summary"]["backlog_by_inbox"]
    if inbox:
        results = [r for r in results if _match(r, "inbox", inbox)]
    if aged_only:
        results = [r for r in results if (r.get("days_14_90") or 0) + (r.get("days_90_plus") or 0) > 0]
    return results


# ---------------------------------------------------------------------------
# Agent Performance
# ---------------------------------------------------------------------------

@mcp.tool()
def get_agent_performance(
    agent_name: Optional[str] = Field(default=None, description="Filter by agent name (partial match), e.g. 'Jessica', 'Shirley Chan'"),
    title: Optional[str] = Field(default=None, description="Filter by title (partial match), e.g. 'Tier 1 CSR', 'Marketing VA'"),
    low_fcr: Optional[bool] = Field(default=None, description="If true, return only agents with FCR below 60% (underperforming)"),
    high_occupancy: Optional[bool] = Field(default=None, description="If true, return agents with occupancy above 80% (capacity risk)"),
) -> list[dict]:
    """Return agent performance metrics including replies/hr, hours/day, occupancy,
    reopen rate, and FCR vs queue benchmark.
    Metrics definition: replies/hr = replies sent per active hour. Occup = handle time / active time.
    Reopen% = share of closes that came back. FCR = first contact resolution vs their queue mix."""
    results = _db["agent_performance"]
    if agent_name:
        results = [r for r in results if _match(r, "agent_name", agent_name)]
    if title:
        results = [r for r in results if _match(r, "title", title)]
    if low_fcr:
        results = [r for r in results if isinstance(r.get("fcr_pct"), (int, float)) and r["fcr_pct"] < 60]
    if high_occupancy:
        results = [r for r in results if isinstance(r.get("occupancy_pct"), (int, float)) and r["occupancy_pct"] > 80]
    return results


# ---------------------------------------------------------------------------
# CSAT
# ---------------------------------------------------------------------------

@mcp.tool()
def get_csat_summary() -> dict:
    """Return overall CSAT score, score distribution, CSAT by channel,
    and CSAT by issue category for the current period.
    Use for the CSAT section of the CX dashboard."""
    return _db["csat_summary"]


# ---------------------------------------------------------------------------
# Trend Report
# ---------------------------------------------------------------------------

@mcp.tool()
def get_trend_report() -> dict:
    """Return the CX trend report including rising issues, declining issues,
    volume vs prior month, and emerging signals.
    Use to surface what's changing in CX volume and identify proactive actions."""
    return _db["trend_report"]


# ---------------------------------------------------------------------------
# Issue Category Analysis
# ---------------------------------------------------------------------------

@mcp.tool()
def get_issue_categories(
    category: Optional[str] = Field(default=None, description="Filter by category key (partial match), e.g. 'defective_product', 'lost_package', 'usage_guidance', 'health_safety'"),
) -> list[dict]:
    """Return issue category breakdown with ticket counts, avg resolution time,
    top affected products, and standard resolution approach.
    Categories: defective_product, lost_package, usage_guidance, wrong_item,
    promo_code, expectation_mismatch, billing, product_feedback, health_safety."""
    results = _db["issue_categories"]
    if category:
        results = [r for r in results if _match(r, "category", category)]
    return results


# ---------------------------------------------------------------------------
# Ticket Lookup
# ---------------------------------------------------------------------------

@mcp.tool()
def get_tickets(
    ticket_id: Optional[str] = Field(default=None, description="Look up a specific ticket by ID, e.g. 'TKT-10042'"),
    status: Optional[str] = Field(default=None, description="Filter by status: 'open' | 'resolved' | 'escalated'"),
    priority: Optional[str] = Field(default=None, description="Filter by priority: 'urgent' | 'high' | 'medium' | 'low'"),
    inbox: Optional[str] = Field(default=None, description="Filter by inbox name (partial match), e.g. 'Escalations', 'X TikTok'"),
    issue_category: Optional[str] = Field(default=None, description="Filter by issue category, e.g. 'defective_product', 'lost_package'"),
    product_sku: Optional[str] = Field(default=None, description="Filter by product SKU (partial match), e.g. 'KT-CURL-HEATLESS'"),
    unassigned_only: Optional[bool] = Field(default=None, description="If true, return only unassigned tickets"),
) -> list[dict]:
    """Return tickets with full details including summary, resolution, tags, and CSAT.
    Use for ticket lookup, case review, and queue management."""
    results = _db["tickets"]
    if ticket_id:
        results = [r for r in results if r["ticket_id"].lower() == ticket_id.lower()]
    if status:
        results = [r for r in results if _match(r, "status", status)]
    if priority:
        results = [r for r in results if _match(r, "priority", priority)]
    if inbox:
        results = [r for r in results if _match(r, "inbox", inbox)]
    if issue_category:
        results = [r for r in results if _match(r, "issue_category", issue_category)]
    if product_sku:
        results = [r for r in results if product_sku.lower() in str(r.get("product_sku", "")).lower()]
    if unassigned_only:
        results = [r for r in results if not r.get("assigned_agent_id")]
    return results


# ---------------------------------------------------------------------------
# Similar Case Search  (core agent-assist feature)
# ---------------------------------------------------------------------------

@mcp.tool()
def find_similar_cases(
    description: str = Field(description="Free-text description of the current issue, e.g. 'customer says heatless curling set broke after one use' or 'shampoo bar leaving waxy residue'"),
    product_sku: Optional[str] = Field(default=None, description="Optional: narrow results to a specific product SKU"),
    limit: int = Field(default=5, description="Maximum number of similar cases to return (default 5)"),
) -> dict:
    """Search past resolved tickets for cases similar to the current issue.
    Returns matching tickets with their summaries and resolutions, plus the
    recommended resolution playbook for the matched issue category.
    Use when an agent asks: 'have we seen a case like this before?' or 'how was this resolved?'"""

    desc_lower = description.lower()
    keywords = [w for w in desc_lower.split() if len(w) > 3]

    # Score each resolved ticket by keyword overlap across searchable fields
    scored = []
    for ticket in _db["tickets"]:
        if ticket.get("status") not in ("resolved", "escalated"):
            continue
        if product_sku and product_sku.lower() not in str(ticket.get("product_sku", "")).lower():
            continue

        search_blob = " ".join([
            str(ticket.get("subject", "")),
            str(ticket.get("summary", "")),
            str(ticket.get("resolution", "")),
            str(ticket.get("issue_category", "")),
            " ".join(ticket.get("tags", []))
        ]).lower()

        score = sum(1 for kw in keywords if kw in search_blob)
        if score > 0:
            scored.append((score, ticket))

    scored.sort(key=lambda x: x[0], reverse=True)
    matched_tickets = [t for _, t in scored[:limit]]

    # Identify the dominant issue category from matches
    if matched_tickets:
        categories = [t.get("issue_category") for t in matched_tickets if t.get("issue_category")]
        dominant_category = max(set(categories), key=categories.count) if categories else None
    else:
        dominant_category = None

    # Look up the playbook for that category
    playbook = None
    if dominant_category:
        playbooks = [p for p in _db["resolution_playbooks"] if p["issue_category"] == dominant_category]
        if playbooks:
            playbook = playbooks[0]

    return {
        "query": description,
        "matches_found": len(matched_tickets),
        "similar_cases": [
            {
                "ticket_id": t["ticket_id"],
                "subject": t["subject"],
                "product_sku": t.get("product_sku"),
                "issue_category": t.get("issue_category"),
                "summary": t.get("summary"),
                "resolution": t.get("resolution"),
                "csat_score": t.get("csat_score"),
                "tags": t.get("tags", [])
            }
            for t in matched_tickets
        ],
        "recommended_playbook": playbook
    }


# ---------------------------------------------------------------------------
# Resolution Playbooks
# ---------------------------------------------------------------------------

@mcp.tool()
def get_resolution_playbook(
    issue_category: Optional[str] = Field(default=None, description="Issue category key, e.g. 'defective_product', 'lost_package', 'usage_guidance', 'health_safety'"),
    playbook_id: Optional[str] = Field(default=None, description="Specific playbook ID, e.g. 'pb03'"),
) -> list[dict]:
    """Return step-by-step resolution playbooks for common issue types.
    Each playbook includes resolution steps, what NOT to do, and a template response.
    Available: defective_product, lost_package, usage_guidance (heatless curler + shampoo bar),
    health_safety (allergic reaction — escalate immediately)."""
    results = _db["resolution_playbooks"]
    if issue_category:
        results = [r for r in results if _match(r, "issue_category", issue_category)]
    if playbook_id:
        results = [r for r in results if r["playbook_id"].lower() == playbook_id.lower()]
    return results


# ---------------------------------------------------------------------------
# Contact Lookup
# ---------------------------------------------------------------------------

@mcp.tool()
def get_contact(
    email: Optional[str] = Field(default=None, description="Customer email address (exact or partial match)"),
    name: Optional[str] = Field(default=None, description="Customer name (partial match)"),
) -> list[dict]:
    """Look up a customer contact profile including lifetime orders, spend,
    segment, ticket history count, and any agent notes.
    Use before responding to a ticket to understand the customer's history."""
    results = _db["contacts"]
    if email:
        results = [r for r in results if _match(r, "email", email)]
    if name:
        results = [r for r in results if _match(r, "name", name)]
    return results


# ---------------------------------------------------------------------------
# Full CX Dashboard
# ---------------------------------------------------------------------------

@mcp.tool()
def get_cx_dashboard() -> dict:
    """Return a complete CX dashboard snapshot combining backlog summary,
    agent performance, CSAT summary, issue category breakdown, and trend report.
    Use when asked for a full overview or weekly CX report."""
    return {
        "snapshot_date": _db["company"]["snapshot_date"],
        "snapshot_period": _db["company"]["snapshot_period"],
        "backlog": _db["backlog_summary"],
        "agent_performance": _db["agent_performance"],
        "csat": _db["csat_summary"],
        "issue_categories": _db["issue_categories"],
        "trends": _db["trend_report"]
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
