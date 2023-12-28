from mastodon import Mastodon
from requests import Session
from requests_ratelimiter import LimiterAdapter
from sys import exit, stderr
from threading import Thread
from time import sleep
from urllib3 import Retry

from fediverse_analysis.crawl.save import _Save


class Crawler:
    """Leverage Mastodon.py to retrieve data from a Mastodon instance via API
    GET requests.
    """
    NUM_RETRIES = 5

    def __init__(self, instance: str, save: _Save) -> None:
        """Arguments:
        instance -- an instance's base URI, e. g.: 'pawoo.net'.
        """
        self.instance = instance
        self.is_running = False
        self.last_seen_created_at = None
        self.mastodon = Mastodon(
            api_base_url=self.instance, session=self._session()
        )
        self.max_wait = 3600
        self.save = save

    def _crawl_updates(
        self, initial_wait: int = 60, min_id: str = None,
        return_on_up_to_date=False
    ) -> str:
        """Poll public timeline of a Mastodon instance via an API call
        to get new statuses.
        Return the id of the latest status.
        """
        wait_time = initial_wait
        self.is_running = True
        self.timer = Thread(target=self._print_timer, daemon=True)
        self.timer.start()
        print('Last crawled status created at:', flush=True)
        statuses = None
        while True:
            statuses = self.mastodon.timeline(
                timeline='public', limit=40, min_id=min_id)
            if (statuses):
                for status in statuses:
                    self.save.write_status(status, self.instance,
                        'api/v1/timelines/public')
                min_id = statuses[0].get('id')
                self.last_seen_created_at = statuses[0].get('created_at')
            # Adjust wait time between requests to actual activity
            if (len(statuses) == 40):
                if(wait_time > 1):
                    wait_time *= 0.9
            elif (return_on_up_to_date):
                self.is_running = False
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

    def _session(self) -> Session:
        retries = Retry(
            total=28,
            connect=14,
            read=14,
            redirect=14,
            status=14,
            other=14,
            backoff_factor=1,
            backoff_max=2**15,
            status_forcelist=[
                400, 403, 404, 500, 502, 503, 504, 522, 523, 530
            ],
            respect_retry_after_header=True
        )
        adapter = LimiterAdapter(
            burst=1,
            max_retries=retries,
            per_second=1
        )
        session = Session()
        session.headers['User-Agent'] = (
            'Webis Mastodon crawler '
            +'(https://webis.de/, webis@listserv.uni-weimar.de)'
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

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
