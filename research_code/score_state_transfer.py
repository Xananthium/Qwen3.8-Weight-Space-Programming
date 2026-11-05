"""Strict, deterministic scoring for the four authored state-transfer holdouts.

Usage: python score_state_transfer.py RESULT.json [--output SCORES.json]
       Answer maps and original data-dependent self-tests are not bundled.

The last explicit \\boxed{...} after a closed thinking section is scored.
Room-pair and text/cursor answers also allow exactly two separate final boxes,
in order, if the last box alone is not a complete typed answer. No extra boxes
or contradictory parts are discarded to make that fallback succeed.
Formatting normalization never drops unknown entities or changes sequence order.
Optional --semantic-review JSON is recorded separately and cannot alter scores.
This module uses only the standard library and never calls a model or service.
"""

import argparse
import collections
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
DEFAULT_SCORING = None
GRADER_VERSION = "state_transfer_v2_final_box_or_exact_two_parts"
BOX = re.compile(r"(?<!\\)\\boxed\s*\{")
STYLE = re.compile(r"\\(?:text|textrm|texttt|mathrm|mathbf|mathit|operatorname|boxed)\s*\{([^{}]*)\}")


def _escaped(text, index):
    preceding = index - 1
    while preceding >= 0 and text[preceding] == "\\":
        preceding -= 1
    return (index - preceding - 1) % 2 == 1


def final_boxes(text):
    """Return top-level payloads; never fall back past a malformed last box."""
    if "</think>" not in text:
        return [], "unfinished_thinking"
    final = text.rsplit("</think>", 1)[1]
    if "<think>" in final:
        return [], "unfinished_thinking"
    position, payloads = 0, []
    while match := BOX.search(final, position):
        depth, end = 1, match.end()
        while end < len(final) and depth:
            if not _escaped(final, end):
                depth += (final[end] == "{") - (final[end] == "}")
            end += 1
        if depth:
            return [], "unbalanced_final_box"
        payloads.append(final[match.end():end - 1])
        # Skip nested boxes: the whole outer payload must satisfy the grammar.
        position = end
    return (payloads, None) if payloads else ([], "no_final_box")


def final_box(text):
    payloads, reason = final_boxes(text)
    return (payloads[-1] if payloads else None), reason


def normalize_format(payload):
    text = payload.replace("−", "-").replace("–", "-")
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = re.sub(r"\\(?:left|right|bigl|bigr|Bigl|Bigr)(?![A-Za-z])", "", text)
    for command, replacement in [("langle", "("), ("rangle", ")"),
                                 ("lbrack", "["), ("rbrack", "]"),
                                 ("mid", "|"), ("vert", "|")]:
        text = re.sub(r"\\" + command + r"(?![A-Za-z])", lambda _: replacement, text)
    text = re.sub(r"\\(?:longrightarrow|rightarrow|Rightarrow|to)(?![A-Za-z])|[→⇒]", ",", text)
    text = re.sub(r"\\(?:qquad|quad|space)(?![A-Za-z])|\\[,;:! ]|~", " ", text)
    while STYLE.search(text):
        text = STYLE.sub(r"\1", text)
    text = text.replace(r"\{", "{").replace(r"\}", "}")
    text = re.sub(r"\\[()\[\]]", "", text)
    text = text.replace("$", "").replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip()


def _outer(text):
    pairs = {"(": ")", "[": "]", "{": "}"}
    text = text.strip()
    while len(text) >= 2 and text[0] in pairs and text[-1] == pairs[text[0]]:
        # Only remove a wrapper enclosing the entire payload.
        depth = 0
        for index, char in enumerate(text):
            depth += (char == text[0]) - (char == text[-1])
            if depth == 0:
                break
        if index != len(text) - 1:
            break
        text = text[1:-1].strip()
    return text


def _sequence(text):
    text = _outer(text)
    text = re.sub(r"\s+\b(?:and|then)\b\s+", ",", text, flags=re.I)
    # A plain whitespace-separated list is also unambiguous for these atoms.
    parts = re.split(r"\s*[,;]\s*", text) if re.search(r"[,;]", text) else text.split()
    return [part.strip().strip("\"'") for part in parts]


def answer_kind(answer):
    if isinstance(answer, list):
        return "integer_tuple" if all(type(value) is int for value in answer) else "queue"
    if set(answer) == {"room", "next_room"}:
        return "room_pair"
    if set(answer) == {"text", "characters_left_of_cursor"}:
        return "text_cursor"
    raise ValueError("Unknown frozen answer schema")


def parse_payload(kind, text):
    text = _outer(text)
    if kind == "queue":
        text = re.sub(r"^(?:final\s+)?queue\s*[:=]\s*", "", text, flags=re.I)
        values = _sequence(text)
        return [value.casefold() for value in values] if values and all(re.fullmatch(r"[A-Za-z]+", value) for value in values) else None
    if kind == "integer_tuple":
        text = re.sub(r"^\(\s*x\s*,\s*y\s*,\s*z\s*\)\s*[:=]\s*", "", text, flags=re.I)
        labeled = re.fullmatch(r"x\s*[:=]\s*([+-]?\d+)\s*[,;]\s*y\s*[:=]\s*([+-]?\d+)\s*[,;]\s*z\s*[:=]\s*([+-]?\d+)", text, re.I)
        values = list(labeled.groups()) if labeled else _sequence(text)
        return [int(value) for value in values] if values and all(re.fullmatch(r"[+-]?\d+", value) for value in values) else None
    if kind == "room_pair":
        labeled = re.fullmatch(r"(?:current\s+)?room\s*[:=]\s*([A-Za-z]+)\s*[,;]\s*next(?:[ _]+room)?\s*[:=]\s*([A-Za-z]+)", text, re.I)
        values = list(labeled.groups()) if labeled else _sequence(text)
        if values and all(re.fullmatch(r"[A-Za-z]+", value) for value in values):
            # Keep extra entities so they compare wrong rather than disappearing.
            return [value.casefold() for value in values]
        return None
    if kind == "text_cursor":
        marker = re.fullmatch(r"([A-Za-z]*)\|([A-Za-z]*)", text)
        if marker:
            return {"text": "".join(marker.groups()), "characters_left_of_cursor": len(marker[1])}
        pair = re.fullmatch(
            r"(?:(?:final\s+)?text\s*[:=]\s*)?[\"']?([A-Za-z|]+)[\"']?\s*[,;]\s*"
            r"(?:(?:cursor|characters[ _]+left[ _]+of[ _]+cursor)\s*[:=]\s*)?([+-]?\d+)"
            r"(?:\s+characters?(?:\s+(?:to\s+the\s+)?left(?:\s+of\s+(?:the\s+)?cursor)?)?)?", text, re.I)
        if not pair:
            return None
        literal, count = pair[1], int(pair[2])
        if literal.count("|") > 1:
            return None
        parsed = {"text": literal.replace("|", ""), "characters_left_of_cursor": count}
        if "|" in literal and literal.index("|") != count:
            parsed["conflicting_marker_position"] = literal.index("|")
        return parsed
    raise ValueError("Unknown answer kind: " + kind)


def canonical_gold(answer):
    kind = answer_kind(answer)
    if kind == "queue":
        return [value.casefold() for value in answer]
    if kind == "room_pair":
        return [answer["room"].casefold(), answer["next_room"].casefold()]
    return answer


def _complete_answer(kind, parsed):
    if parsed is None:
        return False
    return len(parsed) == 2 if kind == "room_pair" else True


def parse_separate_parts(kind, parts):
    """Conservative two-part grammar, independent of the frozen answer values."""
    if len(parts) != 2:
        return None
    if kind == "room_pair":
        values = []
        labels = [r"(?:current\s+)?room", r"next(?:[ _]+room)?"]
        for part, label in zip(parts, labels):
            atom = _outer(part)
            atom = re.sub(r"^(?:" + label + r")\s*[:=]\s*", "", atom, flags=re.I)
            atom = atom.strip().strip("\"'")
            if not re.fullmatch(r"[A-Za-z]+", atom):
                return None
            values.append(atom.casefold())
        return values
    if kind == "text_cursor":
        # The existing full-consumption grammar checks labels and cursor-marker
        # consistency; a complete first box plus another number cannot pass.
        return parse_payload(kind, _outer(parts[0]) + "," + _outer(parts[1]))
    return None


def score_output(output, expected):
    kind = answer_kind(expected)
    text = output.get("text", "")
    boxes, reason = final_boxes(text)
    raw = boxes[-1] if boxes else None
    normalized = normalize_format(raw) if raw is not None else None
    parsed = parse_payload(kind, normalized) if normalized is not None else None
    parse_mode, normalized_parts = "single_box", None
    if reason is None and kind in {"room_pair", "text_cursor"} and not _complete_answer(kind, parsed):
        if len(boxes) == 2:
            normalized_parts = [normalize_format(part) for part in boxes]
            parsed = parse_separate_parts(kind, normalized_parts)
            parse_mode = "two_part_boxes"
        elif len(boxes) > 2:
            parsed, reason = None, "extra_part_boxes"
    if output.get("finish_reason") == "length":
        status, reason = "cutoff", "token_limit"
    elif output.get("finish_reason") != "stop":
        status, reason = "unparsed", "not_completed"
    elif parsed is None:
        status, reason = "unparsed", reason or "unsupported_answer_format"
    else:
        status = "correct" if parsed == canonical_gold(expected) else "wrong"
    return {"kind": kind, "status": status, "strict_correct": status == "correct",
            "reason": reason, "raw_box": raw, "normalized_box": normalized,
            "raw_boxes": boxes, "normalized_parts": normalized_parts, "parse_mode": parse_mode,
            "parsed_answer": parsed, "expected": expected,
            "tokens": output.get("tokens"), "finish_reason": output.get("finish_reason"),
            "thinking_closed": "</think>" in text}


def score(result, frozen=None, semantic_review=None):
    if result.get("error"):
        raise ValueError("Cannot score an errored result")
    if frozen is None:
        raise ValueError("Supply the separately authorized frozen scoring map")
    records = result.get("job", {}).get("records")
    if records is not None and sorted(record["id"] for record in records) != sorted(frozen):
        raise ValueError("Result job must contain exactly the four frozen holdouts")
    outputs = {}
    for output in result.get("outputs", []):
        key = output["id"]
        if key not in frozen or key in outputs:
            raise ValueError("Unknown or duplicate output id: " + key)
        outputs[key] = output
    rows = [{"id": key, **score_output(outputs.get(key, {}), item["answer"])}
            for key, item in frozen.items()]
    counts = collections.Counter(row["status"] for row in rows)
    report = {"grader_version": GRADER_VERSION, "rows": rows,
              "summary": {"n": len(rows), "counts": {key: counts[key] for key in ("correct", "wrong", "unparsed", "cutoff")},
                          "strict_accuracy": counts["correct"] / len(rows)}}
    if semantic_review is not None:
        report["semantic_review"] = semantic_review
        report["semantic_review_policy"] = "Agent review only; never overrides strict rows or summary."
    return report


def main():
    parser = argparse.ArgumentParser(description="Frozen state parser; answer map supplied separately.")
    parser.add_argument("result", type=Path)
    parser.add_argument("--scoring", type=Path, required=True)
    parser.add_argument("--semantic-review", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() in {args.result.resolve(), args.scoring.resolve()}:
        parser.error("Refuse existing output or input overwrite")
    semantic = json.loads(args.semantic_review.read_text()) if args.semantic_review else None
    report = score(json.loads(args.result.read_text()), json.loads(args.scoring.read_text()), semantic)
    report["scoring_sha256"] = hashlib.sha256(args.scoring.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"]))

if __name__ == "__main__":
    main()
