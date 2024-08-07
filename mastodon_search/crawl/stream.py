from mastodon import (
    Mastodon, MastodonNetworkError, MastodonVersionError, StreamListener
)
from sys import stderr
from threading import Thread
from time import sleep

from mastodon_search.crawl.crawl import Crawler
from mastodon_search.crawl.save import _Save


class Streamer:
    """Leverage Mastodon.py to retrieve data from a Mastodon instance via the
    streaming API.
    """
    def __init__(self, instance: str) -> None:
        """Arguments:
        instance -- an instance's base URI, e. g.: 'mastodon.social'.
        """
        # This indicates if the stream ran in *this* cycle.
        self.did_stream_work = False
        self.instance = instance
        self.is_running = True
        self.last_seen_created_at = None
        self.last_seen_id = None
        self.mastodon = Mastodon(api_base_url=self.instance)
        # Give up streaming after this number of consecutive failed attempts.
        self.max_retries = 5
        self.save = _Save()
        self.timer = Thread(target=self._print_timer, daemon=True)
        self.crawler = Crawler(self.instance, self.save)

    def _intermediate_crawl(self) -> None:
        """Fetch statuses, starting from the last seen one, until we are up
        to date.
        """
        self.is_running = False
        if (self.last_seen_id):
            print('Fetching missed statuses.', flush=True)
        else:
            print(
                'Could not find any previous statuses. Crawling some.',
                flush=True
            )
        self.last_seen_id = self.crawler._crawl_updates(
            initial_wait=10,
            min_id=self.last_seen_id,
            return_on_up_to_date=True
        )
        self.is_running = True
        if not self.timer.is_alive():
            self.timer = Thread(target=self._print_timer, daemon=True)
            self.timer.start()

    def _print_timer(self) -> None:
        """Print `created_at` value of the last crawled status periodically.
        Run as thread to not block anything else.
        """
        sleep(60)
        while True:
            if (not self.is_running):
                return
            if (self.last_seen_created_at):
                print(
                    self.last_seen_created_at.isoformat(timespec='seconds'),
                    flush=True
                )
            else:
                print('None', flush=True)
            sleep(600)

    def stream_updates_to_elastic(
        self,
        host: str,
        password: str,
        port: int,
        username: str,
    ) -> None:
        """Connect to the streaming API of the Mastodon instance and receive
        new public statuses. Write the statuses to Elasticsearch.
        Use crawling of the API via GET requests as a fallback.

        Arguments:
        see mastodon_search.cli: stream_to_es
        """
        self.save.init_elastic_connection(host, password, port, username)
        stream_listener = _UpdateStreamListener(self.instance, self.save, self)
        self.last_seen_id = self.save.get_last_id(self.instance)
        self._intermediate_crawl()
        retries = 0
        while True:
            self.did_stream_work = False
            print('Streaming statuses. Last streamed status created at:',
                flush=True)
            try:
                self.mastodon.stream_public(stream_listener)
            except MastodonVersionError:
                print(f'{self.instance} does not support streaming '
                    +'or is unreachable.', file=stderr)
                break
            except MastodonNetworkError as e:
                # Server closes connection, we reconnect.
                # Sadly, there are multiple causes that trigger this error.
                if (str(e) == 'Server ceased communication.'):
                    print(e)
                else:
                    print(
                        'During streaming an error occured:', e,
                        file=stderr, flush=True
                    )
                    break
            except Exception as e:
                print(
                    'During streaming an error occured:', e,
                    file=stderr, flush=True
                )
                break
            sleep(3)
            if (self.did_stream_work):
                retries = 0
            else:
                retries += 1
                # Too many consecutive failed attempts. Give up streaming.
                if (retries >= self.max_retries):
                    break
            self._intermediate_crawl()
        print('Falling back to crawling.', file=stderr, flush=True)
        self.is_running = False
        self.crawler._crawl_updates(min_id=self.last_seen_id)


class _UpdateStreamListener(StreamListener):
    """Provide own methods for when something happens with a connected
    stream.
    """
    def __init__(self, instance: str, save: _Save, streamer: Streamer) -> None:
        self.instance = instance
        self.save = save
        self.streamer = streamer

    def on_update(self, status) -> None:
        self.streamer.last_seen_id = status['id']
        self.streamer.last_seen_created_at = status['created_at']
        self.save.write_status(status, self.instance,
            'api/v1/streaming/public')
        if (not self.streamer.did_stream_work):
            self.streamer.did_stream_work = True
