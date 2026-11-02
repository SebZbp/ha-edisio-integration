"""User-facing strings must not contain <...>: the HA frontend parses them as tags (edisio-pnv)."""
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).parent.parent / "custom_components" / "edisio"


@pytest.mark.parametrize("fname", ["strings.json", "translations/en.json"])
def test_no_angle_brackets_in_user_strings(fname):
    bad = []

    def walk(node, path=""):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, str) and re.search(r"<[^>]*>", node):
            bad.append((path, node))

    walk(json.loads((ROOT / fname).read_text()))
    assert not bad, bad
