"""App Inputs"""

# pyright: reportGeneralTypeIssues=false

# third-party
from tcex.input.input import Input
from tcex.input.model.app_api_service_model import AppApiServiceModel


class AppBaseModel(AppApiServiceModel):
    """Base model for the App containing any common inputs.

    Declare one field per service-config parameter defined in ``app_spec.yml``
    (which generates ``install.json``). Inputs are injected by ThreatConnect
    ONLY at service start — a long-running service never sees an updated
    value, so anything time-sensitive (a token with an expiry) must be
    re-checked before use rather than trusted.

    Make every field Optional with a default so the app still boots on an
    instance where the parameter was left blank; validation failures here exit
    the app with status 1 before it ever serves a request.

    Example — a plain string and an encrypted secret::

        # third-party
        from tcex.input.field_type.sensitive import Sensitive

        class AppBaseModel(AppApiServiceModel):
            example_api_url: str | None = None
            example_api_key: Sensitive | None = None

    Read a Sensitive value with ``.value``; see ``app.py`` for how inputs
    become endpoint-visible config.
    """


class AppInputs:
    """App Inputs"""

    def __init__(self, inputs: Input):
        """Initialize instance properties."""
        self.inputs = inputs

    def update_inputs(self):
        """Add custom App model to inputs.

        Input will be validate when the model is added an any exceptions will
        cause the App to exit with a status code of 1.
        """
        self.inputs.add_model(AppBaseModel)
