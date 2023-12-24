from mastodon import (
    Mastodon, MastodonNetworkError, MastodonVersionError, StreamListener
)
from sys import exit, stderr
from threading import Thread
from time import sleep
from typing import TextIO

from fediverse_analysis.crawl.crawl import Crawler
from fediverse_analysis.crawl.save import _Save


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
        self.retries = 0
        self.save = _Save()
        self.timer = Thread(target=self._print_timer, daemon=True)
        self.crawler = Crawler(self.instance, self.save)

    def _intermediate_crawl(self) -> None:
        if (self.last_seen_id):
            print('Fetching missed statuses.', flush=True)
            self.last_seen_id = self.crawler._crawl_updates(
                initial_wait=10,
                min_id=self.last_seen_id,
                return_on_up_to_date=True
            )
        else:
            print('Could not find any previous statuses.', flush=True)

    def _print_timer(self) -> None:
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

    def stream_updates_to_es(
        self,
        host: str,
        password: str = '',
        port: int = 9200,
        username: str = ''
    ) -> None:
        """Connect to the streaming API of the Mastodon instance and receive
        new public statuses. Write the statuses to Elasticsearch.
        Use crawling of the API via GET requests as a fallback.
        """
        self.save.init_es_connection(host, password, port, username)
        stream_listener = _UpdateStreamListener(self.instance, self.save, self)
        self.last_seen_id = self.save.get_last_id(self.instance)
        self._intermediate_crawl()
        self.timer.start()
        while True:
            try:
                self.did_stream_work = False
                print('Streaming statuses. Last streamed status created at:',
                    flush=True)
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
                self.retries = 0
            else:
                self.retries += 1
                # Too many consecutive failed attempts. Give up streaming.
                if (self.retries >= self.max_retries):
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
        self.counter = 0
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
