"""Define custom settings for app."""

# first-party
from core.model.model_base import ModelBase


class SettingModel(ModelBase):
    """Custom Setting Model"""

    # Define custom settings for the App
    sample_types: set[str]
