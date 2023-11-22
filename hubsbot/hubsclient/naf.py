import time
from .utils import typed_dataclass, field, gen_uuid


@typed_dataclass
class NAF:
    network_id: str = field(default_factory=gen_uuid)
    owner_id: str | None = None
    creator_id: str | None = None
    last_owner_time: float = field(default_factory=time.time)
    template: str | None = None
    persistent: bool = False
    parent: str | None = None
    components: list = field(default_factory=list)
    is_first_sync: bool = True

    def to_obj(self):
        self.last_owner_time = time.time()
        data = {
            "networkId": self.network_id,
            "owner": self.owner_id or self.creator_id,
            "creator": self.creator_id or self.owner_id,
            "lastOwnerTime": self.last_owner_time,
            "template": self.template,
            "persistent": self.persistent,
            "parent": self.parent,
            "components": self.components,
            "isFirstSync": self.is_first_sync,
        }
        self.is_first_sync = False
        return data

    @classmethod
    def from_obj(cls, data):
        obj = cls(
            network_id=data["networkId"],
            owner_id=data["owner"],
            creator_id=data["creator"],
            parent=data["parent"],
            template=data["template"],
            persistent=data["persistent"],
        )
        obj.last_owner_time = data["lastOwnerTime"]
        obj.components = data["components"]
        obj.is_first_sync = data["isFirstSync"]
        return obj
