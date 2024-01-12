from datetime import datetime, UTC
from json import dumps, JSONDecodeError, load, loads
from mastodon import (
        Mastodon, MastodonAPIError,
        MastodonInternalServerError, MastodonNetworkError,
        MastodonNotFoundError, MastodonVersionError
)
from sys import exit, stderr
from typing import TextIO

USER_AGENT = 'Webis Mastodon crawler (https://webis.de/, webis@listserv.uni-weimar.de)'

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
    # Find out where we left last time.
    try:
        with open(output_file, mode='rb') as f:
            # Go to the beginning of the last line.
            try:
                f.seek(-2, 2)
                while (f.read(1) != b'\n'):
                    f.seek(-2, 1)
                last_instance_done = loads(f.readline().decode()).get('instance')
            except OSError:
                last_instance_done = ''
    except FileNotFoundError:
        last_instance_done = ''
    # Obtain data.
    with open(output_file, mode='a') as f:
        for instance in instances:
            skip = False
            if(instance <= last_instance_done):
                continue
            print(f'\r{instance}                                    ', end='')
            try:
                mastodon = Mastodon(
                    api_base_url=instance,
                    user_agent=USER_AGENT
                )
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

def get_instances_data_rerun(input_file: TextIO, output_file: str) -> None:
    """Take the output file of get_instances_data as input_file and re-query
    all instances with incomplete data to fill in gaps. If run a few times,
    this actually increases the amount of instances with data by 5–10%.
    """
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
    with open(output_file, mode='a') as f:
        for line in input_file:
            line_dic = loads(line)
            instance = line_dic['instance']
            if(instance <= last_instance_done):
                print('instance already present in output file:', instance)
                continue
            if (line_dic['nodeinfo'] and line_dic['activity']):
                f.write(f'{dumps(line_dic, ensure_ascii=False)}\n')
                print(instance, '– data already present')
                continue
            skip = False
            print(instance)
            try:
                mastodon = Mastodon(
                    api_base_url=instance,
                    request_timeout=5,
                    user_agent=USER_AGENT
                )
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
            dic = replace_datetime(dic)
            f.write(f'{dumps(dic, ensure_ascii=False)}\n')
        print()

def replace_datetime(iterable: dict | list) -> dict | list:
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
            iterable[key] = replace_datetime(value)
    return iterable
