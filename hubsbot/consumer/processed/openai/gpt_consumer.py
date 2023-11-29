from typing import List, Dict

import openai

from hubsbot import Bot
from hubsbot.consumer import TextConsumer, Message
from hubsbot.consumer.processed.vosk import VoskVoiceConsumer
from hubsbot.peer import Peer

entry_prompt = """
You are a voice assistant for VR platform Mozilla Hubs. You receive messages transcribed from a particular user in the VR room.
Note that transcriptions may not be absolutely correct. Feel free to correct words which you think are transcribed incorrectly based on the context.
"""


class GptConsumer(TextConsumer):
    def __init__(self, peer: Peer, bot: Bot):
        # history of messages
        self.history: List[Dict] = [
            {'role': 'system', 'content': entry_prompt}
        ]
        self.peer = peer
        self.bot = bot

    async def on_message(self, msg: Message):
        self.history.append({'role': 'user', 'content': msg.body})
        completion = await openai.ChatCompletion.acreate(model="gpt-3.5-turbo",
                                                         messages=self.history)
        self.history.append(completion.choices[0].message)
        await self.bot.hubs_client.send_chat(f'{self.peer.display_name}: {completion.choices[0].message["content"]}')
