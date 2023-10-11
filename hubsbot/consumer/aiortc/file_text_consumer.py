from pathlib import Path
from hubsbot.consumer import TextConsumer, Message


class FileTextConsumer(TextConsumer):
    def __init__(self, path: Path):
        """
        This consumer puts each message into a file, separating them by triple new line character ('\n\n\n').
        :param path: The path of the file to write into
        """
        self.path = path

    async def on_message(self, msg: Message):
        with open(self.path, 'a') as f:
            f.write(msg.body + '\n\n\n')
