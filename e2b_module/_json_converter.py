import json
from typing import Any, Dict


def _clean_for_json(data: Any, include_empty: bool = False) -> Any:
    if data is None:
        return None
    if isinstance(data, list):
        items = [_clean_for_json(i, include_empty) for i in data]
        if not include_empty:
            items = [i for i in items if i not in (None, {}, [], '')]
        return items
    if isinstance(data, dict):
        if '_null_flavor' in data:
            return {'null_flavor': data['_null_flavor'], 'value': data.get('_value')}
        result = {}
        for k, v in data.items():
            cleaned = _clean_for_json(v, include_empty)
            if include_empty or cleaned not in (None, {}, [], ''):
                result[k] = cleaned
        return result
    return data


def _to_json(data: Dict[str, Any], root_tag: str,
             indent: int = 2, include_empty: bool = False) -> str:
    cleaned = _clean_for_json(data, include_empty)
    wrapper = {root_tag: cleaned}
    return json.dumps(wrapper, ensure_ascii=False, indent=indent, default=str)
