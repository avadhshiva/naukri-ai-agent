from __future__ import annotations

import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from typing import Iterable


@dataclass
class EmailConfig:
    enabled: bool
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    mail_from: str
    mail_to: str


def _build_company_site_html(jobs: Iterable[dict], site_name: str) -> str:
    rows = []
    for job in jobs:
        rows.append(
            "<tr>"
            f"<td>{escape(job.get('searchTitle', ''))}</td>"
            f"<td>{escape(job.get('company', ''))}</td>"
            f"<td>{escape(job.get('location', ''))}</td>"
            f"<td>{escape(job.get('jobExperienceReq', 'Not specified'))}</td>"
            f"<td>{escape(job.get('salary', ''))}</td>"
            f"<td><a href=\"{escape(job.get('jobUrl', ''))}\">Open</a></td>"
            f"<td>{escape(job.get('notes', ''))}</td>"
            "</tr>"
        )

    site_display = site_name.capitalize()
    table = (
        "<table style=\"width:100%;border-collapse:collapse;\">"
        "<thead>"
        "<tr>"
        "<th style=\"text-align:left;border-bottom:1px solid #ddd;padding:8px;\">Role</th>"
        "<th style=\"text-align:left;border-bottom:1px solid #ddd;padding:8px;\">Company</th>"
        "<th style=\"text-align:left;border-bottom:1px solid #ddd;padding:8px;\">Location</th>"
        "<th style=\"text-align:left;border-bottom:1px solid #ddd;padding:8px;\">Experience</th>"
        "<th style=\"text-align:left;border-bottom:1px solid #ddd;padding:8px;\">Salary</th>"
        "<th style=\"text-align:left;border-bottom:1px solid #ddd;padding:8px;\">Link</th>"
        "<th style=\"text-align:left;border-bottom:1px solid #ddd;padding:8px;\">Notes</th>"
        "</tr>"
        "</thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        if rows
        else f"<p>No {site_display}-site jobs captured in this run.</p>"
    )

    generated_at = escape(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return (
        "<div style=\"font-family:Segoe UI,Arial,sans-serif;\">"
        f"<h2>{site_display}: Jobs Found</h2>"
        f"<p>Generated at {generated_at}</p>"
        f"{table}"
        "</div>"
    )


def send_company_site_digest(email_cfg: EmailConfig, jobs: list[dict], site_name: str = "Naukri") -> bool:
    if not email_cfg.enabled:
        return False
    if not (email_cfg.smtp_host and email_cfg.smtp_user and email_cfg.smtp_password and email_cfg.mail_to):
        return False

    # Include all jobs that were captured but not necessarily 'apply_on_company_site'
    # This ensures the user sees all relevant findings.
    html = _build_company_site_html(jobs, site_name)

    site_display = site_name.capitalize()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{site_display} Digest: Jobs Found ({len(jobs)})"
    msg["From"] = email_cfg.mail_from or email_cfg.smtp_user
    msg["To"] = email_cfg.mail_to
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(email_cfg.smtp_host, email_cfg.smtp_port) as server:
        server.starttls()
        server.login(email_cfg.smtp_user, email_cfg.smtp_password)
        server.sendmail(msg["From"], [email_cfg.mail_to], msg.as_string())
    return True

