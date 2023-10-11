from hubsbot.consumer import VoiceConsumer
from aiortc.contrib.media import MediaRecorder


class MediaRecorderVoiceConsumer(VoiceConsumer):
    """Nothing to adapt actually.
    """
    def __init__(self, *args, **kwargs):
        self._m = MediaRecorder(*args, **kwargs)

    def addTrack(self, track):
        self._m.addTrack(track)

    async def start(self):
        await self._m.start()

    async def stop(self):
        await self._m.stop()
