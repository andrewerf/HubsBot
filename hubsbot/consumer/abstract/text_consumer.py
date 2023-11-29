from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class Message:
    body: str


class TextConsumer(ABC):
    @abstractmethod
    async def on_message(self, msg: Message):
        """
        This method is called when a new message is received from the remote peer associated with this TextConsumer.

        :param msg: The message
        """
        pass
