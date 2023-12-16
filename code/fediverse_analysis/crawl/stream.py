import mastodon as mstdn
from sys import exit, stderr
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
        self.last_seen_id = None
        self.mastodon = mstdn.Mastodon(api_base_url=self.instance)
        # Give up streaming after this number of consecutive failed attempts.
        self.max_retries = 5
        self.retries = 0
        self.save = _Save()
        self.crawler = Crawler(self.instance, self.save)

    def intermediate_crawl(self) -> None:
        if (self.last_seen_id):
            print('Fetching missed statuses.')
            self.last_seen_id = self.crawler._crawl_updates(
                initial_wait=10,
                min_id=self.last_seen_id,
                return_on_up_to_date=True
            )
        else:
            print('Could not find any previous statuses.')

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
        self.intermediate_crawl()
        while True:
            try:
                self.did_stream_work = False
                self.mastodon.stream_public(stream_listener)
            except mstdn.MastodonVersionError:
                print(f'{self.instance} does not support streaming '
                    +'or is unreachable.', file=stderr)
                break
            except mstdn.MastodonNetworkError as e:
                # Server closes connection, we reconnect.
                # Sadly, there are multiple causes that trigger this error.
                if (str(e) == 'Server ceased communication.'):
                    print(f'\n{e}')
                else:
                    if (self.did_stream_work):
                        print()
                    print('During streaming an error occured:', e, file=stderr)
                    break
            except Exception as e:
                if (self.did_stream_work):
                    print()
                print('During streaming an error occured:', e, file=stderr)
                break
            sleep(3)
            if (self.did_stream_work):
                self.retries = 0
            else:
                self.retries += 1
                # Too many consecutive failed attempts. Give up streaming.
                if (self.retries >= self.max_retries):
                    break
            self.intermediate_crawl()
        print('Falling back to crawling.', file=stderr)
        self.crawler._crawl_updates(min_id=self.last_seen_id)


class _UpdateStreamListener(mstdn.StreamListener):
    """Provide own methods for when something happens with a connected
    stream.
    """
    def __init__(self, instance: str, save: _Save, streamer: Streamer) -> None:
        self.counter = 0
        self.instance = instance
        self.save = save
        self.streamer = streamer

    def on_update(self, status) -> None:
        self.streamer.last_seen_id = status[_Save.ID]
        self.save.write_status(status, self.instance,
            'api/v1/streaming/public')
        self.counter += 1
        if (not self.streamer.did_stream_work):
            print('Started streaming successfully. Status count:')
            print(self.counter, end='')
            self.streamer.did_stream_work = True
        else:
            print('\r', self.counter, end='', sep='')

