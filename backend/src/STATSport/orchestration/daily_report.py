"""Build daily PhysicalData reports from persisted scrape runs."""

from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import bindparam, create_engine, text

from .persist_dataset import physical_database_url


def _local_datetime(value: datetime | None, tz: ZoneInfo) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(tz)


def _duration(started_at: datetime | None, completed_at: datetime | None) -> str:
    if started_at is None or completed_at is None:
        return "En cours"
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)
    seconds = max(0, int((completed_at - started_at).total_seconds()))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def load_daily_report_data(
    database_url: str,
    report_date: date,
    timezone_name: str = "Europe/Paris",
) -> dict:
    tz = ZoneInfo(timezone_name)
    start_at = datetime.combine(report_date, time.min, tzinfo=tz)
    end_at = datetime.combine(report_date + timedelta(days=1), time.min, tzinfo=tz)
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            run_rows = connection.execute(
                text("""
                    SELECT CAST(id AS text) AS id, display_name, scrape_type, status,
                           found, inserted, updated, skipped, failed, error_message,
                           request_payload, started_at, completed_at
                    FROM scrape_runs
                    WHERE started_at >= :start_at AND started_at < :end_at
                    ORDER BY started_at, id
                """),
                {"start_at": start_at, "end_at": end_at},
            ).mappings().all()
            run_ids = [row["id"] for row in run_rows]
            activity_results_by_run = {run_id: [] for run_id in run_ids}
            if run_ids:
                activity_rows = connection.execute(
                    text("""
                        SELECT CAST(run_id AS text) AS run_id,
                               details -> 'activity_results' AS activity_results
                        FROM scrape_logs
                        WHERE step = 'run_finished'
                          AND CAST(run_id AS text) IN :run_ids
                    """).bindparams(bindparam("run_ids", expanding=True)),
                    {"run_ids": run_ids},
                ).mappings().all()
                for row in activity_rows:
                    activity_results_by_run[row["run_id"]] = row["activity_results"] or []
    finally:
        engine.dispose()

    runs = []
    sessions = []
    for row in run_rows:
        run = dict(row)
        run["activity_results"] = activity_results_by_run.get(run["id"], [])
        run["started_local"] = _local_datetime(run["started_at"], tz)
        run["completed_local"] = _local_datetime(run["completed_at"], tz)
        run["duration"] = _duration(run["started_at"], run["completed_at"])
        request_payload = run.get("request_payload") or {}
        run["team_name"] = request_payload.get("teamName") or ""
        for activity in run["activity_results"]:
            sessions.append({**activity, "run_name": run["display_name"]})
        runs.append(run)
    return {"report_date": report_date, "timezone": timezone_name, "runs": runs, "sessions": sessions}


def _paragraph(value, style: ParagraphStyle) -> Paragraph:
    safe_text = escape(str(value if value is not None else "" )).replace("\n", "<br/>")
    return Paragraph(safe_text or " ", style)


def build_daily_report_pdf(report_data: dict) -> bytes:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=18, leading=22, alignment=TA_CENTER, textColor=colors.HexColor("#17324D"),
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=15, textColor=colors.HexColor("#17324D"), spaceBefore=8,
    )
    body_style = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=8, leading=10)
    header_style = ParagraphStyle(
        "TableHeader", parent=body_style, fontName="Helvetica-Bold", textColor=colors.white,
    )
    cell_style = ParagraphStyle("TableCell", parent=body_style, wordWrap="CJK")

    runs = report_data["runs"]
    sessions = report_data["sessions"]
    totals = {
        key: sum(int(run.get(key) or 0) for run in runs)
        for key in ("found", "inserted", "updated", "skipped", "failed")
    }
    status_counts = {status: sum(1 for session in sessions if session.get("status") == status)
                     for status in ("NEW", "UPDATE", "ERROR")}

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), rightMargin=12 * mm, leftMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=14 * mm, title="PhysicalData daily report",
        author="Scomp",
    )
    story = [
        _paragraph(f"Rapport quotidien PhysicalData - {report_data['report_date'].isoformat()}", title_style),
        _paragraph(f"Fuseau horaire : {report_data['timezone']}", body_style),
        Spacer(1, 5 * mm),
        _paragraph("Synthèse", section_style),
    ]
    summary_rows = [
        [_paragraph(label, header_style) for label in ("Runs", "Sessions trouvées", "Nouvelles", "Mises à jour", "Inchangées", "Erreurs")],
        [len(runs), totals["found"], totals["inserted"], totals["updated"], totals["skipped"], totals["failed"]],
    ]
    summary_table = Table(summary_rows, colWidths=[35 * mm, 43 * mm, 35 * mm, 37 * mm, 35 * mm, 28 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#EEF3F7")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5DF")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5DF")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([summary_table, Spacer(1, 3 * mm)])
    story.append(_paragraph(
        f"Sessions importées : {totals['inserted'] + totals['updated']} | "
        f"Nouvelles : {status_counts['NEW']} | Mises à jour : {status_counts['UPDATE']} | "
        f"Erreurs : {status_counts['ERROR']}",
        body_style,
    ))

    story.append(_paragraph("Runs", section_style))
    run_headers = ("Automatisation", "Équipe", "Début", "Fin", "Durée", "Statut", "Trouvées", "Nouvelles", "Mises à jour", "Inchangées", "Erreurs")
    run_rows = [[_paragraph(label, header_style) for label in run_headers]]
    for run in runs:
        started = run["started_local"].strftime("%H:%M:%S") if run["started_local"] else "-"
        completed = run["completed_local"].strftime("%H:%M:%S") if run["completed_local"] else "-"
        run_rows.append([
            _paragraph(run.get("display_name") or run.get("scrape_type") or "Run", cell_style),
            _paragraph(run.get("team_name") or "-", cell_style),
            started,
            completed,
            run["duration"],
            _paragraph(run.get("status") or "unknown", cell_style),
            int(run.get("found") or 0),
            int(run.get("inserted") or 0),
            int(run.get("updated") or 0),
            int(run.get("skipped") or 0),
            int(run.get("failed") or 0),
        ])
    if len(run_rows) == 1:
        run_rows.append([_paragraph("Aucun run PhysicalData enregistré ce jour.", cell_style)] + [""] * (len(run_headers) - 1))
    run_table = Table(
        run_rows,
        colWidths=[42 * mm, 27 * mm, 20 * mm, 20 * mm, 19 * mm, 21 * mm, 18 * mm, 18 * mm, 22 * mm, 20 * mm, 16 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )
    run_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F8")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5DF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([run_table, Spacer(1, 3 * mm), _paragraph("Sessions importées ou en erreur", section_style)])

    session_headers = ("Session", "Date de session", "Statut", "Run")
    session_rows = [[_paragraph(label, header_style) for label in session_headers]]
    for session in sessions:
        session_rows.append([
            _paragraph(session.get("activity_name") or "Activité sans nom", cell_style),
            _paragraph(session.get("session_date") or "Date inconnue", cell_style),
            _paragraph(session.get("status") or "ERROR", cell_style),
            _paragraph(session.get("run_name") or "-", cell_style),
        ])
    if len(session_rows) == 1:
        session_rows.append([_paragraph("Aucune session nouvelle, mise à jour ou en erreur.", cell_style), "", "", ""])
    session_table = Table(session_rows, colWidths=[88 * mm, 35 * mm, 30 * mm, 90 * mm], repeatRows=1, hAlign="LEFT")
    session_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F8")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5DF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(session_table)

    for run in runs:
        if run.get("error_message"):
            story.extend([
                Spacer(1, 2 * mm),
                _paragraph(f"Erreur - {run.get('display_name') or run['scrape_type']}: {run['error_message']}", body_style),
            ])

    document.build(story)
    return buffer.getvalue()


def build_daily_report(report_date: date, timezone_name: str | None = None) -> tuple[str, bytes]:
    timezone_name = timezone_name or "Europe/Paris"
    config_path = Path(__file__).resolve().parents[4] / "config" / ".env"
    database_url = physical_database_url(config_path)
    report_data = load_daily_report_data(database_url, report_date, timezone_name)
    pdf_content = build_daily_report_pdf(report_data)
    filename = f"physicaldata-report-{report_date.isoformat()}.pdf"
    return filename, pdf_content