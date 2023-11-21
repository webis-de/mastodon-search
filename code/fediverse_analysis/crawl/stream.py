import mastodon as mstdn
from sys import exit
from typing import TextIO

from fediverse_analysis.crawl.save import _Save


class Streamer:
    """Leverage Mastodon.py to retrieve data from a Mastodon instance via the
    streaming API.
    """
    def __init__(self, instance: str) -> None:
        """Arguments:
        instance -- an instance's base URI, e. g.: 'pawoo.net'.
        """
        self.mastodon = mstdn.Mastodon(api_base_url=instance)
        self.save = _Save()
        self.stream_listener = _UpdateStreamListener(instance, self.save)

    def _stream_local_updates(self) -> None:
        """Connect to the streaming API of the Mastodon instance and receive
        new public, local statuses.
        """
        while True:
            try:
                self.mastodon.stream_public(self.stream_listener, local=True)
            except mstdn.MastodonVersionError:
                print(f'{self.instance} does not support streaming.')
                exit(1)
            except mstdn.MastodonNetworkError as e:
                # Server closes connection, we reconnect.
                # Sadly, there are multiple causes that trigger this error.
                if (str(e) == 'Server ceased communication.'):
                    pass
                else:
                    print(e)
                    exit(1)

    def stream_updates_to_es(
        self,
        host: str,
        index: str,
        password: str = '',
        port: int = 9200,
        username: str = ''
    ) -> None:
        """Connect to the streaming API of the Mastodon instance and receive
        new public statuses. Write the statuses to Elasticsearch.
        """
        self.save.init_es_connection(host, index, password, port, username)
        self._stream_local_updates()

    def stream_updates_to_file(self, file: TextIO) -> None:
        """Connect to the streaming API of the Mastodon instance and receive
        new public statuses. Write the statuses as JSON Lines to a file.
        """
        self.save.output_file = file
        self._stream_local_updates()


class _UpdateStreamListener(mstdn.StreamListener):
    """Provide own methods for when something happens with a connected
    stream.
    """
    def __init__(self, instance: str, save: _Save) -> None:
        self.instance = instance
        self.save = save

    def on_update(self, status) -> None:
        self.save.write_status(status, self.instance)
