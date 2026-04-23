import re

_BLOCK_TOKEN = "__CAVEMAN_BLOCK_{i}__"


def run_pipeline(text: str, rules: list[dict]) -> dict:
    original = text
    by_type = lambda t: [r for r in rules if r["type"] == t]

    text = _strip_markdown(text)
    text, protected = _exempt_blocks(text, by_type("exempt"))
    text = _strip_fillers(text, by_type("strip"))
    text = _substitutions(text, by_type("substitution"))
    text = _deduplicate(text, by_type("deduplicate"))
    text = _fuzzy_deduplicate(text, by_type("deduplicate"))
    text = _normalise_whitespace(text)
    text = _whitespace(text, by_type("whitespace"))
    text = _capitalise_sentences(text)
    text = _restore_blocks(text, protected)

    return {
        "original": original,
        "output": text,
        "original_chars": len(original),
        "output_chars": len(text),
        "reduction_pct": round((1 - len(text) / max(len(original), 1)) * 100, 1),
        "protected_blocks": protected,
    }


def _strip_markdown(text: str) -> str:
    patterns = [
        (r"^#{1,6}\s+", "", re.MULTILINE),
        (r"\*\*(.*?)\*\*", r"\1", 0),
        (r"\*(.*?)\*", r"\1", 0),
        (r"__(.*?)__", r"\1", 0),
        (r"^>\s+", "", re.MULTILINE),
        (r"^[-*+]\s+", "", re.MULTILINE),
        (r"^\d+\.\s+", "", re.MULTILINE),
    ]
    for pattern, repl, flags in patterns:
        text = re.sub(pattern, repl, text, flags=flags)
    return text


def _exempt_blocks(text: str, rules: list[dict]) -> tuple[str, dict]:
    protected = {}
    targets = {t for r in rules for t in r["targets"]} or {"code_blocks"}

    def _protect(m):
        token = _BLOCK_TOKEN.format(i=len(protected))
        protected[token] = m.group(0)
        return token

    block_patterns = {
        "code_blocks": [(r"```[\s\S]*?```", _protect), (r"`[^`]+`", _protect)],
        "tables": [(r"(\|.+\|\n)+", _protect)],
    }

    for target, patterns in block_patterns.items():
        if target in targets:
            for pattern, handler in patterns:
                text = re.sub(pattern, handler, text)

    return text, protected


def _strip_fillers(text: str, rules: list[dict]) -> str:
    phrases = [
        p for r in rules if r["target"] == "filler_phrases" for p in r["phrases"]
    ]
    for phrase in phrases:
        text = re.sub(
            r"\b" + re.escape(phrase) + r"\b[,.]?\s*", " ", text, flags=re.IGNORECASE
        )
        text = re.sub(
            r"[,.]?\s*\b" + re.escape(phrase) + r"\b", " ", text, flags=re.IGNORECASE
        )
    text = re.sub(r"(?<=[.!?])\s*,\s*", " ", text)
    text = re.sub(r"^\s*,\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\.\s*,\s*", ". ", text)
    return re.sub(r" {2,}", " ", text)


def _substitutions(text: str, rules: list[dict]) -> str:
    for rule in rules:
        flags = re.IGNORECASE if rule["case_insensitive"] else 0
        pattern = r"\b" + re.escape(rule["from_"].strip()) + r"\b"
        text = re.sub(pattern, rule["to"], text, flags=flags)
    return text


def _tokenize(sentence: str) -> set[str]:
    return set(re.sub(r"[^a-z0-9\s]", "", sentence.lower()).split())


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _split_sentences(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"((?<=[.!?])\s+|\n+)", text)
    result = []
    i = 0
    while i < len(parts):
        segment = parts[i]
        delimiter = parts[i + 1] if i + 1 < len(parts) else ""
        result.append((segment, delimiter))
        i += 2
    return result


def _deduplicate(text: str, rules: list[dict]) -> str:
    if not rules:
        return text
    seen, unique = set(), []
    segments = re.split(r"((?<=[.!?])\s+|\n+)", text)
    for segment in segments:
        stripped = segment.strip()
        if not stripped:
            unique.append(segment)
            continue
        key = re.sub(r"[^a-z0-9]", "", stripped.lower())
        if not key:
            unique.append(segment)
            continue
        if key not in seen:
            seen.add(key)
            unique.append(segment)
    return "".join(unique)


def _fuzzy_deduplicate(text: str, rules: list[dict], threshold: float = 0.75) -> str:
    if not rules:
        return text

    pairs = _split_sentences(text)
    kept = []
    seen_tokens: list[set[str]] = []

    for sentence, delimiter in pairs:
        stripped = sentence.strip()
        if not stripped:
            kept.append((sentence, delimiter))
            continue

        tokens = _tokenize(stripped)
        if len(tokens) < 3:
            kept.append((sentence, delimiter))
            continue

        is_duplicate = any(_jaccard(tokens, s) >= threshold for s in seen_tokens)

        if not is_duplicate:
            seen_tokens.append(tokens)
            kept.append((sentence, delimiter))

    return "".join(s + d for s, d in kept)


def _normalise_whitespace(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    return text.strip()


def _whitespace(text: str, rules: list[dict]) -> str:
    if not rules:
        return text
    ops = {op for r in rules for op in r["ops"]}
    if "remove_double_spaces" in ops:
        text = re.sub(r" {2,}", " ", text)
    if "remove_leading_spaces" in ops:
        text = re.sub(r"^ +", "", text, flags=re.MULTILINE)
    if "remove_trailing_spaces" in ops:
        text = re.sub(r" +$", "", text, flags=re.MULTILINE)
    if "remove_blank_lines" in ops:
        text = re.sub(r"\n{2,}", "\n", text)
    return text


def _capitalise_sentences(text: str) -> str:
    text = re.sub(r"(?<=[.!?]\s)([a-z])", lambda m: m.group(1).upper(), text)
    text = re.sub(r"(?:^|\n)([a-z])", lambda m: m.group(0).upper(), text)
    return text


def _restore_blocks(text: str, protected: dict) -> str:
    for token, original in protected.items():
        text = text.replace(token, original)
    return text
