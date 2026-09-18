"""Registry of persisted data types.

Every ``data_type`` this app writes through ``safe_datastore`` must be listed
here. The list drives the backup/restore endpoints
(``api/endpoint/storage/transfer.py``) — a type that is missing from it is
silently absent from every export, so a restore produces an app that looks
fine and has quietly lost that data.

Naming: lowercase, hyphenated, and stable forever. The name becomes a
directory under ``{tc_out_path}/app-data/{org_key}/``, so renaming one
orphans every existing record.
"""

DATA_TYPES: tuple[str, ...] = ('example-preferences',)


def redact_record(data_type: str, record: dict) -> dict:
    """Return ``record`` with secrets stripped, for a redacted export.

    Called once per record by ``GET /api/storage/export?redactSecrets=true``.
    The default is identity — implement a branch here for any data type that
    stores a credential.

    Think carefully before making redaction the default. A secret that is
    already readable through the app's own GET endpoint gains no
    confidentiality by being dropped from a backup, but a *restored* record
    with a silently missing credential fails every call it makes with nothing
    pointing back at the backup. A visibly sensitive backup file beats a
    silently broken integration — which is why ``redactSecrets`` is opt-in.

    Example::

        if data_type == 'my-sources':
            return {
                **record,
                'authSecret': None,
                'hasAuth': bool(record.get('authSecret')),
            }
        return record
    """
    return record
