import mastodon as mstdn
from json import dumps
from sys import exit
from typing import TextIO


class Streamer:
    """Leverage Mastodon.py to retrieve data from a Mastodon instance."""
    _CREATED_AT = 'created_at'
    _ACCOUNT = 'account'
    _LAST_STATUS_AT = 'last_status_at'

    def __init__(self, instance: str) -> None:
        """Arguments:
        instance -- an instance's base URI, e. g.: 'pawoo.net'.
        """
        self.instance = instance
        self.output_file = None

        self.mastodon = mstdn.Mastodon(api_base_url=self.instance)

    def _write_status(self, status: dict) -> None:
        """Write an ActivityPub status to the output file."""
        # Replace datetime objects with strings.
        status[Streamer._CREATED_AT] = str(status[Streamer._CREATED_AT])
        for key in (Streamer._CREATED_AT, Streamer._LAST_STATUS_AT):
            status[Streamer._ACCOUNT][key] = str(
                status[Streamer._ACCOUNT][key])
        self.output_file.write(dumps(status, ensure_ascii=False) + '\n')

    def stream_local_updates(self, file: TextIO) -> None:
        """Connect to the streaming API of the Mastodon instance and receive
        new public, local statuses.
        """
        self.output_file = file
        try:
            self.mastodon.stream_public(
                _UpdateStreamListener(self), local=True)
        except mstdn.MastodonVersionError:
            print(f'{self.instance} does not support streaming.')
            exit(1)
        except mstdn.MastodonNetworkError as e:
            print(e)
            exit(1)
        exit(0)


class _UpdateStreamListener(mstdn.StreamListener):
    """Provide own methods for when something happens with a connected
    stream.
    """
    def __init__(self, crawler: Streamer) -> None:
        self.crawler = crawler

    def on_update(self, status) -> None:
        self.crawler._write_status(status)
