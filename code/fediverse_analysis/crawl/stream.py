import mastodon as mstdn
from sys import exit
from typing import TextIO

from fediverse_analysis.crawl.crawl import Crawler
from fediverse_analysis.crawl.save import _Save


class Streamer:
    """Leverage Mastodon.py to retrieve data from a Mastodon instance via the
    streaming API.
    """
    def __init__(self, instance: str) -> None:
        """Arguments:
        instance -- an instance's base URI, e. g.: 'pawoo.net'.
        """
        self.instance = instance
        self.last_seen_id = None
        self.mastodon = mstdn.Mastodon(api_base_url=self.instance)
        self.save = _Save()

    def _stream_local_updates(self) -> None:
        """Connect to the streaming API of the Mastodon instance and receive
        new public, local statuses. Use crawling of the API via GET requests
        as a fallback.
        """
        stream_listener = _UpdateStreamListener(self.instance, self.save, self)
        while True:
            try:
                self.mastodon.stream_public(stream_listener, local=True)
            except mstdn.MastodonVersionError:
                print(f'{self.instance} does not support streaming.')
                break
            except mstdn.MastodonNetworkError as e:
                # Server closes connection, we reconnect.
                # Sadly, there are multiple causes that trigger this error.
                if (str(e) == 'Server ceased communication.'):
                    pass
                else:
                    print(e)
                    break
            except Exception:
                break
        print('Falling back to crawling.')
        crawler = Crawler(self.instance, self.save)
        crawler._crawl_local_updates(self.last_seen_id)

    def stream_updates_to_es(
        self,
        host: str,
        password: str = '',
        port: int = 9200,
        username: str = ''
    ) -> None:
        """Connect to the streaming API of the Mastodon instance and receive
        new public statuses. Write the statuses to Elasticsearch.
        """
        self.save.init_es_connection(host, password, port, username)
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
    def __init__(self, instance: str, save: _Save, streamer: Streamer) -> None:
        self.instance = instance
        self.save = save
        self.streamer = streamer

    def on_update(self, status) -> None:
        self.streamer.last_seen_id = status[_Save.ID]
        self.save.write_status(status, self.instance,
            '/api/v1/streaming/public/local')
