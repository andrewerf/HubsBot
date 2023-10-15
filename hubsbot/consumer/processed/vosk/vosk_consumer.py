import json
from typing import List
from aiortc import MediaStreamTrack
from av import AudioFrame
from pydub import AudioSegment
import io
import itertools

from vosk import Model, KaldiRecognizer

from hubsbot.consumer.processed.phrases_consumer import PhrasesVoiceConsumer


def batched(x, n):
    it = iter(x)
    for batch in itertools.islice(it, n):
        yield batch


class VoskVoiceConsumer(PhrasesVoiceConsumer):
    def __init__(self, track: MediaStreamTrack):
        super().__init__(track)
        self.model = Model(lang='ru')
        self.framerate = 48000
        self.rec = KaldiRecognizer(self.model, self.framerate)
        self.rec.SetWords(True)
        self.rec.SetPartialWords(True)

    async def on_phrase_text(self, text: str):
        pass

    async def on_phrase(self, frames: List[AudioFrame]):
        segment = AudioSegment.empty()
        for frame in frames:
            raw = frame.to_ndarray().tobytes()
            s = io.BytesIO(raw)
            segment = segment + AudioSegment.from_raw(s, sample_width=frame.format.bytes,
                                                      channels=len(frame.layout.channels), frame_rate=frame.sample_rate)

        segment = segment.set_frame_rate(self.framerate)
        segment = segment.set_channels(1)
        self.rec.AcceptWaveform(segment.raw_data)

        res = json.loads(self.rec.FinalResult())['text']
        await self.on_phrase_text(res)
