from mastodon import Mastodon
from requests import Session
from requests_ratelimiter import LimiterAdapter
from sys import exit
from threading import Thread
from time import sleep
from urllib3 import Retry

from mastodon_search.crawl.save import _Save
from mastodon_search.globals import USER_AGENT


class Crawler:
    """Leverage Mastodon.py to retrieve data from a Mastodon instance via API
    GET requests.
    """
    def __init__(self, instance: str, save: _Save) -> None:
        """Arguments:
        instance -- an instance's base URI, e. g.: 'pawoo.net'.
        save -- an instance of this module's _Save class
        """
        self.instance = instance
        self.is_running = False
        self.last_seen_created_at = None
        self.mastodon = Mastodon(
            api_base_url=self.instance, session=self._session()
        )
        self.save = save
        self.timer = Thread(target=self._print_timer, daemon=True)

    def _crawl_updates(
        self, initial_wait: int = 60, max_wait: int = 3600,
        min_id: str = None, return_on_up_to_date: bool = False
    ) -> str:
        """Poll public timeline of a Mastodon instance continuously via an API
        call to get new statuses. Automatically adapt the wait time between
        two requests to go easy on smaller instances.

        Arguments:
        initial_wait -- wait time in seconds between two requests when starting
        max_wait -- maximum wait time in seconds between two requests
        min_id -- set API parameter to start with, see
            https://docs.joinmastodon.org/methods/timelines/#query-parameters
        return_on_up_to_date -- stop and return the id of the latest status
            when there are no newer statuses
        """
        wait_time = initial_wait
        self.is_running = True
        if (not self.timer.is_alive()):
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
            elif (wait_time >= max_wait):
                wait_time = max_wait
            # Go up quick on small instances
            elif (len(statuses) == 0):
                wait_time *= 2
            elif (len(statuses) <= 3):
                wait_time *= 1.5
            elif (len(statuses) <= 10):
                wait_time *= 1.1
            sleep(wait_time)

    def _session(self) -> Session:
        """Return a session from the requests module."""
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
                400, 403, 404,
                500, 502, 503, 504,
                520, 521, 522, 523, 524, 525, 526, 527, 530
            ],
            respect_retry_after_header=True
        )
        adapter = LimiterAdapter(
            burst=1,
            max_retries=retries,
            per_second=1
        )
        session = Session()
        session.headers['User-Agent'] = USER_AGENT
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

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
