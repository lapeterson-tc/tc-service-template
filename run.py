"""Run App"""

# standard library
import sys
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    # third-party
    from tcex import TcEx  # must be imported later, but also needed typing hints

    # first-party
    from app import App  # must be imported later, but also needed typing hints


class Run:
    """Run App"""

    @cached_property
    def app(self) -> 'App':
        """Return a properly configured App instance."""
        # initialize the TcEx
        tcex = self.tcex

        # first-party
        from app import App  # pylint: disable=import-outside-toplevel

        return App(tcex)

    def exit(self, code: int, msg: str) -> NoReturn:
        """Exit the App."""
        self.tcex.exit.exit(code, msg)  # pylint: disable=no-member

    @cached_property
    def tcex(self) -> 'TcEx':
        """Return a properly configured TcEx instance."""
        # third-party
        from tcex import TcEx  # pylint: disable=import-outside-toplevel

        return TcEx()

    def launch(self):
        """Launch the App"""
        try:
            # perform prep/setup operations
            self.app.setup(**{})  # noqa: PIE804

            # configure the event callback
            self.tcex.app.service.api_event_callback = self.app.api_event_callback  # type: ignore

            # listen on channel/topic
            self.tcex.app.service.listen()

            # start heartbeat threads
            self.tcex.app.service.heartbeat()

            # inform TC that micro-service is Ready
            self.tcex.app.service.ready = True

            # loop until exit
            self.tcex.log.info('feature=app, event=loop-forever')
            if hasattr(self.app, 'loop_forever'):
                self.app.loop_forever()  # pylint: disable=no-member
            else:
                while self.tcex.app.service.loop_forever(sleep=1):
                    pass

            # perform cleanup/teardown operations
            self.app.teardown(**{})  # noqa: PIE804
        except Exception:
            ex_msg = 'Generic Error.  See logs for more details.'
            self.tcex.log.exception(ex_msg)
            self.exit(1, ex_msg)

    def setup(self):
        """Handle the deps directory."""
        # configure the deps directory before importing any third-party packages
        # for TcEx 4 and above, all additional packages are in the "deps" directory
        deps_dir = Path.cwd() / 'deps'
        if not deps_dir.is_dir():
            sys.exit(
                f'Running an App requires a "deps" directory. Could not find the {deps_dir} '
                'directory.\n\nTry running "tcex deps" to install dependencies.'
            )
        sys.path.insert(0, str(deps_dir))  # insert deps directory at the front of the path

    def teardown(self):
        """Teardown the App."""
        # explicitly call the exit method
        self.exit(0, msg=self.app.exit_message)


if __name__ == '__main__':
    # Launch the App
    run = Run()
    run.setup()
    run.launch()
    run.teardown()
