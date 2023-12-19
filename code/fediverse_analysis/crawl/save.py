from collections import deque
from collections.abc import Iterator
from datetime import datetime, UTC
from elasticsearch import AuthenticationException
from elasticsearch.helpers import streaming_bulk
from elasticsearch_dsl import connections
from threading import Thread
from time import sleep
from uuid import NAMESPACE_URL, uuid5

from fediverse_analysis.elastic_dsl.mastodon import Status


class _Save(deque[Status]):
    """Provide methods to store ActivityPub data on disk."""
    # How many statuses are saved to Elasticsearch at once.
    CHUNK_SIZE = 500
    # Save to Elasticsearch after this number of minutes, even if there are
    # less statuses than CHUNK_SIZE. Note that saving only takes place after
    # the next status is received.
    MAX_MINUTES = 10
    INT_MAX = 2**31 - 1
    INT_MIN = -2**31
    NAMESPACE_FA = uuid5(NAMESPACE_URL, 'fediverse_analysis')
    NAMESPACE_MASTODON = uuid5(NAMESPACE_FA, 'Mastodon')

    def __init__(self) -> None:
        self.es_connection = None
        self.flush = False
        self.flush_minutes = 0
        self.timer = Thread(
            target=self.bulk_timer, daemon=True)

        self.timer.start()

    def bulk_timer(self) -> None:
        while True:
            sleep(60)
            self.flush = True
            self.flush_minutes += 1

    def check_int(self, num: int) -> str:
        if (num <= self.INT_MAX and num >= self.INT_MIN):
            return num
        else:
            return None

    def check_str(self, value: object) -> str:
        return (str(value) if value else None)

    def generate_statuses(self) -> Iterator[Status]:
        while (self):
            yield self.popleft()

    def get_last_id(self, instance: str) -> str | None:
        """Return latest id of all statuses that were crawled from a given
        instance, or None if there is no status yet.
        """
        status = Status.search()\
                .filter('term', crawled_from_instance=instance)\
                .sort('-crawled_at')\
                .source(['id'])\
                .params(size=1)\
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

    def write_status(
        self, status: dict, crawled_from_instance: str, api_method: str
    ) -> None:
        """Write an ActivityPub status to an Elasticsearch instance.
        Arguments:
        status -- The mastodon status as received by Mastodon.py
        crawled_from_instance -- Which fediverse instance this status was
            crawled from
        api_method -- The API method/path, e. g. 'api/v1/streaming/public'
        """
        # Put status data into the ES DSL document.
        status_uuid = uuid5(self.NAMESPACE_MASTODON,
            crawled_from_instance + '/' + str(status.get('id')))
        acc = status.get('account')
        if (acc.get('acct') == acc.get('username')):
            instance = crawled_from_instance
            is_local = True
        else:
            instance = acc.get('acct').split('@', maxsplit=1)[1]
            is_local = False
        dsl_status = Status(
            meta={'id': status_uuid},
            api_url=('https://' + crawled_from_instance
                       + '/api/v1/statuses/' + str(status.get('id'))),
            content=status.get('content'),
            crawled_at=datetime.now(tz=UTC),
            crawled_from_api_url=(
                'https://' + crawled_from_instance + '/' + api_method),
            crawled_from_instance=crawled_from_instance,
            created_at=status.get('created_at'),
            edited_at=status.get('edited_at'),
            id=str(status.get('id')),
            in_reply_to_id=self.check_str(status.get('in_reply_to_id')),
            in_reply_to_account_id=self.check_str(
                status.get('in_reply_to_account_id')),
            instance=instance,
            is_local=is_local,
            language=status.get('language'),
            sensitive=status.get('sensitive'),
            spoiler_text=self.check_str(status.get('spoiler_text')),
            uri=status.get('uri'),
            url=status.get('url'),
            visibility=status.get('visibility')
        )
        dsl_status.set_account(
            acct=acc.get('acct'),
            avatar=acc.get('avatar'),
            avatar_static=acc.get('avatar_static'),
            bot=acc.get('bot'),
            created_at=acc.get('created_at'),
            discoverable=acc.get('discoverable'),
            display_name=acc.get('display_name'),
            emojis=acc.get('emojis'),
            fields=acc.get('fields'),
            followers_count=self.check_int(acc.get('followers_count')),
            following_count=self.check_int(acc.get('following_count')),
            group=acc.get('group'),
            handle=(acc.get('username') + '@' + instance),
            header=acc.get('header'),
            header_static=acc.get('header_static'),
            id=str(acc.get('id')),
            last_status_at=acc.get('last_status_at'),
            locked=acc.get('locked'),
            noindex=acc.get('noindex'),
            note=self.check_str(acc.get('note')),
            statuses_count=self.check_int(acc.get('statuses_count')),
            uri=acc.get('uri'),
            url=acc.get('url'),
            username=acc.get('username')
        )
        if (app := status.get('application')):
            dsl_status.set_application(
                name=app.get('name'),
                website=app.get('website'))
        if (card := status.get('card')):
            dsl_status.set_card(
                author_name=self.check_str(card.get('author_name')),
                author_url=self.check_str(card.get('author_url')),
                blurhash=self.check_str(card.get('blurhash')),
                description=self.check_str(card.get('description')),
                embed_url=self.check_str(card.get('embed_url')),
                height=card.get('height'),
                image=card.get('image'),
                image_description=self.check_str(
                    card.get('image_description')),
                language=self.check_str(card.get('language')),
                provider_name=self.check_str(card.get('provider_name')),
                provider_url=self.check_str(card.get('provider_url')),
                published_at=card.get('published_at'),
                title=self.check_str(card.get('title')),
                type=card.get('type'),
                url=self.check_str(card.get('url')),
                width=card.get('width')
            )
        if (poll := status.get('poll')):
            dsl_status.set_poll(
                expires_at=poll.get('expires_at'),
                expired=poll.get('expired'),
                id=str(poll.get('id')),
                multiple=poll.get('multiple'),
                options=poll.get('options'),
                voters_count=poll.get('voters_count'),
                votes_count=poll.get('votes_count')
            )
        if (reblog := status.get('reblog')):
            dsl_status.set_reblog(
                id=str(reblog.get('id')),
                url=reblog.get('url')
            )
        for emoji in status.get('emojis'):
            dsl_status.add_emoji(
                shortcode=emoji.get('shortcode'),
                static_url=emoji.get('static_url'),
                url=emoji.get('url'),
                visible_in_picker=emoji.get('visible_in_picker')
            )
        for ma in status.get('media_attachments'):
            dsl_status.add_media_attachment(
                blurhash=self.check_str(ma.get('blurhash')),
                description=self.check_str(ma.get('description')),
                id=str(ma.get('id')),
                raw_meta=ma.get('meta'),
                preview_url=self.check_str(ma.get('preview_url')),
                remote_url=self.check_str(ma.get('remote_url')),
                type=ma.get('type'),
                url=ma.get('url')
            )
        for mention in status.get('mentions'):
            dsl_status.add_mention(
                acct=mention.get('acct'),
                id=str(mention.get('id')),
                url=mention.get('url'),
                username=mention.get('username')
            )
        for tag in status.get('tags'):
            dsl_status.add_tag(
                name=tag.get('name'),
                url=tag.get('url')
            )

        # Save status.
        self.append(dsl_status.to_dict(include_meta=True))
        if (self.flush):
            if (len(self) >= self.CHUNK_SIZE
                    or self.flush_minutes >= self.MAX_MINUTES):
                deque(
                    streaming_bulk(
                        client=self.es_connection,
                        actions=self.generate_statuses()
                    ),
                    maxlen=0
                )
                self.flush_minutes = 0
            self.flush = False
