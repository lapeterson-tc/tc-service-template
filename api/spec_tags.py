"""SpecTree OpenAPI Tag Specification

One Tag per feature area; pass it to ``@spec.validate(..., tags=[...])`` so the
Swagger UI at ``apidoc/swagger`` groups endpoints sensibly. Add a tag here when
you add a feature package under ``api/endpoint/``.
"""

# third-party
from spectree import Tag

tag_util = Tag(
    name='[Internal] Util',
    description='Endpoints related to Utility features',
)

tag_storage = Tag(
    name='[Internal] Storage',
    description='Endpoints related to backup/restore of app storage',
)

tag_example = Tag(
    name='[Internal] Example',
    description='Endpoints for the example dashboard feature (replace with your own)',
)
