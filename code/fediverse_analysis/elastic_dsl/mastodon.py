"""Define a common Mastodon status in Elasticsearch DSL."""

from datetime import datetime
from elasticsearch_dsl import (
    Boolean, Date, Document, Float, InnerDoc,
    Integer, Keyword, Nested, Object, Text
)

class Account(InnerDoc):
    # acct is handle@instance
    acct: str = Keyword()
    avatar: str = Text()
    bot: bool = Boolean()
    display_name: str = Text()
    followers_count: int = Integer()
    following_count: int = Integer()
    group: bool = Boolean()
    id: str = Keyword()
    statuses_count: int = Integer()
    url: str = Text()
    username: str = Keyword()

class Application(InnerDoc):
    name: str = Keyword()
    website: str = Text()

# A teaser of linked content.
class Card(InnerDoc):
    description: str = Text()
    height: int = Integer()
    image: str = Text()
    language: str = Keyword()
    provider_name: str = Text()
    type: str = Keyword()
    title: str = Text()
    url: str = Text()
    width: int = Integer()

class Emoji(InnerDoc):
    # Emojis are custom emojis per instance. The URL shows where one can find
    # them. They are used in a status by writing :shortcode: .
    shortcode: str = Keyword()
    url: str = Text()

# Part of MediaAttachment: focal point for thumbnails
class Focus(InnerDoc):
    x: float = Float()
    y: float = Float()

# Meta information of MediaAttachments.
class MetaInfo(InnerDoc):
    aspect: float = Float()
    bitrate: int = Integer()
    duration: float = Float()
    frame_rate: str = Text()
    height: int = Integer()
    width: int = Integer()

# Meta information of MediaAttachments.
class Meta(InnerDoc):
    audio_bitrate: str = Text()
    audio_channels: str = Text()
    audio_encode: str = Text()
    focus: Focus() = Object(Focus)
    original: MetaInfo() = Object(MetaInfo)
    small: MetaInfo() = Object(MetaInfo)

class MediaAttachment(InnerDoc):
    blurhash: str = Text()
    description: str = Text()
    id: str = Keyword()
    meta_: Meta = Object(Meta)
    preview_url: str = Text()
    remote_url: str = Text()
    type: str = Keyword()
    url: str = Text()

class Mention(InnerDoc):
    acct: str = Keyword()
    id: str = Keyword()
    url: str = Text()
    username: str = Keyword()

# An option of a poll
class Option(InnerDoc):
    title: str = Text()
    votes_count: int = Integer()

class Poll(InnerDoc):
    expires_at: datetime = Date()
    id: str = Keyword()
    # Whether multiple selection is allowed
    multiple: bool = Boolean()
    voters_count: int = Integer()

    options: list[Option] = Nested(Option)

    def add_option(self, title, votes_count) -> None:
        self.options.append(Option(title=title, votes_count=votes_count))

# Reblog is a reference to another status that was boosted ("retweeted")
class Reblog(InnerDoc):
    id: str = Keyword()
    url: str = Text()

class Tag(InnerDoc):
    name: str = Keyword()
    url: str = Text()


class Status(Document):
    account: Account = Object(Account)
    # Custom attribute
    api_url: str = Text()
    # Which application was used to post this status
    application: Application = Object(Application)
    card: Card = Object(Card)
    content: str = Text()
    # Custom attribute
    crawled_from_api_url = Text()
    # Custom attribute
    crawled_from_instance = Keyword()
    created_at: datetime = Date()
    edited_at: datetime = Date()
    id: str = Keyword()
    in_reply_to_account_id: str = Keyword()
    in_reply_to_id: str = Keyword()
    # Custom attribute: the instance this status was posted on
    instance: str = Keyword()
    # Custom attribute: if this status originates from the instance itself
    is_local: bool = Boolean()
    language: str = Keyword()
    # Custom attribute
    last_seen: datetime = Date()
    poll: Poll = Object(Poll)
    reblog: Reblog = Object(Reblog)
    # On media: Indicates NSFW. / Activates click to show.
    sensitive: bool = Boolean()
    spoiler_text: str = Text()
    uri: str = Text()
    url: str = Text()
    visibility: str = Keyword()

    emojis: list[Emoji] = Nested(Emoji)
    media_attachments: list[MediaAttachment] = Nested(MediaAttachment)
    mentions: list[Mention] = Nested(Mention)
    tags: list[str] = Nested(Tag)

    class Index:
        name = 'corpus_mastodon_statuses'
        settings = {
            'number_of_shards': 10,
            'number_of_replicas': 2
        }

    def add_emoji(self, shortcode, url) -> None:
        self.emojis.append(Emoji(shortcode=shortcode, url=url))

    def add_media_attachment(
        self, blurhash, description, id, raw_meta,
        preview_url, remote_url, type, url
    ) -> None:
        """meta should be the original dict that Mastodon.py gives: with an
        'original' entry that itself is a dict containing 'aspect', 'height'
        and 'width' as integers.
        """
        if (raw_meta):
            if (focus := raw_meta.get('focus')):
                focus = Focus(
                    x=focus.get('x'),
                    y=focus.get('y')
                )
            else:
                focus = None
            if (orig := raw_meta.get('original')):
                orig_meta_info = MetaInfo(
                    aspect=orig.get('aspect'),
                    bitrate=orig.get('bitrate'),
                    duration=orig.get('duration'),
                    frame_rate=orig.get('frame_rate'),
                    height=orig.get('height'),
                    width=orig.get('width')
                )
            else:
                orig_meta_info = None
            if (small := raw_meta.get('small')):
                small_meta_info = MetaInfo(
                    aspect=small.get('aspect'),
                    bitrate=small.get('bitrate'),
                    duration=small.get('duration'),
                    frame_rate=small.get('frame_rate'),
                    height=small.get('height'),
                    width=small.get('width')
                )
            else:
                small_meta_info = None
            meta_ = Meta(
                audio_bitrate=raw_meta.get('audio_bitrate'),
                audio_channels=raw_meta.get('audio_channels'),
                audio_encode=raw_meta.get('audio_encode'),
                focus=focus,
                original=orig_meta_info,
                small=small_meta_info
            )
        else:
            meta_ = None
        self.media_attachments.append(
            MediaAttachment(
                blurhash=blurhash, description=description, id=id,
                meta_=meta_, preview_url=preview_url,
                remote_url=remote_url, type=type, url=url
            )
        )

    def add_mention(self, acct, id, url, username) -> None:
        self.mentions.append(
            Mention(acct=acct, id=id, url=url, username=username))

    def add_tag(self, name, url) -> None:
        self.tags.append(Tag(name=name, url=url))

    def set_account(
        self, acct, avatar, bot, display_name, followers_count,
        following_count, group, id, statuses_count, url, username
    ) -> None:
        self.account = Account(
            acct=acct,
            avatar=avatar,
            bot=bot,
            display_name=display_name,
            followers_count=followers_count,
            following_count=following_count,
            group=group,
            id=id,
            statuses_count=statuses_count,
            url=url,
            username=username
        )

    def set_application(self, name: str, website: str) -> None:
        if (name or website):
            self.application = Application(name=name, website=website)

    def set_card(
        self, description, height, image, language,
        provider_name, type, title, url, width
    ) -> None:
        self.card = Card(
            description=description,
            height=height,
            image=image,
            language=language,
            provider_name=provider_name,
            type=type,
            title=title,
            url=url,
            width=width
        )

    def set_poll(
            self, expires_at, id, multiple, options, voters_count) -> None:
        """options should be a list of dicts, each dict being one vote option
        like this: {'title': 'Choice 1', 'votes_count': 0}
        (the default in Mastodon.py).
        """
        poll = Poll(expires_at=expires_at, id=id, multiple=multiple,
            voters_count=voters_count)
        for option in options:
            poll.add_option(option.get('title'), option.get('votes_count'))
        self.poll = poll

    def set_reblog(self, id, url) -> None:
        self.reblog = Reblog(id=id, url=url)
