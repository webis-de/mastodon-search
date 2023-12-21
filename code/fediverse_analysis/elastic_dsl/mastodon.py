"""Define a common Mastodon status in Elasticsearch DSL."""

from datetime import datetime
from elasticsearch_dsl import (
    Boolean, Date, Document, Float, InnerDoc,
    Integer, Keyword, Nested, Object, Text
)

class Emoji(InnerDoc):
    # Emojis are custom emojis per instance. The URL shows where one can find
    # them. They are used in a status by writing :shortcode: .
    shortcode: str = Keyword()
    static_url: str = Keyword()
    url: str = Keyword()
    visible_in_picker: bool = Boolean()

class Field(InnerDoc):
    # Additional metadata attached to a profile as name-value pairs.
    name: str = Text()
    value: str = Text()
    verified_at: datetime = Date()

class Account(InnerDoc):
    # acct is handle@instance
    acct: str = Keyword()
    avatar: str = Keyword()
    avatar_static: str = Keyword()
    bot: bool = Boolean()
    created_at: datetime = Date()
    discoverable: bool = Boolean()
    display_name: str = Keyword()
    followers_count: int = Integer()
    following_count: int = Integer()
    group: bool = Boolean()
    # Custom attribute: username@instance
    handle: str = Keyword()
    header: str = Keyword()
    header_static: str = Keyword()
    id: str = Keyword()
    last_status_at: datetime = Date()
    locked: bool = Boolean()
    noindex: bool = Boolean()
    note: str = Text()
    statuses_count: int = Integer()
    url: str = Keyword()
    uri: str = Keyword()
    username: str = Keyword()

    emojis: list[Emoji] = Nested(Emoji)
    fields: list[Field] = Nested(Field)

    def add_emoji(
        self, shortcode, url, static_url, visible_in_picker
    ) -> None:
        self.emojis.append(Emoji(
            shortcode=shortcode,
            url=url,
            static_url=static_url,
            visible_in_picker=visible_in_picker
        ))

    def add_field(self, name, value, verified_at) -> None:
        self.fields.append(Field(
            name=name, value=value, verified_at=verified_at
        ))

class Application(InnerDoc):
    name: str = Keyword()
    website: str = Keyword()

# A teaser of linked content.
class Card(InnerDoc):
    author_name: str = Keyword()
    author_url: str = Keyword()
    blurhash: str = Keyword()
    description: str = Text()
    embed_url: str = Keyword()
    height: int = Integer()
    image: str = Keyword()
    image_description: str = Text()
    language: str = Keyword()
    provider_name: str = Keyword()
    provider_url: str = Keyword()
    published_at: datetime = Date()
    title: str = Text()
    type: str = Keyword()
    url: str = Keyword()
    width: int = Integer()

# Part of MediaAttachment: focal point for thumbnails
class Focus(InnerDoc):
    x: float = Float()
    y: float = Float()

# Meta information of MediaAttachments.
class MetaInfo(InnerDoc):
    aspect: float = Float()
    bitrate: int = Integer()
    duration: float = Float()
    frame_rate: str = Keyword()
    height: int = Integer()
    width: int = Integer()

# Meta information of MediaAttachments.
class Meta(InnerDoc):
    audio_bitrate: str = Keyword()
    audio_channels: str = Keyword()
    audio_encode: str = Keyword()
    focus: Focus() = Object(Focus)
    original: MetaInfo() = Object(MetaInfo)
    small: MetaInfo() = Object(MetaInfo)

class MediaAttachment(InnerDoc):
    blurhash: str = Keyword()
    description: str = Text()
    id: str = Keyword()
    meta_: Meta = Object(Meta)
    preview_url: str = Keyword()
    remote_url: str = Keyword()
    type: str = Keyword()
    url: str = Keyword()

class Mention(InnerDoc):
    acct: str = Keyword()
    id: str = Keyword()
    url: str = Keyword()
    username: str = Keyword()

# An option of a poll
class Option(InnerDoc):
    title: str = Text()
    votes_count: int = Integer()

class Poll(InnerDoc):
    expires_at: datetime = Date()
    expired: bool = Boolean()
    id: str = Keyword()
    # Whether multiple selection is allowed
    multiple: bool = Boolean()
    votes_count: int = Integer()
    voters_count: int = Integer()

    options: list[Option] = Nested(Option)

    def add_option(self, title, votes_count) -> None:
        self.options.append(Option(title=title, votes_count=votes_count))

# Reblog is a reference to another status that was boosted ("retweeted")
class Reblog(InnerDoc):
    id: str = Keyword()
    url: str = Keyword()

class Tag(InnerDoc):
    name: str = Keyword()
    url: str = Keyword()


class Status(Document):
    account: Account = Object(Account)
    # Custom attribute
    api_url: str = Keyword()
    # Which application was used to post this status
    application: Application = Object(Application)
    card: Card = Object(Card)
    content: str = Text()
    # Custom attribute
    crawled_at: datetime = Date()
    # Custom attribute
    crawled_from_api_url = Keyword()
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
    poll: Poll = Object(Poll)
    reblog: Reblog = Object(Reblog)
    # On media: Indicates NSFW. / Activates click to show.
    sensitive: bool = Boolean()
    spoiler_text: str = Text()
    uri: str = Keyword()
    url: str = Keyword()
    visibility: str = Keyword()

    emojis: list[Emoji] = Nested(Emoji)
    media_attachments: list[MediaAttachment] = Nested(MediaAttachment)
    mentions: list[Mention] = Nested(Mention)
    tags: list[str] = Nested(Tag)

    class Index:
        name = 'corpus_mastodon_statuses'
        settings = {
            'number_of_replicas': 2,
            'number_of_shards': 10
        }

    def add_emoji(
        self, shortcode, url, static_url, visible_in_picker
    ) -> None:
        self.emojis.append(Emoji(
            shortcode=shortcode,
            url=url,
            static_url=static_url,
            visible_in_picker=visible_in_picker
        ))

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
        self, acct, avatar, avatar_static, bot, created_at, discoverable,
        display_name, emojis, fields, followers_count, following_count, group,
        handle, header, header_static, id, last_status_at, locked, noindex,
        note, statuses_count, uri, url, username
    ) -> None:
        self.account = Account(
            acct=acct,
            avatar=avatar,
            avatar_static=avatar_static,
            bot=bot,
            created_at=created_at,
            discoverable=discoverable,
            display_name=display_name,
            followers_count=followers_count,
            following_count=following_count,
            group=group,
            handle=handle,
            header=header,
            header_static=header_static,
            id=id,
            last_status_at=last_status_at,
            locked=locked,
            noindex=noindex,
            note=note,
            statuses_count=statuses_count,
            uri=uri,
            url=url,
            username=username
        )
        for emoji in emojis:
            self.account.add_emoji(
                shortcode=emoji.get('shortcode'),
                static_url=emoji.get('static_url'),
                url=emoji.get('url'),
                visible_in_picker=emoji.get('visible_in_picker')
            )
        for field in fields:
            self.account.add_field(
                field.get('name'),
                field.get('value'),
                field.get('verified_at')
            )

    def set_application(self, name: str, website: str) -> None:
        if (name or website):
            self.application = Application(name=name, website=website)

    def set_card(
        self, author_name, author_url, blurhash, description, embed_url,
        height, image, image_description, language, provider_name,
        provider_url, published_at, title, type, url, width
    ) -> None:
        self.card = Card(
            author_name=author_name,
            author_url=author_url,
            blurhash=blurhash,
            description=description,
            embed_url=embed_url,
            height=height,
            image=image,
            image_description=image_description,
            language=language,
            provider_name=provider_name,
            provider_url=provider_url,
            published_at=published_at,
            title=title,
            type=type,
            url=url,
            width=width
        )

    def set_poll(
            self, expires_at, expired, id, multiple,
            options, voters_count, votes_count
    ) -> None:
        """options should be a list of dicts, each dict being one vote option
        like this: {'title': 'Choice 1', 'votes_count': 0}
        (the default in Mastodon.py).
        """
        poll = Poll(
            expires_at=expires_at, expired=expired, id=id, multiple=multiple,
            voters_count=voters_count, votes_count=votes_count
        )
        for option in options:
            poll.add_option(option.get('title'), option.get('votes_count'))
        self.poll = poll

    def set_reblog(self, id, url) -> None:
        self.reblog = Reblog(id=id, url=url)
