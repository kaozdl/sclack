#!/usr/bin/env python3
import urwid
from slackclient import SlackClient
from pyslack import config
from pyslack.components import Time, User, Indicators, TextDivider, SideBar, Channel, MessageBox, ChannelHeader, ChatBox, Message, Profile, Reaction, Attachment
from pyslack.image import Image
from pyslack.markdown import MarkdownText
from datetime import datetime
import pprint
import requests

token = config.get_pyslack_config().get('DEFAULT', 'Token')

palette = [
    ('app', '', '', '', 'h99', 'h235'),
    ('sidebar', '', '', '', 'white', 'h24'),
    ('chatbox', '', '', '', 'h99', 'h235'),
    ('chatbox_header', '', '', '', 'h255', 'h235'),
    ('message_input', '', '', '', 'h255', 'h235'),
    ('prompt', '', '', '', 'white', 'h27'),
    ('prompt_arrow', '', '', '', 'h27', 'h235'),
    ('datetime', '', '', '', 'h239', 'h235'),
    ('username', '', '', '', 'h71,underline', 'h235'),
    ('message', '', '', '', 'h253', 'h235'),
    ('history_date', '', '', '', 'h244', 'h235'),
    ('is_typing', '', '', '', 'h244', 'h235'),
    ('selected_channel', '', '', '', 'white', 'h162'),
    ('active_channel', '', '', '', 'white', 'h33'),
    ('active_message', '', '', '', 'white', 'h237'),
    ('active_link', '', '', '', 'h21,underline', 'h237'),
    ('separator', '', '', '', 'h244', 'h235'),
    ('edited', '', '', '', 'h239', 'h235'),
    ('starred', '', '', '', 'h214', 'h235'),
    ('reaction', '', '', '', 'h27', 'h235'),
    ('presence_active', '', '', '', 'h40', 'h24'),
    ('presence_away', '', '', '', 'h239', 'h24'),
    ('link', '', '', '', 'h21,underline', 'h235'),
    ('cite', '', '', '', 'italics,white', 'h235'),
    ('app_badge', '', '', '', 'h235', 'h248'),
    ('field_title', '', '', '', 'white,bold,underline', 'h235'),
    ('field_value', '', '', '', 'h253', 'h235'),
    ('italics', '', '', '', 'italics,white', 'h235'),
    ('bold', '', '', '', 'bold,h254', 'h235'),
    ('code', '', '', '', 'h124', 'h252')
]

def main():
    slack = SlackClient(token)
    slack_channels = slack.api_call('conversations.list', exclude_archived=True, types='public_channel,private_channel,im,mpim')['channels']

    my_channels = list(filter(lambda channel:
        'is_channel' in channel and channel['is_member'] and (channel['is_channel'] or not channel['is_mpim']),
        slack_channels))
    my_channels.sort(key=lambda channel: channel['name'])

    channels = [
        Channel(channel['name'], is_private=channel['is_private'], is_selected=channel['id'] == 'C1A1MMJAE')
        for channel in my_channels
    ]
    urwid.set_encoding('UTF-8')

    profile = Profile(name="haskellcamargo", is_online=True)
    sidebar = urwid.AttrWrap(SideBar(channels=channels, title='nginformatica', profile=profile), 'sidebar')
    header = urwid.AttrWrap(ChannelHeader(
        date='Today',
        topic='Tudo é terrível',
        num_members=13,
        name='rung',
        is_private=False
    ), 'chatbox_header')
    message_box = urwid.AttrWrap(MessageBox(user='haskellcamargo', typing='vitorebatista'), 'message_input')

    messages = slack.api_call('channels.history', unreads=True, channel='C1A1MMJAE')['messages']
    members = slack.api_call('users.list')['members']

    def shorten_hex(color):
        return '{}{}{}'.format(
            hex(round(int(color[:2], 16) / 17))[-1],
            hex(round(int(color[2:4], 16) / 17))[-1],
            hex(round(int(color[4:], 16) / 17))[-1]
        )

    messages.reverse()
    with open('ignored.pyc', 'w+') as m:
        m.write(pprint.pformat(messages))

    def find_user(id, users):
        return next(filter(lambda user: user['id'] == id, users), None)

    def find_bot(id, users):
        return next(filter(lambda user: user.get('is_bot', False) and user['profile']['bot_id'] == id, users), None)

    _messages = []
    # Bots cache
    _bots = {}
    for message in messages:
        if message.get('subtype', None) == 'bot_message':
            bot = find_bot(message['bot_id'], members)
            if bot:
                user_name = bot['profile']['display_name']
            elif message['bot_id'] in _bots:
                # Use bot data from cache
                bot = _bots.get(message['bot_id'])
                user_name = bot['name']
            else:
                bot = slack.api_call('bots.info', bot=message['bot_id'])['bot']
                _bots[message['bot_id']] = bot
                user_name = bot['name']

            is_app = 'app_id' in bot
            color = '#{}'.format(shorten_hex(bot.get('color', '333333')))
        else:
            is_app = False
            user = find_user(message['user'], members)
            user_name = user['profile']['display_name']
            color = '#{}'.format(shorten_hex(user.get('color', '333333')))

        file = message.get('file')
        if file and file.get('filetype', None) in ('jpg', 'png', 'gif', 'jpeg', 'bmp'):
            file = Image(token=token, path=file['url_private'])
        else:
            file = None

        attachments = [
            Attachment(
                fields=attachment.get('fields'), color='#{}'.format(
                    shorten_hex(attachment.get('color', 'CCCCCC'))
                ),
                pretext=attachment.get('pretext')
            )
            for attachment in message.get('attachments', [])
        ]

        time = Time(message['ts'])
        text = MarkdownText(message['text'])
        is_edited = 'edited' in message
        is_starred = message.get('is_starred', False)
        reactions = list(map(
            lambda reaction: Reaction(name=reaction['name'], count=reaction['count']),
            message.get('reactions', [])
        ))

        user = User(name=user_name, color=color, is_app=is_app)
        indicators = Indicators(is_edited=is_edited, is_starred=is_starred)

        _messages.append(Message(
            time=time,
            user=user,
            text=text,
            indicators=indicators,
            reactions=reactions,
            file=file,
            attachments=attachments
        ))
    chatbox = ChatBox(
        messages=_messages,
        header=header,
        message_box=message_box
    )

    chatbox = urwid.AttrWrap(chatbox, 'chatbox')
    columns = urwid.Columns([
        ('fixed', 25, sidebar),
        ('weight', 1, chatbox)
    ])
    app = urwid.Frame(urwid.AttrWrap(columns, 'app'))
    loop = urwid.MainLoop(app, palette)
    loop.screen.set_terminal_properties(colors=256)
    loop.screen.set_mouse_tracking()
    loop.run()
main()
