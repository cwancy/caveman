import tomllib

_PARSERS = {
    "substitution": lambda e: {
        "type": "substitution",
        "from_": e["from"],
        "to": e.get("to", ""),
        "case_insensitive": e.get("case_insensitive", True),
    },
    "strip": lambda e: {
        "type": "strip",
        "target": e["target"],
        "phrases": e.get("phrases", []),
    },
    "deduplicate": lambda e: {
        "type": "deduplicate",
        "scope": e.get("scope", "sentences"),
    },
    "exempt": lambda e: {
        "type": "exempt",
        "targets": e.get("targets", []),
    },
    "whitespace": lambda e: {
        "type": "whitespace",
        "ops": e.get("ops", []),
    },
}


def load_rules(path) -> list[dict]:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return [
        _PARSERS[e["type"]](e) for e in data.get("rules", []) if e["type"] in _PARSERS
    ]
