from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Iterable


DICTIONARY_ENDPOINT = "https://www.dictionaryapi.com/api/v3/references/collegiate/json/"
THESAURUS_ENDPOINT = "https://www.dictionaryapi.com/api/v3/references/thesaurus/json/"
DATAMUSE_ENDPOINT = "https://api.datamuse.com/words"
WORDNET_ENDPOINT = "https://en-word.net/api/lemma/"
MOBY_ENDPOINT = "https://dict.org/bin/Dict"


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


def parse_datamuse_response(payload: Any) -> tuple[list[Entry], list[str]]:
    """Map an exact Datamuse lookup into WordDesk's shared entry model."""
    if not isinstance(payload, list):
        raise ValueError("Datamuse returned an unexpected response.")
    if not payload or not isinstance(payload[0], dict):
        return [], []

    raw = payload[0]
    headword = clean_markup(raw.get("word", "")) or "Entry"
    tags = raw.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    pronunciation = next(
        (clean_markup(tag.split(":", 1)[1]) for tag in tags if isinstance(tag, str) and tag.startswith("ipa_pron:")),
        "",
    )
    if pronunciation:
        pronunciation = f"/{pronunciation}/"

    labels = {"n": "noun", "v": "verb", "adj": "adjective", "adv": "adverb", "u": "other"}
    grouped: dict[str, list[Sense]] = {}
    definitions = raw.get("defs", [])
    if not isinstance(definitions, list):
        definitions = []
    for definition in definitions:
        if not isinstance(definition, str):
            continue
        part, separator, text = definition.partition("\t")
        label = labels.get(part, part) if separator else ""
        definition_text = clean_markup(text if separator else part)
        if definition_text:
            senses = grouped.setdefault(label, [])
            senses.append(Sense(str(len(senses) + 1), definition_text))

    entries = [
        Entry(headword=headword, functional_label=label, pronunciation=pronunciation, senses=senses)
        for label, senses in grouped.items()
    ]
    return entries, []


class _MobyResultsParser(HTMLParser):
    """Collect preformatted definition blocks from a DICT result page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_pre = False
        self.block_text: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "pre":
            self.in_pre = True
            self.block_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "pre" and self.in_pre:
            self.blocks.append("".join(self.block_text))
            self.in_pre = False
            self.block_text = []

    def handle_data(self, data: str) -> None:
        if self.in_pre:
            self.block_text.append(data)


def parse_moby_response(payload: Any, word: str) -> tuple[list[Entry], list[str]]:
    """Map a dict.org Moby Thesaurus result page into the shared entry model."""
    if not isinstance(payload, str):
        raise ValueError("Moby Thesaurus returned an unexpected response.")
    parser = _MobyResultsParser()
    parser.feed(payload)
    result_text = next((block for block in parser.blocks if "Moby Thesaurus words for" in block), "")
    _, separator, word_text = result_text.partition(":")
    synonyms = [] if not separator else _unique(word_text.split(","))
    synonyms = [item for item in synonyms if item.casefold() != word.casefold()]
    if not synonyms:
        return [], []
    return [Entry(headword=clean_markup(word), synonyms=synonyms)], []


def parse_wordnet_response(payload: Any, word: str = "") -> tuple[list[Entry], list[str]]:
    """Map Open English WordNet synsets into entries grouped by part of speech."""
    if not isinstance(payload, list):
        raise ValueError("WordNet returned an unexpected response.")

    labels = {"n": "noun", "v": "verb", "a": "adjective", "s": "adjective", "r": "adverb"}
    grouped: dict[str, Entry] = {}
    searched = clean_markup(word).replace("_", " ")

    for raw in payload:
        if not isinstance(raw, dict):
            continue
        part = clean_markup(raw.get("partOfSpeech", ""))
        label = labels.get(part, part)
        members = raw.get("members", [])
        if not isinstance(members, list):
            members = []
        lemmas = _unique(
            str(member.get("lemma", "")).replace("_", " ")
            for member in members
            if isinstance(member, dict)
        )
        headword = searched or (lemmas[0] if lemmas else "Entry")
        entry = grouped.setdefault(label, Entry(headword=headword, functional_label=label))

        matching_member = next(
            (
                member
                for member in members
                if isinstance(member, dict)
                and clean_markup(member.get("lemma", "")).replace("_", " ").casefold() == headword.casefold()
            ),
            None,
        )
        if not entry.pronunciation and matching_member:
            pronunciations = matching_member.get("pronunciation", [])
            if isinstance(pronunciations, list):
                value = next(
                    (
                        clean_markup(item.get("value", ""))
                        for item in pronunciations
                        if isinstance(item, dict) and item.get("value")
                    ),
                    "",
                )
                if value:
                    entry.pronunciation = f"/{value}/"

        definitions = raw.get("definition", [])
        if not isinstance(definitions, list):
            definitions = []
        examples = raw.get("example", [])
        if not isinstance(examples, list):
            examples = []
        example_texts = [
            clean_markup(example.get("text", "") if isinstance(example, dict) else example)
            for example in examples
        ]
        synonyms = [lemma for lemma in lemmas if lemma.casefold() != headword.casefold()]
        antonym_relations = raw.get("antonym", [])
        if not isinstance(antonym_relations, list):
            antonym_relations = []
        antonyms = _unique(
            str(relation.get("target_lemma", "")).replace("_", " ")
            for relation in antonym_relations
            if isinstance(relation, dict)
        )
        for definition in definitions:
            definition_text = clean_markup(definition)
            if definition_text:
                entry.senses.append(
                    Sense(
                        number=str(len(entry.senses) + 1),
                        definition=definition_text,
                        examples=list(filter(None, example_texts)),
                        synonyms=synonyms,
                        antonyms=antonyms,
                    )
                )

    return list(grouped.values()), []
