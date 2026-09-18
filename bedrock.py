"""Bedrock Module.

Thin wrapper around the AWS Bedrock runtime, injected onto endpoints as
``self.bedrock`` by ``InjectableMiddleware`` (see ``app.py:App.middleware``).

Availability is decided once at boot by ``app.py:App._check_bedrock_api``,
which sets ``app_config.bedrock`` — the UI reads that flag from
``/api/tc/app-config`` to hide AI surfaces. Endpoints must still fail soft
(200 + an ``error`` string) when an invoke fails at request time.
"""

# standard library
from collections.abc import Callable
from functools import partial

# third-party
import boto3
from botocore.client import Config
from tcex.pleb.cached_property import cached_property

# Cross-region inference profile id. Change with the region below.
MODEL_ID = 'us.anthropic.claude-sonnet-4-6'
REGION_NAME = 'us-east-1'


class Bedrock:
    """Bedrock Module"""

    def __init__(self):
        """Initialize instance properties."""
        self.connection_timeout = 120
        self.read_timeout = 120
        self.region_name = REGION_NAME
        self.retries = {
            'max_attempts': 0,
            'mode': 'standard',
        }
        self.service_name = 'bedrock-runtime'

    @cached_property
    def anthropic_config(self) -> dict:
        """Return the base Anthropic messages-API request body.

        GOTCHA: this is a ``cached_property`` — ONE dict shared by every
        request. Always ``dict(...)``-copy it before setting ``messages`` or
        ``system``, or concurrent requests will clobber each other.
        """
        return {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 2048,
            'temperature': 0,
            'top_k': 0,
        }

    @property
    def bedrock_config(self):
        """Return the botocore client config."""
        return Config(
            connect_timeout=self.connection_timeout,
            read_timeout=self.read_timeout,
            retries=self.retries,
        )

    @property
    def boto3_client(self):
        """Return the bedrock-runtime client."""
        return self.boto3_session.client(service_name=self.service_name, config=self.bedrock_config)

    @cached_property
    def boto3_session(self):
        """Return the boto3 session."""
        return boto3.Session(region_name=self.region_name)

    @cached_property
    def invoke_model(self) -> Callable[..., dict]:
        """Invoke the Bedrock Model."""
        return partial(
            self.boto3_client.invoke_model,
            accept='application/json',
            contentType='application/json',
            modelId=MODEL_ID,
        )
