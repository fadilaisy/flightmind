"""Helpers for the agent tests: a fake Claude client and the contract's AskResponse schema."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import yaml

SPEC = yaml.safe_load((Path(__file__).parents[3] / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))


def inline(node):
    """Resolve $refs and turn OpenAPI 3.0 `nullable` into JSON Schema."""
    if isinstance(node, list):
        return [inline(n) for n in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return inline(SPEC["components"]["schemas"][node["$ref"].split("/")[-1]])
    out = {k: inline(v) for k, v in node.items()}
    if out.pop("nullable", False) and "type" in out:
        out["type"] = [out["type"], "null"]
    return out


def check_ask_response(body):
    jsonschema.validate(body, inline({"$ref": "#/components/schemas/AskResponse"}))


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def thinking_block(text="reasoning"):
    return SimpleNamespace(type="thinking", thinking=text, signature="sig")


def tool_use(id, name, input):
    return SimpleNamespace(type="tool_use", id=id, name=name, input=input)


def usage(i=100, o=20, cc=0, cr=0):
    return SimpleNamespace(
        input_tokens=i, output_tokens=o, cache_creation_input_tokens=cc, cache_read_input_tokens=cr
    )


def response(stop_reason, content, use=None, model="claude-haiku-5-5"):
    return SimpleNamespace(stop_reason=stop_reason, content=content, usage=use or usage(), model=model)


def tool_turn(*blocks):
    return response("tool_use", list(blocks))


def final_turn(status, claims):
    return response("end_turn", [text_block(json.dumps({"status": status, "claims": claims}))])


def claim(text, *cites):
    return {"text": text, "citations": [{"kind": k, "id": i} for k, i in cites]}


class FakeMessages:
    def __init__(self, owner):
        self._owner = owner

    async def create(self, **kwargs):
        owner = self._owner
        recorded = dict(kwargs)
        recorded["messages"] = copy.copy(kwargs["messages"])  # the loop appends to the same list
        owner.calls.append(recorded)
        if owner.on_call:
            owner.on_call(len(owner.calls))
        item = owner.script.pop(0) if owner.script else owner.repeat
        if isinstance(item, BaseException):
            raise item
        return item


class FakeAnthropic:
    """Stands in for AsyncAnthropic: scripted responses, recorded request arguments."""

    def __init__(self, script=None, repeat=None, on_call=None):
        self.script = list(script or [])
        self.repeat = repeat
        self.on_call = on_call
        self.calls = []
        self.messages = FakeMessages(self)
