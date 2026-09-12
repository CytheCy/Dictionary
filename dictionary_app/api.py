from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any, Iterable


DICTIONARY_ENDPOINT = "https://www.dictionaryapi.com/api/v3/references/collegiate/json/"
THESAURUS_ENDPOINT = "https://www.dictionaryapi.com/api/v3/references/thesaurus/json/"
FREE_DICTIONARY_ENDPOINT = "https://api.dictionaryapi.dev/api/v2/entries/en/"


@dataclass
class Sense:
    number: str = ""
    definition: str = ""
    examples: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    antonyms: list[str] = field(default_factory=list)


@dataclass
class Entry:
    headword: str
    functional_label: str = ""
    pronunciation: str = ""
    senses: list[Sense] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    antonyms: list[str] = field(default_factory=list)
    etymology: str = ""


_TOKEN_RE = re.compile(r"\{([^{}]*)\}")
_SPACE_RE = re.compile(r"\s+")


def clean_markup(value: Any) -> str:
    """Turn Merriam-Webster's inline formatting tokens into readable plain text."""
    if value is None:
        return ""
    text = str(value)
    previous = None
    while previous != text:
        previous = text

        def replace(match: re.Match[str]) -> str:
            parts = match.group(1).split("|")
            tag = parts[0]
            if tag in {"bc"}:
                return ": "
            if tag in {"ldquo", "rdquo"}:
                return '"'
            if tag == "mdash":
                return "—"
            if tag in {"it", "/it", "wi", "/wi", "sc", "/sc", "inf", "/inf", "sup", "/sup", "parahw", "/parahw"}:
                return ""
            if tag in {"sx", "d_link", "a_link", "i_link", "et_link", "mat", "phrase", "qword", "ds", "dxt"}:
                return parts[1] if len(parts) > 1 else ""
            return parts[1] if len(parts) > 1 else ""

        text = _TOKEN_RE.sub(replace, text)
    return _SPACE_RE.sub(" ", html.unescape(text)).strip(" ;,")


def _unique(words: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for word in words:
        word = clean_markup(word)
        marker = word.casefold()
        if word and marker not in seen:
            seen.add(marker)
            result.append(word)
    return result


def _word_list(groups: Any) -> list[str]:
    words: list[str] = []
    if not isinstance(groups, list):
        return words
    for group in groups:
        if isinstance(group, list):
            for item in group:
                if isinstance(item, dict):
                    word = item.get("wd", "")
                    if word:
                        words.append(word)
                elif isinstance(item, str):
                    words.append(item)
    return _unique(words)


def _parse_dt(dt: Any) -> tuple[str, list[str]]:
    definition_parts: list[str] = []
    examples: list[str] = []
    if not isinstance(dt, list):
        return "", []
    for item in dt:
        if not isinstance(item, list) or len(item) < 2:
            continue
        kind, value = item[0], item[1]
        if kind == "text":
            definition_parts.append(clean_markup(value))
        elif kind == "vis" and isinstance(value, list):
            examples.extend(clean_markup(v.get("t", "")) for v in value if isinstance(v, dict))
    return " ".join(filter(None, definition_parts)).strip(), list(filter(None, examples))


def _parse_sense(data: dict[str, Any]) -> Sense | None:
    definition, examples = _parse_dt(data.get("dt"))
    synonyms = _word_list(data.get("syn_list"))
    antonyms = _word_list(data.get("ant_list"))
    if not (definition or examples or synonyms or antonyms):
        return None
    return Sense(clean_markup(data.get("sn", "")), definition, examples, synonyms, antonyms)


def _walk_sseq(node: Any) -> list[Sense]:
    result: list[Sense] = []
    if isinstance(node, list):
        if (
            len(node) >= 2
            and isinstance(node[0], str)
            and node[0] in {"sense", "sen", "sdsense"}
            and isinstance(node[1], dict)
        ):
            parsed = _parse_sense(node[1])
            if parsed:
                result.append(parsed)
        else:
            for child in node:
                result.extend(_walk_sseq(child))
    elif isinstance(node, dict):
        parsed = _parse_sense(node)
        if parsed:
            result.append(parsed)
    return result


def _etymology(entry: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in entry.get("et", []):
        if isinstance(block, list) and len(block) >= 2 and block[0] == "text":
            parts.append(clean_markup(block[1]))
    return " ".join(filter(None, parts))


def parse_response(payload: Any) -> tuple[list[Entry], list[str]]:
    """Parse either Collegiate endpoint; string arrays are spelling suggestions."""
    if not isinstance(payload, list):
        raise ValueError("The service returned an unexpected response.")
    if not payload:
        return [], []
    if all(isinstance(item, str) for item in payload):
        return [], _unique(payload)

    entries: list[Entry] = []
    for raw in payload:
        if not isinstance(raw, dict):
            continue
        meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
        hwi = raw.get("hwi") if isinstance(raw.get("hwi"), dict) else {}
        headword = clean_markup(hwi.get("hw") or str(meta.get("id", "")).split(":", 1)[0]).replace("*", "·")
        pronunciation = ""
        prs = hwi.get("prs", [])
        if isinstance(prs, list):
            pronunciation = next((clean_markup(p.get("mw")) for p in prs if isinstance(p, dict) and p.get("mw")), "")
        senses: list[Sense] = []
        for definition in raw.get("def", []):
            if isinstance(definition, dict):
                senses.extend(_walk_sseq(definition.get("sseq", [])))
        entries.append(
            Entry(
                headword=headword or "Entry",
                functional_label=clean_markup(raw.get("fl", "")),
                pronunciation=pronunciation,
                senses=senses,
                synonyms=_word_list(meta.get("syns", [])),
                antonyms=_word_list(meta.get("ants", [])),
                etymology=_etymology(raw),
            )
        )
    return entries, []


def parse_free_dictionary_response(payload: Any) -> tuple[list[Entry], list[str]]:
    """Map dictionaryapi.dev's response into WordDesk's shared entry model."""
    if isinstance(payload, dict) and payload.get("title"):
        return [], []
    if not isinstance(payload, list):
        raise ValueError("The service returned an unexpected response.")

    entries: list[Entry] = []
    for raw in payload:
        if not isinstance(raw, dict):
            continue
        headword = clean_markup(raw.get("word", "")) or "Entry"
        pronunciation = clean_markup(raw.get("phonetic", ""))
        if not pronunciation:
            phonetics = raw.get("phonetics", [])
            if isinstance(phonetics, list):
                pronunciation = next(
                    (clean_markup(item.get("text", "")) for item in phonetics if isinstance(item, dict) and item.get("text")),
                    "",
                )
        origin = clean_markup(raw.get("origin", ""))
        meanings = raw.get("meanings", [])
        if not isinstance(meanings, list):
            meanings = []
        for meaning in meanings:
            if not isinstance(meaning, dict):
                continue
            senses: list[Sense] = []
            definitions = meaning.get("definitions", [])
            if not isinstance(definitions, list):
                definitions = []
            for index, definition in enumerate(definitions, 1):
                if not isinstance(definition, dict):
                    continue
                definition_text = clean_markup(definition.get("definition", ""))
                example = clean_markup(definition.get("example", ""))
                synonyms = _unique(definition.get("synonyms", [])) if isinstance(definition.get("synonyms"), list) else []
                antonyms = _unique(definition.get("antonyms", [])) if isinstance(definition.get("antonyms"), list) else []
                if definition_text or example or synonyms or antonyms:
                    senses.append(Sense(str(index), definition_text, [example] if example else [], synonyms, antonyms))
            entries.append(
                Entry(
                    headword=headword,
                    functional_label=clean_markup(meaning.get("partOfSpeech", "")),
                    pronunciation=pronunciation,
                    senses=senses,
                    synonyms=_unique(meaning.get("synonyms", [])) if isinstance(meaning.get("synonyms"), list) else [],
                    antonyms=_unique(meaning.get("antonyms", [])) if isinstance(meaning.get("antonyms"), list) else [],
                    etymology=origin,
                )
            )
    return entries, []
