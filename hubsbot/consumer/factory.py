from abc import ABC, abstractmethod
from aiortc import MediaStreamTrack

from hubsbot.peer import Peer
from .voice_consumer import VoiceConsumer
from .text_consumer import TextConsumer


class ConsumerFactory(ABC):
    @abstractmethod
    def create_voice_consumer(self, peer: Peer, track: MediaStreamTrack) -> VoiceConsumer:
        """
        Create a voice consumer for the given remote peer.

        :param peer: Peer
        :param track: The track associated with the consumer
        :return: Created consumer
        """
        pass

    @abstractmethod
    def create_text_consumer(self, peer: Peer) -> TextConsumer:
        """
        Create a text (chat) consumer for the given remote peer.

        :param peer: Peer
        :return: Created consumer
        """
        pass
