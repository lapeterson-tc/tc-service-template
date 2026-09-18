"""API Endpoint /api/example/ask-ai.

EXAMPLE FEATURE — delete or adapt when you build your own.

One-shot AI summarization over an arbitrary JSON context supplied by the UI.
This is the reference pattern for any AI-assisted surface in the template:

- The **context builders are module-level pure functions**, so the interesting
  logic (what gets sent to the model, and how it is capped) is unit-testable
  without tcex or boto3.
- The handler is **gated on ``app_config.bedrock``**, which the boot preflight
  sets. The UI reads that same flag from ``/api/tc/app-config`` and hides the
  AI surface entirely when it is false.
- It **never 500s**: a gated-off or failed invocation is an HTTP 200 with
  ``summary: null`` and an ``error`` string.
- The shared ``bedrock.anthropic_config`` dict is **copied before mutation** —
  it is a ``cached_property`` shared by every request, so setting
  ``messages``/``system`` in place leaks one request's prompt into the next.

Sending data to Bedrock sends it outside ThreatConnect. Cap what you send, and
say so in the UI.
"""

# standard library
import json

# third-party
from spectree import Response

# first-party
from api.endpoint.endpoint_base import EndpointBase
from api.spec_tags import tag_example
from bedrock import MODEL_ID
from core.api.falcon_request import FalconRequest
from core.api.falcon_response import FalconResponse
from core.api.spec import spec
from core.api.validation.models.query_param_filter_model import QueryParamFilterModel
from core.model.model_base import ModelBase

# Context caps. A caller can always hand over more than a model should see;
# truncate loudly rather than failing the request.
MAX_ITEMS = 100
MAX_VALUE_CHARS = 500
MAX_CONTEXT_CHARS = 20_000
TRUNCATION_MARKER = '…[truncated]'

SYSTEM_PROMPT = (
    'You are an analyst assistant embedded in a ThreatConnect application. '
    'Given a structured context, write a concise markdown summary covering: '
    'what the data shows, anything notable or anomalous, and what the analyst '
    'should look at next. Rules: base every statement ONLY on the provided '
    'context — never invent facts, figures, or attributions. If the context is '
    'sparse, say so briefly instead of padding. Keep it under ~250 words. Use '
    'markdown lists sparingly; no preamble.'
)


def truncate(value: str, limit: int = MAX_VALUE_CHARS) -> str:
    """Return ``value`` cut to ``limit`` characters with a visible marker."""
    value = value or ''
    if len(value) <= limit:
        return value
    return value[:limit] + TRUNCATION_MARKER


def serialize_context(context: dict | None) -> str:
    """Render a JSON-ish context blob as bounded ``key: value`` text.

    Pure, so the caps are directly testable. Lists are flattened to at most
    ``MAX_ITEMS`` entries and every scalar is truncated; nested structures are
    JSON-dumped and then truncated the same way.
    """
    if not isinstance(context, dict) or not context:
        return '(no context provided)'

    lines: list[str] = []
    for key, value in list(context.items())[:MAX_ITEMS]:
        if isinstance(value, (str, int, float, bool)) or value is None:
            lines.append(f'{key}: {truncate(str(value))}')
        elif isinstance(value, list):
            shown = value[:MAX_ITEMS]
            rendered = ', '.join(
                truncate(v if isinstance(v, str) else json.dumps(v, default=str)) for v in shown
            )
            suffix = f' (+{len(value) - len(shown)} more)' if len(value) > len(shown) else ''
            lines.append(f'{key}: {truncate(rendered)}{suffix}')
        else:
            lines.append(f'{key}: {truncate(json.dumps(value, default=str))}')
    return '\n'.join(lines)


def build_user_message(question: str | None, context: dict | None) -> str:
    """Build the single user message sent to the model, capped end-to-end."""
    parts = []
    if question and question.strip():
        parts.append(f'Question: {question.strip()}')
    parts.append('Context:')
    parts.append(serialize_context(context))
    message = '\n'.join(parts)
    if len(message) > MAX_CONTEXT_CHARS:
        message = message[:MAX_CONTEXT_CHARS] + TRUNCATION_MARKER
    return message


class QueryParamPost(QueryParamFilterModel):
    """Query parameters for POST /api/example/ask-ai."""


class RequestBodyModel(ModelBase):
    """Request body model."""

    question: str | None = None
    context: dict | None = None


class ResponseBodyModel(ModelBase):
    """Response body model."""

    summary: str | None = None
    model: str | None = None
    error: str | None = None


class ExampleAskAi(EndpointBase):
    """API Endpoint /api/example/ask-ai."""

    @spec.validate(
        query=QueryParamPost,
        json=RequestBodyModel,
        resp=Response(HTTP_200=ResponseBodyModel),
        skip_validation=True,
        tags=[tag_example],
    )
    def on_post(
        self,
        _req: FalconRequest,
        resp: FalconResponse,
        body: RequestBodyModel,
        query_params: QueryParamPost,  # noqa: ARG002 - spectree contract
    ):
        """Return an AI-generated markdown summary of the supplied context."""
        self._summarize(resp, body)

    def _summarize(self, resp: FalconResponse, body: RequestBodyModel):
        """Undecorated core (spectree-free so endpoint tests can call it directly)."""
        if not getattr(self.app_config, 'bedrock', False):
            resp.media = {
                'summary': None,
                'model': None,
                'error': 'AI summarization is not available (Bedrock preflight failed).',
            }
            return

        user_message = build_user_message(body.question, body.context)

        # Copy the shared cached config — mutating it in place would leak this
        # request's messages/system into every later invocation.
        model_body = dict(self.bedrock.anthropic_config)
        model_body['system'] = SYSTEM_PROMPT
        model_body['messages'] = [
            {'role': 'user', 'content': [{'text': user_message, 'type': 'text'}]}
        ]

        try:
            response = self.bedrock.invoke_model(body=json.dumps(model_body))
            response_data = json.loads(response['body'].read())
            summary = response_data['content'][0]['text']
            resp.media = {'summary': summary, 'model': MODEL_ID, 'error': None}
        except Exception as ex:  # noqa: BLE001 - never-500
            self.log.warning(f'action=ask_ai, message=Bedrock invocation failed: {ex}')
            resp.media = {'summary': None, 'model': None, 'error': str(ex)}
