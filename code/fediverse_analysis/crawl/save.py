from datetime import datetime, UTC
from elasticsearch import AuthenticationException
from elasticsearch_dsl import connections, Index
from json import dumps
from uuid import NAMESPACE_URL, uuid5

from fediverse_analysis.elastic_dsl.mastodon import Status


class _Save:
    """Provide methods to store ActivityPub data on disk."""
    ACCOUNT = 'account'
    ACCT = 'acct'
    APPLICATION = 'application'
    AVATAR = 'avatar'
    BOT = 'bot'
    CARD = 'card'
    CONTENT = 'content'
    CREATED_AT = 'created_at'
    DESCRIPTION = 'description'
    DISPLAY_NAME = 'display_name'
    EDITED_AT = 'edited_at'
    EMOJIS = 'emojis'
    EXPIRES_AT = 'expires_at'
    FOLLOWERS_COUNT = 'followers_count'
    FOLLOWING_COUNT = 'following_count'
    GROUP = 'group'
    HEIGHT = 'height'
    ID = 'id'
    IMAGE = 'image'
    IN_REPLY_TO_ACCOUNT_ID = 'in_reply_to_account_id'
    IN_REPLY_TO_ID = 'in_reply_to_id'
    LANGUAGE = 'language'
    LAST_STATUS_AT = 'last_status_at'
    MEDIA_ATTACHMENTS = 'media_attachments'
    MENTIONS = 'mentions'
    MULTIPLE = 'multiple'
    META = 'meta'
    NAME = 'name'
    OPTIONS = 'options'
    POLL = 'poll'
    PREVIEW_REMOTE_URL = 'preview_remote_url'
    PREVIEW_URL = 'preview_url'
    PROVIDER_NAME = 'provider_name'
    REBLOG = 'reblog'
    REMOTE_URL = 'remote_url'
    REPLIES_COUNT = 'replies_count'
    SENSITIVE = 'sensitive'
    SHORTCODE = 'shortcode'
    SPOILER_TEXT = 'spoiler_text'
    STATUSES_COUNT = 'statuses_count'
    TAGS = 'tags'
    TITLE = 'title'
    TYPE = 'type'
    URI = 'uri'
    URL = 'url'
    USERNAME = 'username'
    VISIBILITY = 'visibility'
    VOTERS_COUNT = 'voters_count'
    WEBSITE = 'website'
    WIDTH = 'width'

    NAMESPACE_FA = uuid5(NAMESPACE_URL, 'fediverse_analysis')
    NAMESPACE_MASTODON = uuid5(NAMESPACE_FA, 'Mastodon')

    def __init__(self) -> None:
        self.es_connection = None
        self.output_file = None

    def replace_datetime(self, iterable: dict | list) -> dict | list:
        """Iterate over possibly nested dicts and lists and replace datetime
        objects with strings in ISO format with millisecond precision,
        e. g.: 2000-01-01-19T00:00:00.000+00:00 .
        """
        if (isinstance(iterable, dict)):
            it = iter(iterable.items())
        else:
            it = iter(enumerate(iterable))
        for key, value in it:
            if isinstance(value, datetime):
                if (not value.tzinfo):
                    iterable[key] = value.replace(
                        tzinfo=UTC).isoformat(timespec='milliseconds')
                else:
                    iterable[key] = value.isoformat(timespec='milliseconds')
            elif isinstance(value, dict) or isinstance(value, list):
                iterable[key] = self.replace_datetime(value)
        return iterable

    def init_es_connection(
        self,
        host: str,
        password: str = '',
        port: int = 9200,
        username: str = ''
    ) -> None:
        es_host = host + ':' + str(port)
        try:
            self.es_connection = connections.create_connection(
                hosts=es_host, basic_auth=(username, password))
        except ValueError as e:
            print('URL must include scheme and host, e. g. https://localhost')
            exit(1)
        try:
            # exists should be run every time to actually check the connection.
            if (not Status._index.exists(self.es_connection)):
                Status.init()
        except AuthenticationException:
            print('Authentication failed. Wrong username and/or password.')
            exit(1)
        except Exception as e:
            print(e)
            exit(1)

    def replace(self, string: str) -> str:
        return (string if string else None)

    def write_status(self, status: dict, instance: str, method: str) -> None:
        """Write an ActivityPub status to the previously defined output.
        Arguments:
        method -- How the status was retrieved, e. g. 'stream'
        """
        if (self.output_file):
            status = self.replace_datetime(status)
            self.output_file.write(dumps(status, ensure_ascii=False) + '\n')
        # Elasticsearch
        else:
            status_uuid = uuid5(self.NAMESPACE_MASTODON,
                instance + '/' + str(status.get(self.ID)))
            tags = []
            for tag in status.get(self.TAGS):
                tags.append(tag[self.NAME])
            # Put status data into the ES DSL frame.
            acc = status.get(self.ACCOUNT)
            dsl_status = Status(
                meta={'id': status_uuid},
                api_url = ('https://' + instance
                           + '/api/v1/statuses/' + str(status.get(self.ID))),
                content = status.get(self.CONTENT),
                crawl_method = method,
                created_at = status.get(self.CREATED_AT),
                edited_at = status.get(self.EDITED_AT),
                id = str(status.get(self.ID)),
                in_reply_to_id = str(status.get(self.IN_REPLY_TO_ID)),
                in_reply_to_account_id = str(
                    status.get(self.IN_REPLY_TO_ACCOUNT_ID)),
                instance = instance,
                language = status.get(self.LANGUAGE),
                last_seen = datetime.now(tz=UTC),
                local = (acc.get(self.ACCT) == acc.get(self.USERNAME)),
                sensitive = status.get(self.SENSITIVE),
                spoiler_text = self.replace(status.get(self.SPOILER_TEXT)),
                tags = tags,
                uri = status.get(self.URI),
                url = status.get(self.URL),
                visibility = status.get(self.VISIBILITY)
            )
            dsl_status.set_account(
                acct = acc.get(self.ACCT),
                avatar = acc.get(self.AVATAR),
                bot = acc.get(self.BOT),
                display_name = acc.get(self.DISPLAY_NAME),
                followers_count = acc.get(self.FOLLOWERS_COUNT),
                following_count = acc.get(self.FOLLOWING_COUNT),
                group = acc.get(self.GROUP),
                id = str(acc.get(self.ID)),
                statuses_count = acc.get(self.STATUSES_COUNT),
                url = acc.get(self.URL),
                username = acc.get(self.USERNAME)
            )
            if (app := status.get(self.APPLICATION)):
                dsl_status.set_application(
                    app.get(self.NAME), app.get(self.WEBSITE))
            if (card := status.get(self.CARD)):
                dsl_status.set_card(
                    description = self.replace(status.get(self.DESCRIPTION)),
                    height = status.get(self.HEIGHT),
                    image = status.get(self.IMAGE),
                    language = self.replace(status.get(self.LANGUAGE)),
                    provider_name = self.replace(status.get(self.PROVIDER_NAME)),
                    type = status.get(self.TYPE),
                    title = self.replace(status.get(self.TITLE)),
                    url = status.get(self.URL),
                    width = status.get(self.WIDTH))
            if (poll := status.get(self.POLL)):
                dsl_status.set_poll(
                    expires_at = poll.get(self.EXPIRES_AT),
                    id = str(poll.get(self.ID)),
                    multiple = poll.get(self.MULTIPLE),
                    options = poll.get(self.OPTIONS),
                    voters_count = poll.get(self.VOTERS_COUNT)
                )
            if (reblog := status.get(self.REBLOG)):
                dsl_status.set_reblog(
                    str(reblog.get(self.ID)),
                    reblog.get(self.URL)
                )
            for emoji in status.get(self.EMOJIS):
                dsl_status.add_emoji(
                    emoji.get(self.SHORTCODE),
                    emoji.get(self.URL)
                )
            for ma in status.get(self.MEDIA_ATTACHMENTS):
                dsl_status.add_media_attachment(
                    self.replace(ma.get(self.DESCRIPTION)),
                    str(ma.get(self.ID)),
                    ma.get(self.META),
                    ma.get(self.PREVIEW_URL),
                    ma.get(self.REMOTE_URL),
                    ma.get(self.TYPE),
                    ma.get(self.URL)
                )
            for mention in status.get(self.MENTIONS):
                dsl_status.add_mention(
                    mention.get(self.ACCT),
                    str(mention.get(self.ID)),
                    mention.get(self.URL),
                    mention.get(self.USERNAME)
                )
            dsl_status.save()
