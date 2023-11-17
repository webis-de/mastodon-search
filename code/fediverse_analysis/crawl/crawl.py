import mastodon as mstdn
from sys import exit
from time import sleep
from typing import TextIO

from fediverse_analysis.crawl.save import _Save
from fediverse_analysis.util.mastodon import Status


class Crawler:
    """Leverage Mastodon.py to retrieve data from a Mastodon instance via API
    GET requests.
    """
    def __init__(self, instance: str) -> None:
        """Arguments:
        instance -- an instance's base URI, e. g.: 'pawoo.net'.
        """
        self.instance = instance
        self.mastodon = mstdn.Mastodon(api_base_url=self.instance)
        self.save = _Save()
        self.max_wait = 3600

    def _crawl_local_updates(self) -> None:
        """Start receiving new public, local statuses."""
        wait_time = 60
        try:
            # Bootstrapping statuses without min_id argument.
            statuses = self.mastodon.timeline(
                timeline='public', local=True, limit=40)
        except Exception as e:
            print(e)
            exit(1)
        while True:
            if (statuses):
                min_id = statuses[0].get(self.save.ID)
                for status in statuses:
                    self.save.write_status(status, self.instance)
            # Adjust wait time between requests to actual activity
            if (len(statuses) == 40):
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
            try:
                statuses = self.mastodon.timeline(
                    timeline='public', local=True, limit=40, min_id=min_id)
            except Exception as e:
                print(e)
                break

    def crawl_to_es(
        self,
        host: str,
        index: str,
        password: str = '',
        username: str = '',
        max_wait_time: int = None,
        port: int = 9200
    ) -> None:
        """Connect to the streaming API of the Mastodon instance and receive
        new public statuses. Write the statuses to Elasticsearch.
        """
        if (max_wait_time):
            self.wait_time = max_wait_time
        try:
            self.save.init_es_connection(host, index, password, port, username)
        except ValueError as e:
            print(e)
            exit(1)
        except AuthenticationException:
            print('Authentication failed. Wrong username and/or password.')
            exit(1)
        self._crawl_local_updates()
