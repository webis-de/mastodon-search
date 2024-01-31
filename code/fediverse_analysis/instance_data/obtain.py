from datetime import datetime, UTC
from json import dumps, JSONDecodeError, load, loads
from mastodon import (
        Mastodon, MastodonAPIError,
        MastodonInternalServerError, MastodonNetworkError,
        MastodonNotFoundError, MastodonVersionError
)
from sys import exit, stderr
from threading import active_count, BoundedSemaphore, Lock, Thread
from time import sleep
from typing import TextIO


class Obtainer:
    # Max. number of worker threads. Minimum: 1.
    # If using too many, you'll likely get rate limited and gather no data at
    # all. 8 was fine, at least for one run.
    MAX_THREADS = 6
    USER_AGENT = 'Webis Mastodon crawler (https://webis.de/, webis@listserv.uni-weimar.de)'

    def __init__(self, input_file: TextIO, output_file: str) -> None:
        self.input_file = input_file
        self.output_file = output_file
        self.input_data = {}
        self.output_data = {}
        self.done = 0
        self.todo = 0
        # The 2 additional Threads are the main and a write-to-file thread.
        self.limiter = BoundedSemaphore(self.MAX_THREADS + 2)
        self.lock = Lock()

    def get_instances_data(self) -> None:
        """Read an instance list from a JSON file , query all instances for
        `nodeinfo` and `instance/activity` and save the data to a file.
        """
        # Read input file.
        lines = self.input_file.readlines()
        # Reading a `nodes.json` file.
        if (len(lines) == 1):
            self.input_data = {
                instance: {
                    'instance': instance,
                    'nodeinfo': None,
                    'activity': None,
                }
                for instance in loads(lines[0])
            }
        else:
            # Reading output of this program.
            for line in lines:
                line_dict = loads(line)
                self.input_data[line_dict['instance']] = line_dict
        self.todo = len(self.input_data)
        # Skip instances that were done already.
        try:
            with open(self.output_file, mode='r') as f:
                for line in f:
                    del self.input_data[loads(line)['instance']]
                    self.done += 1
        except FileNotFoundError:
            pass
        writer_thread = Thread(target=self.write_data)
        writer_thread.start()
        # Obtain data.
        for instance in self.input_data.keys():
            self.limiter.acquire()
            t = Thread(
                target=self.query_instance, args=(instance,)
            )
            t.start()

    def query_instance(self, instance: str) -> None:
        data = self.input_data[instance]
        if (data['nodeinfo'] and data['activity']):
            skip = True
        else:
            try:
                mastodon = Mastodon(
                    api_base_url=instance,
                    request_timeout=30,
                    user_agent=self.USER_AGENT
                )
            # {Index,Value}Error occur if the Mastodon version looks "weird",
            # e. g. if it's not actually a Mastodon server.
            except (IndexError, MastodonVersionError, ValueError):
                skip = True
            else:
                skip = False
        if (not skip):
            if (not data['nodeinfo']):
                try:
                    data['nodeinfo'] = mastodon.instance_nodeinfo()
                except (
                    MastodonAPIError, MastodonInternalServerError,
                    MastodonNetworkError, MastodonNotFoundError,
                    MastodonVersionError
                ):
                    pass
            if (not data['activity']):
                try:
                    data['activity'] = mastodon.instance_activity()
                except (
                    MastodonAPIError, MastodonNetworkError,
                    MastodonNotFoundError, MastodonVersionError
                ):
                    pass
        # Replace datetime.datetime objects by ISO strings so we can write
        # it to file as JSON.
        with self.lock:
            self.output_data[instance] = self.replace_datetime(data)
        self.done += 1
        print(f'\r{self.done}/{self.todo}', end='', flush=True)
        self.limiter.release()

    def write_data(self) -> None:
        with open(self.output_file, mode='a') as f:
            while (True):
                if (self.done >= self.todo):
                    return
                sleep(10)
                with self.lock:
                    for value in self.output_data.values():
                        f.write(f'{dumps(value, ensure_ascii=False)}\n')
                    self.output_data = {}

    def replace_datetime(self, iterable: dict | list) -> dict | list:
        """Iterate over arbitrary, possibly nested dicts and lists and replace
        datetime objects with strings in ISO format.
        """
        if (isinstance(iterable, dict)):
            it = iter(iterable.items())
        else:
            it = iter(enumerate(iterable))
        for key, value in it:
            if isinstance(value, datetime):
                if (not value.tzinfo):
                    iterable[key] = value.replace(
                        tzinfo=UTC).isoformat()
                else:
                    iterable[key] = value.isoformat()
            elif isinstance(value, dict) or isinstance(value, list):
                iterable[key] = self.replace_datetime(value)
        return iterable
