from datetime import datetime, UTC
from elasticsearch import AuthenticationException
from elasticsearch_dsl import connections, Index
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

    INT_MAX = pow(2, 31) - 1
    INT_MIN = -pow(2, 31)
    NAMESPACE_FA = uuid5(NAMESPACE_URL, 'fediverse_analysis')
    NAMESPACE_MASTODON = uuid5(NAMESPACE_FA, 'Mastodon')

    def __init__(self) -> None:
        self.es_connection = None

    def check_int(self, num: int) -> str:
        if (num <= self.INT_MAX and num >= self.INT_MIN):
            return num
        else:
            return None

    def check_str(self, string: str) -> str:
        return (string if string else None)

    def get_last_id(self, instance: str) -> str | None:
        """Return latest id of all statuses from given instance, or None if
        there is no status yet.
        """
        status = Status.search()\
                .filter('term', instance=instance)\
                .sort('-last_seen')[0]\
                .source(['id'])\
                .execute()\
                .hits
        if (status):
            return status[0]['id']
        else:
            return None

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
            print('Elasticsearch authentication failed.'
                +'Wrong username and/or password.')
            exit(1)

    def write_status(self, status: dict, instance: str, method: str) -> None:
        """Write an ActivityPub status to an Elasticsearch instance.
        Arguments:
        status -- The mastodon status as received by Mastodon.py
        instance -- Which fediverse instance this status is from
        method -- How the status was retrieved, e. g. 'stream'
        """
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
            spoiler_text = self.check_str(status.get(self.SPOILER_TEXT)),
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
            followers_count = self.check_int(acc.get(self.FOLLOWERS_COUNT)),
            following_count = self.check_int(acc.get(self.FOLLOWING_COUNT)),
            group = acc.get(self.GROUP),
            id = str(acc.get(self.ID)),
            statuses_count = self.check_int(acc.get(self.STATUSES_COUNT)),
            url = acc.get(self.URL),
            username = acc.get(self.USERNAME)
        )
        if (app := status.get(self.APPLICATION)):
            dsl_status.set_application(
                app.get(self.NAME), app.get(self.WEBSITE))
        if (card := status.get(self.CARD)):
            dsl_status.set_card(
                description = self.check_str(status.get(self.DESCRIPTION)),
                height = status.get(self.HEIGHT),
                image = status.get(self.IMAGE),
                language = self.check_str(status.get(self.LANGUAGE)),
                provider_name = self.check_str(status.get(self.PROVIDER_NAME)),
                type = status.get(self.TYPE),
                title = self.check_str(status.get(self.TITLE)),
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
                self.check_str(ma.get(self.DESCRIPTION)),
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
