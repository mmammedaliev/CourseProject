import re
from typing import Any, Optional

from _constants import FIELD_LABELS, ENUM_LABELS, NULL_FLAVOR_LABELS


def _fmt_date(hl7: Optional[str]) -> str:
    """Convert HL7 compact date (YYYYMMDD…) to ISO-style string."""
    if not hl7:
        return ''
    s = str(hl7).strip()
    if re.match(r'^\d{8}$', s):
        return f'{s[0:4]}-{s[4:6]}-{s[6:8]}'
    if re.match(r'^\d{6}$', s):
        return f'{s[0:4]}-{s[4:6]}'
    if re.match(r'^\d{4}$', s):
        return s
    return s


def _resolve_enum(field: str, raw: Optional[str]) -> str:
    """Return human-readable label for an enum field value, or raw value."""
    if raw is None:
        return ''
    mapping = ENUM_LABELS.get(field, {})
    return mapping.get(str(raw), str(raw))


def _label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace('_', ' ').title())


def _fmt_val(field: str, raw: Any) -> str:
    """Format a raw parsed value for display (HTML/JSON)."""
    if raw is None:
        return ''
    if isinstance(raw, dict):
        nf = raw.get('_null_flavor')
        if nf:
            return f'[{NULL_FLAVOR_LABELS.get(nf, nf)}]'
        return str(raw.get('_value') or '')
    resolved = _resolve_enum(field, str(raw))
    if any(kw in field for kw in ('date', 'birth', 'creation', 'received', 'recent',
                                   'death', 'start', 'end', 'last_administration',
                                   'date_time')):
        return _fmt_date(resolved) or resolved
    return resolved


def _scalar(raw: Any) -> Optional[str]:
    """Extract scalar string from parsed value."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        v = raw.get('_value')
        return str(v) if v is not None else None
    return str(raw)
