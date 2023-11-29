from abc import ABC, abstractmethod


class VoiceConsumer(ABC):
    @abstractmethod
    async def start(self):
        """
        Starts consuming. Should be called right after the initialisation.

        This function is called in "fire-and-forget" manner, therefore it probably should not return unless :meth:`stop` is called.
        """
        pass

    @abstractmethod
    async def stop(self):
        """
        Gracefully stops consuming
        """
        pass