import mastodon as mstdn
from sys import exit, stderr
from time import sleep

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

    def _crawl_updates(
        self, initial_wait: int = 60, min_id: str = None,
        return_on_up_to_date=False
    ) -> str:
        """Poll public timeline of a Mastodon instance via an API call
        to get new statuses.
        Return the id of the latest status.
        """
        wait_time = initial_wait
        while True:
            statuses = None
            try:
                statuses = self.mastodon.timeline(
                    timeline='public', limit=40, min_id=min_id)
            except Exception as e:
                print(e, file=stderr)
            # Sometimes we get 'Connection reset by peer' and don't have
            # any new statuses.
            if (statuses):
                min_id = statuses[0].get(self.save.ID)
                for status in statuses:
                    self.save.write_status(status, self.instance,
                        'api/v1/timelines/public')
                # Adjust wait time between requests to actual activity
                if (len(statuses) == 40):
                    if(wait_time > 1):
                        wait_time *= 0.9
                elif (return_on_up_to_date):
                    return min_id
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
            else:
                sleep(10)

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
        last_seen_id = self.save.get_last_id(self.instance)
        self._crawl_updates(min_id=last_seen_id)
