"""Unit tests for the example ask-ai endpoint.

The context builders are module-level pure functions, so the caps (the part
that actually matters -- how much leaves ThreatConnect) are tested without
boto3 or a network call. The endpoint tests inject a fake Bedrock client.
"""

# standard library
import json
import sys
from pathlib import Path
from types import SimpleNamespace

# third-party
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

pytest.importorskip('falcon', reason='falcon not importable (run `tcex deps`)')
pytest.importorskip('tcex', reason='tcex not importable (run `tcex deps`)')

# first-party
from _common import FakeResponse, make_endpoint  # noqa: E402
from api.endpoint.example import ask_ai  # noqa: E402

# ── pure builders ─────────────────────────────────────────────────────────


def test_truncate_marks_cut_values():
    out = ask_ai.truncate('x' * 600, limit=10)
    assert out == 'x' * 10 + ask_ai.TRUNCATION_MARKER


def test_serialize_context_handles_empty():
    assert ask_ai.serialize_context(None) == '(no context provided)'
    assert ask_ai.serialize_context({}) == '(no context provided)'


def test_serialize_context_renders_scalars_and_lists():
    text = ask_ai.serialize_context({'total': 5, 'types': ['Address', 'Host']})
    assert 'total: 5' in text
    assert 'types: Address, Host' in text


def test_serialize_context_caps_long_lists_and_says_so():
    text = ask_ai.serialize_context({'items': [f'v{i}' for i in range(ask_ai.MAX_ITEMS + 25)]})
    assert '+25 more' in text


def test_build_user_message_is_bounded():
    message = ask_ai.build_user_message('q', {'blob': 'y' * 100_000})
    assert len(message) <= ask_ai.MAX_CONTEXT_CHARS + len(ask_ai.TRUNCATION_MARKER)


def test_build_user_message_includes_the_question():
    assert 'Question: why' in ask_ai.build_user_message('why', {'a': 1})


# ── endpoint ──────────────────────────────────────────────────────────────


class _Body:
    """Stand-in for the validated request body."""

    def __init__(self, question=None, context=None):
        self.question = question
        self.context = context


def _endpoint(bedrock_enabled=True, invoke=None):
    bedrock = SimpleNamespace(
        # The real thing is a cached_property shared across requests; the
        # endpoint must copy it before mutating.
        anthropic_config={'anthropic_version': 'bedrock-2023-05-31', 'max_tokens': 2048},
        invoke_model=invoke,
    )
    return make_endpoint(
        ask_ai.ExampleAskAi,
        app_config=SimpleNamespace(bedrock=bedrock_enabled),
        bedrock=bedrock,
    )


def _post(ep, **kwargs):
    resp = FakeResponse()
    ep._summarize(resp, _Body(**kwargs))
    return resp.media


def test_gated_off_returns_a_soft_error():
    body = _post(_endpoint(bedrock_enabled=False), question='hi')
    assert body['summary'] is None
    assert 'not available' in body['error']


def test_successful_invocation_returns_the_summary():
    def invoke(body):
        payload = json.loads(body)
        assert payload['system'] == ask_ai.SYSTEM_PROMPT
        assert payload['messages'][0]['role'] == 'user'
        return {'body': SimpleNamespace(read=lambda: json.dumps({'content': [{'text': '# ok'}]}))}

    body = _post(_endpoint(invoke=invoke), question='q', context={'a': 1})
    assert body['summary'] == '# ok'
    assert body['error'] is None


def test_invoke_failure_soft_errors():
    def invoke(body):  # noqa: ARG001 - endpoint passes body= by keyword
        raise RuntimeError('bedrock exploded')

    body = _post(_endpoint(invoke=invoke), question='q')
    assert body['summary'] is None
    assert 'bedrock exploded' in body['error']


def test_shared_config_is_not_mutated():
    """Setting messages/system in place would leak one request into the next."""
    captured = {}

    def invoke(body):
        captured['sent'] = json.loads(body)
        return {'body': SimpleNamespace(read=lambda: json.dumps({'content': [{'text': 'x'}]}))}

    ep = _endpoint(invoke=invoke)
    _post(ep, question='q')
    assert 'system' not in ep.bedrock.anthropic_config
    assert 'messages' not in ep.bedrock.anthropic_config
    assert 'system' in captured['sent']
