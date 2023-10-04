from dataclasses import dataclass
from typing import List


@dataclass
class Peer:
    """
    Represents the **remote** peer in Hubs.
    """
    id: str # id of the peer
    display_name: str # display name of the peer
    position: List[float] # Vector3f -- position on the scene
    # TODO: avatar description (head, hands position, skin, mesh, etc...) to be here

    def update_from_naf(self, data: dict):
        """
        Updates the peer from stupid and ugly Hubs representation of NAF
        (idk what this abbreviation means, there is no docs on the Hubs protocol).
        """
        position = data['components']["0"]
        self.position[0] = position['x']
        self.position[1] = position['y']
        self.position[2] = position['z']
