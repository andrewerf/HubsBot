import asyncio
from dataclasses import dataclass
from math import atan2
from typing import List
from asyncio import Queue

import numpy as np
from aiortc.mediastreams import AudioStreamTrack

from hubsbot import Bot
from hubsbot.consumer import Message, TextConsumer as BaseTextConsumer
from hubsbot.consumer.abstract.factory import ConsumerFactory as BaseConsumerFactory
from hubsbot.consumer.processed.vosk import VoskVoiceConsumer
from hubsbot.hubsclient.utils import Rotation, Vector3
from hubsbot.peer import Peer


@dataclass
class Animation:
    @dataclass
    class Node:
        pos: np.ndarray # position of node
        r: float = 0.1 # radius to stop before the node
        time: float | None = None # time of transition from previous node to current one
        speed: float | None = 0.2 # speed of transition from previous node to current one.
        # if both time and speed are given, speed takes precedence. If neither are given, animation is instant.

        on_complete = None # coroutine to be invoked when animation has been completed

    nodes: List[Node] # list of nodes to visit


class AnimatedBot(Bot):
    animations: Queue[Animation] = Queue()

    async def _animate(self, animation: Animation):
        async def animate_to_node(self, node: Animation.Node):
            pos = np.asarray(self.hubs_client.avatar.position)[:-1]
            initial_pos = pos
            dist = np.linalg.norm(pos - node.pos, 2)
            k = 0.01

            def get_speed():
                if node.time is None and node.speed is None:
                    return float('inf')
                elif node.speed is not None:
                    return node.speed
                else:
                    return dist / node.time

            speed = k * get_speed()

            direction = (node.pos - initial_pos)
            angle = 180 * atan2(direction[0], direction[2]) / np.pi
            self.hubs_client.avatar.head_transform.rotation = Rotation(x=0, y=angle + 180, z=0)
            await self.hubs_client.sync()

            while dist > node.r:
                pos += speed * direction
                self.hubs_client.avatar.position = Vector3(x=pos[0], y=pos[1], z=pos[2])
                dist = np.linalg.norm(pos - node.pos, 2)
                await self.hubs_client.sync()
                await asyncio.sleep(k)

            if node.on_complete is not None:
                await node.on_complete()

        for node in animation.nodes:
            await animate_to_node(self, node)

    async def _animation_runner(self):
        await asyncio.sleep(3)
        while True:
            animation = await self.animations.get()
            await self._animate(animation)
            self.animations.task_done()

    async def join(self):
        t = super().join()
        return await asyncio.gather(t, asyncio.create_task(self._animation_runner()))


class ConferenceBot(AnimatedBot):

    async def on_room_entered(self):
        pass

    async def join(self):
        t = super().join()
        await self.animations.put(Animation([Animation.Node(pos=np.array([0.04097, 0.1741, -10.9033]))]))



class VoiceConsumer(VoskVoiceConsumer):
    def __init__(self, track: AudioStreamTrack, peer: Peer, bot: Bot):
        super().__init__(track)
        self.peer = peer
        self.bot = bot

    async def on_message(self, msg: Message):
        await self.bot.hubs_client.send_chat(f'Transcribed from {self.peer.display_name}: {msg.body}')
        await self.bot.hubs_client.sync()


class TextConsumer(BaseTextConsumer):
    def __init__(self, peer: Peer, bot: AnimatedBot):
        self.bot = bot
        self.peer = peer

    async def on_message(self, msg: Message):
        print(f'Received msg: {msg}')
        if msg.body == 'pos':
            await self.bot.hubs_client.send_chat(str(self.bot.hubs_client.avatar.position))
        await self.bot.animations.put(Animation(nodes=[Animation.Node(pos=self.peer.matrix[:3, -1], r=1)]))
        pass


class ConsumerFactory(BaseConsumerFactory):
    def __init__(self, bot: AnimatedBot):
        self.bot = bot
        pass

    def create_text_consumer(self, peer: Peer):
        return TextConsumer(peer, self.bot)

    def create_voice_consumer(self, peer: Peer, track: AudioStreamTrack):
        recorder = VoiceConsumer(track, peer, self.bot)
        return recorder




def main():
    bot = AnimatedBot(
        host='9de36d10e9.us2.myhubs.net',
        room_id='YuRGAyX',
        avatar_id='basebot',
        display_name='Conference bot',
        consumer_factory=None,
        voice_track=AudioStreamTrack())
    bot.consumer_factory = ConsumerFactory(bot)

    asyncio.get_event_loop().run_until_complete(bot.join())

if __name__ == '__main__':
    main()