"""Report generation modules for AEGIS."""

from aegis.reports.diff_html import render_html_diff_report
from aegis.reports.firmware_html import render_html_firmware_report
from aegis.reports.html import render_html_report
from aegis.reports.research_html import render_html_research_report

__all__ = [
    "render_html_diff_report",
    "render_html_firmware_report",
    "render_html_report",
    "render_html_research_report",
]
