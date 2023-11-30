import mastodon as mstdn
from json import loads
from sys import exit
from time import sleep
from typing import TextIO

from fediverse_analysis.crawl.save import _Save


class Crawler:
    """Leverage Mastodon.py to retrieve data from a Mastodon instance via API
    GET requests.
    """
    def __init__(self, instance: str, save: _Save = _Save()) -> None:
        """Arguments:
        instance -- an instance's base URI, e. g.: 'pawoo.net'.
        """
        self.instance = instance
        self.mastodon = mstdn.Mastodon(api_base_url=self.instance)
        self.save = save
        self.max_wait = 3600

    def _crawl_updates(self, min_id: int = None) -> None:
        """Poll public timeline of a Mastodon instance via an API call
        to get new statuses.
        """
        wait_time = 60
        while True:
            try:
                statuses = self.mastodon.timeline(
                    timeline='public', limit=40, min_id=min_id)
            except Exception as e:
                print(e)
                break
            if (statuses):
                min_id = statuses[0].get(self.save.ID)
                for status in statuses:
                    self.save.write_status(status, self.instance,
                        'api/v1/timelines/public')
            # Adjust wait time between requests to actual activity
            if (len(statuses) == 40):
                if(wait_time > 3):
                    wait_time *= 0.9
            # Never go above a set maximum
            elif (wait_time >= self.max_wait):
                wait_time = self.max_wait
            # Go up quick on small instances
            elif (len(statuses) == 0):
                wait_time *= 2
            elif (len(statuses) <= 3):
                wait_time *= 1.5
            elif (len(statuses) <= 10):
                wait_time *= 1.1
            sleep(wait_time)

    def crawl_to_es(
        self,
        host: str,
        password: str = '',
        username: str = '',
        max_wait_time: int = None,
        port: int = 9200
    ) -> None:
        """Use `_crawl_updates` to get new Mastodon statuses and write
        them to an Elasticsearch instance.
        """
        if (max_wait_time):
            self.wait_time = max_wait_time
        self.save.init_es_connection(host, password, port, username)
        self._crawl_updates()

    def crawl_to_file(self, filename: str, max_wait_time: int = None) -> None:
        """Use `_crawl_updates` to get new Mastodon statuses and write
        them to a file.
        """
        last_id = None
        if (max_wait_time):
            self.wait_time = max_wait_time
        try:
            with open(filename, 'rb') as f:
                try:
                    # While seeking is slower on small files (still not very
                    # expensive absolutely), it's way faster on large files.
                    f.seek(-2, 2)
                    # Seek to first line with content
                    while (f.read(1) != b'}'):
                        f.seek(-2, 1)
                    f.seek(-1024, 1)
                    # Seek to start of line
                    while (f.read(1) != b'\n'):
                        f.seek(-2, 1)
                # In case of an empty/whitespace only file.
                except OSError:
                    f.seek(0)
                else:
                    last_id = loads(f.readline().decode())[_Save.ID]
        except FileNotFoundError:
            pass
        with open(filename, 'a') as f:
            self.save.output_file = f
            self._crawl_updates(last_id)
