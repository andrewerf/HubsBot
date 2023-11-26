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
        components = data['components']
        if '0' in components:
            position = components['0']
            self.position[0] = position['x']
            self.position[1] = position['y']
            self.position[2] = position['z']

    def update_from_nafr_um(self, data: dict):
        """
        It seems like Hubs use "nafr" for a more lightweight representation of naf.
        Only some data is transmitted with nafr.
        Types of nafrs (um, nn, etc.) are mysterious....
        """
        ds = data['d']
        if len(ds) > 0:
            self.update_from_naf(ds[0])