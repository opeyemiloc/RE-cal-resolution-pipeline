import pandas as pd
from typing import List
from src.core.models import LLMMatchDecision, ShippingRecord


# ==========================================
# COLUMN DEFINITIONS
# ==========================================
REPORT_COLUMNS = [
    "Bill of Lading",
    "Container Number",
    "Vessel",
    "Port of Discharge",
    "ETA",
    "Matched Account",
    "Confidence",
    "Status",
]


def build_report_dataframe(
    decisions: List[LLMMatchDecision],
    raw_records: List[ShippingRecord],
) -> pd.DataFrame:
    """
    Joins pipeline decisions back to the original shipping records
    and returns a clean DataFrame ready for email / export.

    Parameters
    ----------
    decisions : List[LLMMatchDecision]
        The final match decisions produced by the pipeline
        (exact matches + rejections + LLM results).
    raw_records : List[ShippingRecord]
        The original container-level records parsed from the manifest.
        Used to pull BL, container, vessel, port, and ETA info.

    Returns
    -------
    pd.DataFrame
        One row per decision with the REPORT_COLUMNS.
    """
    # --- Build a lookup from messy name → shipping details ---
    # Multiple containers can share one BL so we keep all records.
    record_lookup = {}
    for rec in raw_records:
        record_lookup.setdefault(rec.messy_party_name, rec)

    rows = []
    for decision in decisions:
        source_record = record_lookup.get(decision.original_messy_name)

        rows.append({
            "Bill of Lading":   source_record.bill_of_lading if source_record else None,
            "Container Number": source_record.container_number if source_record else None,
            "Vessel":           source_record.vessel_name if source_record else None,
            "Port of Discharge": source_record.port_of_discharge if source_record else None,
            "ETA":              source_record.eta if source_record else None,
            "Matched Account":  decision.resolved_master_name or "—",
            "Confidence":       decision.confidence_score,
            "Status":           _derive_status(decision),
        })

    df = pd.DataFrame(rows, columns=REPORT_COLUMNS)
    return df


# ==========================================
# HTML EMAIL GENERATION
# ==========================================
def generate_email_html(df: pd.DataFrame, vessel_name: str = "") -> str:
    """
    Converts the report DataFrame into a styled HTML email body.

    Parameters
    ----------
    df : pd.DataFrame
        The report DataFrame produced by `build_report_dataframe`.
    vessel_name : str
        Optional vessel identifier shown in the email subject/header.

    Returns
    -------
    str
        A complete HTML string ready to be sent or saved.
    """
    # TODO: Load an HTML/Jinja template from templates/ and render with df
    # Placeholder — returns a bare-bones HTML table for now
    table_html = df.to_html(index=False, border=1, na_rep="—")

    html = f"""\
    <html>
    <head><meta charset="utf-8"></head>
    <body>
        <h2>📦 Container Arrival Report — {vessel_name}</h2>
        {table_html}
    </body>
    </html>
    """
    return html


# ==========================================
# EMAIL DISPATCH (PLACEHOLDER)
# ==========================================
def send_email(html_body: str, recipients: List[str], subject: str) -> None:
    """
    Sends the generated HTML report via email.

    Parameters
    ----------
    html_body : str
        The rendered HTML string.
    recipients : List[str]
        Email addresses to send the report to.
    subject : str
        Email subject line.
    """
    # TODO: Implement SMTP / SendGrid / API email dispatch
    raise NotImplementedError("Email dispatch is not configured yet.")


# ==========================================
# INTERNAL HELPERS
# ==========================================
def _derive_status(decision: LLMMatchDecision) -> str:
    """Maps a decision to a human-readable status label."""
    if not decision.matched:
        return "❌ Unmatched"
    if decision.confidence_score == 100:
        return "✅ Exact Match"
    if decision.confidence_score >= 80:
        return "🟢 High Confidence"
    if decision.confidence_score >= 50:
        return "🟡 Review"
    return "🔴 Low Confidence"
