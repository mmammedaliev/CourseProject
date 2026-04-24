from datetime import datetime
from html import escape as he
from typing import Any, Dict

from _constants import NULL_FLAVOR_LABELS, __version__
from _helpers import _fmt_date, _fmt_val, _label, _resolve_enum, _scalar

_HTML_CSS = """
<style>
  *, *::before, *::after { box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: #1a1a2e;
    background: #f4f6fb;
    margin: 0;
    padding: 20px;
  }
  .report-wrapper {
    max-width: 960px;
    margin: 0 auto;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0,0,0,.12);
    overflow: hidden;
  }
  .report-header {
    background: linear-gradient(135deg, #1a237e 0%, #283593 60%, #3949ab 100%);
    color: #fff;
    padding: 28px 36px 20px;
  }
  .report-header h1 { margin: 0 0 4px; font-size: 22px; letter-spacing: .5px; }
  .report-header .subtitle { font-size: 12px; opacity: .8; margin-bottom: 12px; }
  .report-header .meta { display: flex; gap: 32px; flex-wrap: wrap; }
  .report-header .meta-item { font-size: 12px; }
  .report-header .meta-item strong { display: block; font-size: 13px; }
  .report-body { padding: 24px 36px 32px; }
  .section {
    margin-bottom: 20px;
    border: 1px solid #e0e4ef;
    border-radius: 6px;
    overflow: hidden;
  }
  .section-title {
    background: #e8eaf6;
    color: #1a237e;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 14px;
    text-transform: uppercase;
    letter-spacing: .6px;
    border-bottom: 1px solid #c5cae9;
  }
  .section-body { padding: 12px 14px; }
  table.fields {
    width: 100%;
    border-collapse: collapse;
  }
  table.fields td {
    padding: 5px 8px;
    vertical-align: top;
    border-bottom: 1px solid #f0f2f8;
    font-size: 12.5px;
  }
  table.fields tr:last-child td { border-bottom: none; }
  table.fields td.field-label {
    width: 46%;
    color: #5c6bc0;
    font-weight: 500;
  }
  table.fields td.field-value { color: #212121; }
  .badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
  }
  .badge-yes  { background: #ffebee; color: #c62828; }
  .badge-no   { background: #e8f5e9; color: #2e7d32; }
  .badge-nf   { background: #fff8e1; color: #f57f17; font-style: italic; }
  .subsection-list { margin-top: 8px; }
  .subsection-item {
    background: #fafbff;
    border: 1px solid #e8eaf6;
    border-radius: 4px;
    margin-bottom: 8px;
    padding: 10px 12px;
  }
  .subsection-item:last-child { margin-bottom: 0; }
  .subsection-index {
    font-size: 11px;
    color: #7986cb;
    font-weight: 700;
    margin-bottom: 6px;
    text-transform: uppercase;
  }
  .narrative-block {
    background: #f8f9ff;
    border-left: 3px solid #5c6bc0;
    padding: 12px 14px;
    font-size: 12.5px;
    line-height: 1.7;
    white-space: pre-wrap;
    border-radius: 0 4px 4px 0;
  }
  .seriousness-flags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px; }
  .report-footer {
    text-align: center;
    font-size: 11px;
    color: #9e9e9e;
    padding: 12px;
    border-top: 1px solid #e0e4ef;
  }
</style>
"""


def _bool_badge(val: Any) -> str:
    s = str(val).lower()
    if s in ('true', '1', 'yes'):
        return '<span class="badge badge-yes">YES</span>'
    if s in ('false', '0', 'no'):
        return '<span class="badge badge-no">NO</span>'
    return he(str(val))


def _nf_badge(nf_code: str) -> str:
    label = NULL_FLAVOR_LABELS.get(nf_code, nf_code)
    return f'<span class="badge badge-nf">[{he(label)}]</span>'


def _render_fields_table(fields: Dict[str, Any]) -> str:
    rows = []
    for field, raw in fields.items():
        if raw is None or raw == {} or raw == [] or raw == '':
            continue
        if isinstance(raw, (dict, list)):
            continue
        label = _label(field)
        display = he(_fmt_val(field, raw))
        if str(raw).lower() in ('true', 'false', '1', '0'):
            display = _bool_badge(raw)
        rows.append(
            f'<tr><td class="field-label">{he(label)}</td>'
            f'<td class="field-value">{display}</td></tr>'
        )
    if not rows:
        return ''
    return '<table class="fields">' + ''.join(rows) + '</table>'


def _render_obj(data: Dict[str, Any], depth: int = 0) -> str:
    """Render a dict of fields + nested lists as HTML."""
    parts = []
    scalars = {k: v for k, v in data.items()
               if not isinstance(v, (dict, list))}
    parts.append(_render_fields_table(scalars))

    for key, val in data.items():
        if isinstance(val, list) and val:
            items_html = []
            for idx, item in enumerate(val, 1):
                if isinstance(item, dict):
                    inner = _render_obj(item, depth + 1)
                else:
                    inner = he(str(item))
                items_html.append(
                    f'<div class="subsection-item">'
                    f'<div class="subsection-index">#{idx}</div>{inner}</div>'
                )
            parts.append(
                f'<div style="margin-top:8px"><strong style="font-size:12px;color:#5c6bc0">'
                f'{he(_label(key))}</strong>'
                f'<div class="subsection-list">{"".join(items_html)}</div></div>'
            )
        elif isinstance(val, dict):
            if '_null_flavor' in val:
                pass
            else:
                inner = _render_obj(val, depth + 1)
                parts.append(
                    f'<div style="margin-top:8px"><strong style="font-size:12px;color:#5c6bc0">'
                    f'{he(_label(key))}</strong><div style="margin-left:10px">{inner}</div></div>'
                )
    return ''.join(p for p in parts if p)


def _to_html(data: Dict[str, Any], root_tag: str) -> str:
    """Generate a professional HTML report from parsed ICSR data."""

    c1 = data.get('c_1_identification_case_safety_report') or {}
    case_id   = _scalar(c1.get('c_1_1_sender_safety_report_unique_id')) or 'N/A'
    wwuid     = _scalar(c1.get('c_1_8_1_worldwide_unique_case_identification_number')) or 'N/A'
    date_cr   = _fmt_date(_scalar(c1.get('c_1_2_date_creation'))) or 'N/A'
    type_code = _scalar(c1.get('c_1_3_type_report'))
    rtype     = _resolve_enum('c_1_3_type_report', type_code) if type_code else 'N/A'

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M UTC')

    header = f"""
    <div class="report-header">
      <h1>Individual Case Safety Report (ICSR)</h1>
      <div class="subtitle">ICH E2B(R3) &mdash; Pharmacovigilance Report</div>
      <div class="meta">
        <div class="meta-item"><strong>{he(case_id)}</strong>Sender Report ID</div>
        <div class="meta-item"><strong>{he(wwuid)}</strong>Worldwide Unique Case ID</div>
        <div class="meta-item"><strong>{he(date_cr)}</strong>Date of Creation</div>
        <div class="meta-item"><strong>{he(rtype)}</strong>Report Type</div>
        <div class="meta-item"><strong>{now_str}</strong>Exported at</div>
      </div>
    </div>
    """

    SECTIONS = [
        ('c_1_identification_case_safety_report', 'C.1 — Identification of the Case Safety Report'),
        ('c_2_r_primary_source_information',      'C.2 — Primary Source Information'),
        ('c_3_information_sender_case_safety_report', 'C.3 — Information Sender'),
        ('c_4_r_literature_reference',            'C.4 — Literature Reference'),
        ('c_5_study_identification',              'C.5 — Study Identification'),
        ('d_patient_characteristics',             'D — Patient Characteristics'),
        ('e_i_reaction_event',                    'E — Reaction(s) / Event(s)'),
        ('f_r_results_tests_procedures_investigation_patient', 'F — Results of Tests and Procedures'),
        ('g_k_drug_information',                  'G — Drug(s) Information'),
        ('h_narrative_case_summary',              'H — Narrative Case Summary'),
    ]

    body_parts = []
    for key, title in SECTIONS:
        val = data.get(key)
        if val is None or val == [] or val == {}:
            continue

        if isinstance(val, list):
            items_html = []
            for idx, item in enumerate(val, 1):
                inner = _render_obj(item) if isinstance(item, dict) else he(str(item))
                items_html.append(
                    f'<div class="subsection-item">'
                    f'<div class="subsection-index">Entry #{idx}</div>{inner}</div>'
                )
            content = f'<div class="section-body"><div class="subsection-list">{"".join(items_html)}</div></div>'
        else:
            if key == 'h_narrative_case_summary':
                narrative = _scalar(val.get('h_1_case_narrative', '')) or ''
                reporter  = _scalar(val.get('h_2_reporter_comments', '')) or ''
                sender    = _scalar(val.get('h_4_sender_comments', '')) or ''
                inner = ''
                if narrative:
                    inner += (f'<div style="margin-bottom:10px"><div class="field-label" '
                              f'style="color:#5c6bc0;font-weight:600;margin-bottom:4px">'
                              f'{he(_label("h_1_case_narrative"))}</div>'
                              f'<div class="narrative-block">{he(narrative)}</div></div>')
                if reporter:
                    inner += (f'<div style="margin-bottom:10px"><div class="field-label" '
                              f'style="color:#5c6bc0;font-weight:600;margin-bottom:4px">'
                              f"{he(_label('h_2_reporter_comments'))}</div>"
                              f'<div class="narrative-block">{he(reporter)}</div></div>')
                if sender:
                    inner += (f'<div style="margin-bottom:10px"><div class="field-label" '
                              f'style="color:#5c6bc0;font-weight:600;margin-bottom:4px">'
                              f"{he(_label('h_4_sender_comments'))}</div>"
                              f'<div class="narrative-block">{he(sender)}</div></div>')
                rest = {k: v for k, v in val.items()
                        if k not in ('h_1_case_narrative', 'h_2_reporter_comments', 'h_4_sender_comments')}
                inner += _render_obj(rest)
                content = f'<div class="section-body">{inner}</div>'
            else:
                inner = _render_obj(val)
                content = f'<div class="section-body">{inner}</div>'

        body_parts.append(
            f'<div class="section">'
            f'<div class="section-title">{he(title)}</div>'
            f'{content}</div>'
        )

    body_html = ''.join(body_parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ICSR Report — {he(case_id)}</title>
  {_HTML_CSS}
</head>
<body>
  <div class="report-wrapper">
    {header}
    <div class="report-body">
      {body_html}
    </div>
    <div class="report-footer">
      Generated by E2B R3 Import/Export Module v{__version__} &nbsp;|&nbsp;
      ICH E2B(R3) Standard &nbsp;|&nbsp; License: GPL v3
    </div>
  </div>
</body>
</html>"""
