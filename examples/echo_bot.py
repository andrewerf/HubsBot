"""
This bot writes transcribed voice messages from each user to the chat
"""
import asyncio
from aiortc.mediastreams import AudioStreamTrack

from hubsbot import Bot
from hubsbot.peer import Peer
from hubsbot.consumer import Message
from hubsbot.consumer import \
    ConsumerFactory as BaseConsumerFactory, TextConsumer as BaseTextConsumer  # Abstract factories
from hubsbot.consumer.processed.vosk import VoskVoiceConsumer # A consumer with text transcription


class TextConsumer(BaseTextConsumer):
    def __init__(self, peer: Peer):
        self.peer = peer

    async def on_message(self, msg: Message):
        print(f'Message from {self.peer.id}: {msg}')


class VoiceConsumer(VoskVoiceConsumer):
    def __init__(self, track: AudioStreamTrack, peer: Peer, bot: Bot):
        super().__init__(track)
        self.peer = peer
        self.bot = bot

    async def on_message(self, msg: Message):
        await self.bot.hubs_client.send_chat(f'Transcribed from {self.peer.display_name}: {msg.body}')


# Override consumer factory
class ConsumerFactory(BaseConsumerFactory):
    def __init__(self, bot: Bot):
        self.bot = bot
        pass

    def create_text_consumer(self, peer: Peer):
        return TextConsumer(peer)

    def create_voice_consumer(self, peer: Peer, track: AudioStreamTrack):
        recorder = VoiceConsumer(track, peer, self.bot)
        return recorder


def main():
    bot = Bot(
        host='HOST',
        room_id='ROOM_ID',
        avatar_id="basebot",
        display_name="Python User",
        consumer_factory=None,
        voice_track=AudioStreamTrack())

    bot.consumer_factory = ConsumerFactory(bot)
    asyncio.get_event_loop().run_until_complete(bot.join())


if __name__ == '__main__':
    main()
