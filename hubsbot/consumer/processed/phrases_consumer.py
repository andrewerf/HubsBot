import asyncio
from enum import Enum
from typing import List

from av import AudioFrame

from aiortc import MediaStreamTrack
from aiortc.mediastreams import MediaStreamError

from hubsbot.consumer import VoiceConsumer

import numpy as np
import matplotlib.pyplot as plt


def get_frame_time(frame):
    return frame.samples / frame.sample_rate


class SlidingAverage:
    frames: List[np.ndarray] = []
    lengths: List[float] = []
    length: float = 0

    def __init__(self, length):
        self.length = length

    def add_frame(self, frame: AudioFrame):
        self.lengths.append(get_frame_time(frame))
        self.frames.append(frame.to_ndarray())
        if sum(self.lengths)>self.length:
            self.frames.pop(0)
            self.lengths.pop(0)

    def calc(self):
        return np.abs(np.concatenate(self.frames, axis=1)).mean()


class State(Enum):
    Phrase = 0
    Pause = 1


class PhrasesVoiceConsumer(VoiceConsumer):
    """
    This consumer provides an abstract method ``on_phrase`` which is called when a phrase was separated from the
    input track.
    Phrases are separated based on the sliding-window amplitude of the input frames.
    """

    async def on_phrase(self, frames: List[AudioFrame]):
        """Receives a single phrase from the input.
        This method is called when a single phrase was separated.
        :param frames: List of frames defining the phrase.
        """
        pass

    def __init__(self, track: MediaStreamTrack, sliding_length: float = 0.5, amp_threshold: float = 200):
        self.track = track
        self.frames = []
        self.sliding_length = sliding_length
        self.amp_threshold = amp_threshold
        self.stopped = False

    async def start(self):
        avg = SlidingAverage(self.sliding_length)
        state = State.Pause
        phrase_started = 0

        while not self.stopped:
            try:
                frame = await self.track.recv()
            except MediaStreamError:
                break
            self.frames.append(frame)

            avg.add_frame(frame)
            v = avg.calc()
            if state == State.Pause and v > self.amp_threshold:
                state = State.Phrase
                phrase_started = len(self.frames)
            elif state == State.Phrase and v < self.amp_threshold:
                state = State.Pause
                await self.on_phrase(self.frames[phrase_started:])

        await self.on_phrase(self.frames[phrase_started:])

    async def stop(self):
        self.stopped = True
