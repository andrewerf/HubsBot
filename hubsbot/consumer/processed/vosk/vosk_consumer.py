import json
from typing import List
from aiortc import MediaStreamTrack
from av import AudioFrame
from pydub import AudioSegment
import io
import itertools
from aioprocessing import AioProcess, AioPipe

from vosk import Model, KaldiRecognizer

from hubsbot.consumer import Message
from hubsbot.consumer.processed.phrases_consumer import PhrasesVoiceConsumer


def batched(x, n):
    it = iter(x)
    for batch in itertools.islice(it, n):
        yield batch


def vosk_server(conn, model: Model, framerate: int):
    """
    This function is intended to be called in a separate thread (process actually) to allow non-blocking speech recognition.
    """
    rec = KaldiRecognizer(model, framerate)
    rec.SetWords(True)
    rec.SetPartialWords(True)

    stop = False
    while not stop:
        msg = conn.recv()
        if isinstance(msg, bool):
            stop = msg
        else:
            rec.AcceptWaveform(msg)
            ret = json.loads(rec.FinalResult())
            conn.send(ret)


class VoskVoiceConsumer(PhrasesVoiceConsumer):
    def __init__(self, track: MediaStreamTrack):
        super().__init__(track)
        self.model = Model(lang='ru')
        self.framerate = 48000
        conn1, conn2 = AioPipe(True)
        self.vosk_process = AioProcess(target=vosk_server, args=(conn1, self.model, self.framerate))
        self.vosk_process.start()
        self.conn = conn2

    async def on_message(self, msg: Message):
        pass

    async def on_phrase(self, frames: List[AudioFrame]):
        segment = AudioSegment.empty()
        for frame in frames:
            raw = frame.to_ndarray().tobytes()
            s = io.BytesIO(raw)
            segment = segment + AudioSegment.from_raw(s, sample_width=frame.format.bytes,
                                                      channels=len(frame.layout.channels), frame_rate=frame.sample_rate)

        silence = AudioSegment.silent(2000, self.framerate)
        segment = silence + segment + silence
        segment = segment.set_frame_rate(self.framerate)
        segment = segment.set_channels(1)
        await self.conn.coro_send(segment.raw_data)

        res = (await self.conn.coro_recv())['text']
        await self.on_message(Message(body=res))

    async def stop(self):
        await self.conn.coro_send(False)
        await self.vosk_process.coro_join()
        await self.vosk_process.close()
