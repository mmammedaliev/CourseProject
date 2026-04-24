import xml.etree.ElementTree as ET
from typing import Any, Optional


def _dict_to_xml_elem(tag: str, value: Any, parent: Optional[ET.Element] = None) -> ET.Element:
    """Recursively build an ElementTree element from a value."""
    elem = ET.SubElement(parent, tag) if parent is not None else ET.Element(tag)

    if value is None:
        return elem

    if isinstance(value, dict):
        if 'null_flavor' in value or 'value' in value:
            val_elem = ET.SubElement(elem, 'value')
            v = value.get('value')
            if v is not None:
                val_elem.text = str(v)
            nf = value.get('null_flavor')
            if nf:
                nf_elem = ET.SubElement(elem, 'null_flavor')
                nf_elem.text = str(nf)
        else:
            for k, v in value.items():
                if isinstance(v, list):
                    for item in v:
                        _dict_to_xml_elem(k, item, elem)
                    if len(v) == 1:
                        ET.SubElement(elem, k)
                else:
                    _dict_to_xml_elem(k, v, elem)
        return elem

    if isinstance(value, list):
        for item in value:
            _dict_to_xml_elem(tag, item, parent)
        return elem

    val_elem = ET.SubElement(elem, 'value')
    val_elem.text = str(value)
    return elem


def _to_xml(data: Any, root_tag: str) -> str:
    """Convert dict (from JSON) back to E2B R3 application XML."""
    root = ET.Element(root_tag)
    if isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, list):
                for item in val:
                    _dict_to_xml_elem(key, item, root)
                if len(val) == 1:
                    ET.SubElement(root, key)
            else:
                _dict_to_xml_elem(key, val, root)
    ET.indent(root, space='  ')
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='unicode')
