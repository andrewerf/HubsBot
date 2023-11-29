from pathlib import Path

from aiortc import MediaStreamTrack

from hubsbot.consumer import ConsumerFactory, VoiceConsumer, TextConsumer, Message
from hubsbot.consumer.aiortc import MediaRecorderVoiceConsumer
from hubsbot.peer import Peer


class RecorderFactory(ConsumerFactory):
    def __init__(self, output_path: Path):
        """
        This factory creates consumers writing each peer's speech to a separate .wav file and ignoring the text messages

        :param output_path: The path to save recorded speech.
        """
        self.output_path = output_path

    def create_voice_consumer(self, peer: Peer, track: MediaStreamTrack) -> VoiceConsumer:
        recorder = MediaRecorderVoiceConsumer(str(self.output_path / f'{peer.display_name}.wav'))
        recorder.addTrack(track)
        return recorder

    def create_text_consumer(self, peer: Peer) -> TextConsumer:
        class EmptyTextConsumer(TextConsumer):
            async def on_message(self, msg: Message):
                return

        return EmptyTextConsumer()