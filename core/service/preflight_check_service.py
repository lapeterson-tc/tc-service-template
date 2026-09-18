"""ThreatConnect Preflight Check Service"""


class PreflightCheckService:
    """Service for performing preflight checks."""

    def __init__(self, tcex, log):
        """Initialize class properties."""
        self.tcex = tcex
        self.log = log
        self.preflight_checks = self.default_preflight_checks

    @property
    def default_preflight_checks(self):
        """Return the default preflight checks."""
        return [self._check_filesystem]

    def register_preflight_check(self, check):
        """Register a preflight check."""
        self.preflight_checks.append(check)

    def perform_checks(self):
        """Perform all preflight checks."""
        for preflight_check in self.preflight_checks:
            preflight_check()

    def _check_filesystem(self):
        """Check the filesystem for required conditions."""
        preflight_check_file = self.tcex.inputs.model.tc_out_path / 'preflight'
        try:
            preflight_check_file.write_text('preflight check')
            self.log.info(
                f'action=check_filesystem, '
                f'message=Preflight check for filesystem passed, '
                f'file={preflight_check_file}'
            )
        except Exception as ex:
            self.log.exception(
                'action=check_filesystem, message=Preflight check for filesystem failed, '
            )
            ex_msg = 'Preflight check for filesystem failed.'
            raise RuntimeError(ex_msg) from ex

    # def _check_tc_api(self):
    #     """Check the ThreatConnect API for required conditions."""
    #     try:
    #         owners = self.tcex.api.tc.v3.security.owners()
    #         owners = [o.model.name for o in owners]
    #         self.log.info(
    #             f'action=check_tc_api, message=Preflight check for TC API passed, owners={owners}'
    #         )
    #     except Exception as ex:
    #         self.log.exception('action=check_tc_api, message=Preflight check for TC API failed.')
    #         ex_msg = 'Preflight check for TC API failed.'
    #         raise RuntimeError(ex_msg) from ex
