from datetime import datetime, UTC
from json import dumps, JSONDecodeError, load, loads
from mastodon import (
        Mastodon, MastodonAPIError,
        MastodonInternalServerError, MastodonNetworkError,
        MastodonNotFoundError, MastodonVersionError
)
from sys import exit, stderr
from typing import TextIO

def get_instances_data(nodes_file: TextIO, output_file: str) -> None:
    """Read an instance list from a JSON file in `nodes_file`, query all
    instances for `nodeinfo` and `instance/activity` and save the data to a
    file.
    """
    try:
        instances = load(nodes_file)
    except JSONDecodeError:
        print(f'File does not contain valid JSON: {nodes_file}', file=stderr)
        exit(1)
    # Go to the beginning of the last line
    try:
        with open(output_file, mode='rb') as f:
            try:
                f.seek(-2, 2)
                while (f.read(1) != b'\n'):
                    f.seek(-2, 1)
                last_instance_done = loads(f.readline().decode()).get('instance')
            except OSError:
                last_instance_done = ''
    except FileNotFoundError:
        last_instance_done = ''
    # Get data
    with open(output_file, mode='a') as f:
        for instance in instances:
            skip = False
            if(instance <= last_instance_done):
                continue
            print(f'\r{instance}                                    ', end='')
            try:
                mastodon = Mastodon(api_base_url=instance)
            # {Index,Value}Error occur if the Mastodon version looks "weird",
            # e. g. if it's not actually a Mastodon server.
            except (IndexError, MastodonVersionError, ValueError):
                skip = True
                nodeinfo = None
                activity = None
            if (not skip):
                try:
                    nodeinfo = mastodon.instance_nodeinfo()
                except (
                    MastodonAPIError, MastodonInternalServerError,
                    MastodonNetworkError, MastodonNotFoundError,
                    MastodonVersionError
                ):
                    nodeinfo = None
                try:
                    activity = mastodon.instance_activity()
                except (MastodonAPIError, MastodonNetworkError,
                        MastodonNotFoundError, MastodonVersionError):
                    activity = None
            dic = {
                'instance': instance,
                'nodeinfo': nodeinfo,
                'activity': activity
            }
            # Replace datetime.datetime objects by ISO strings so we can write
            # it to file as JSON.
            dic = replace_datetime(dic)
            f.write(f'{dumps(dic, ensure_ascii=False)}\n')
        print()

def replace_datetime(iterable: dict | list) -> dict | list:
    """Iterate over possibly nested dicts and lists and replace datetime
    objects with strings in ISO format.
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
            iterable[key] = replace_datetime(value)
    return iterable
