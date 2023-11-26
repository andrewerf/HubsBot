from dataclasses import dataclass
import numpy as np
from transforms3d.affines import decompose44, compose


def _get_updated_matrix(matrix: np.ndarray, components: dict, keys=('0', '1', '2')):
    """
    Given initial matrix, updates it from components.
    :param matrix: The matrix
    :param components: The dictionary of components
    :param keys: Tuple of exactly three keys, for translation, rotation and scale
    :return:
    """
    k1, k2, k3 = keys

    T, R, Z, S = decompose44(matrix)
    if k1 in components and components[k1] is not None:
        position = components[k1]
        T = np.array([position['x'], position['y'], position['z']])

    if k2 in components and components[k2] is not None:
        # Hubs use weird frame for the euler angles, which is not supported by transforms3d
        # Of course it is still possible to find proper formulas, but I'll just leave it as a TODO.
        pass

    if k3 in components and components[k3] is not None:
        scale = components[k3]
        Z = np.array([scale['x'], scale['y'], scale['z']])

    return compose(T, R, Z, S)


@dataclass
class Peer:
    """
    Represents the **remote** peer in Hubs.
    """
    id: str # id of the peer
    display_name: str # display name of the peer
    matrix: np.ndarray # 4x4 affine object matrix. Position vector is matrix[:, :-1].
    head_matrix: np.ndarray # 4x4 affine matrix. Represents "head" transfomation of the object. It is updated with nafr.
    # TODO: avatar description (head, hands position, skin, mesh, etc...) to be here

    def update_from_naf(self, data: dict):
        """
        Updates the peer from stupid and ugly Hubs representation of NAF
        (idk what this abbreviation means, there is no docs on the Hubs protocol).
        """
        components = data['components']
        self.matrix = _get_updated_matrix(self.matrix, components, ('0', '1', '2'))
        self.head_matrix = _get_updated_matrix(self.head_matrix, components, ('5', '6', '9999'))

    def update_from_nafr_um(self, data: dict):
        """
        It seems like Hubs use "nafr" for a more lightweight representation of naf.
        Only some data is transmitted with nafr.
        Types of nafrs (um, nn, etc.) are mysterious....
        """
        ds = data['d']
        if len(ds) > 0:
            self.update_from_naf(ds[0])