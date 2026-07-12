import orjson
from pydantic import BaseModel, ValidationError


def parse_json_model[ModelT: BaseModel](text: str, model_type: type[ModelT]) -> ModelT:
    cleaned = _extract_json_object(_strip_code_fence(text))
    try:
        data = orjson.loads(cleaned)
    except orjson.JSONDecodeError as exc:
        raise ValueError("AI provider returned invalid JSON") from exc
    try:
        return model_type.model_validate(data)
    except ValidationError as exc:
        raise ValueError("AI provider returned JSON that did not match the schema") from exc


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        return text.strip()

    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1].strip()
    return text[start:].strip()
