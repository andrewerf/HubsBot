from .naf import NAF
from .utils import typed_dataclass, field, Vector3, Rotation
from enum import Enum


class AvatarType(Enum):
    SKINNABLE = "skinnable"
    GLTF = "gltf"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    MODEL = "model"
    TEXT = "text"
    LIGHT = "light"
    PARTICLE = "particle"
    PRIMITIVE = "primitive"
    UNKNOWN = "unknown"


class HandPose(Enum):
    allOpen = 0
    thumbDown = 1
    indexDown = 2
    mrpDown = 3
    thumbsUp = 4
    point = 5
    allGrip = 6
    pinch = 7


@typed_dataclass
class Transform:
    position: Vector3 = field(default_factory=lambda: Vector3(0, 0, 0))
    rotation: Rotation = field(default_factory=lambda: Rotation(0, 0, 0))
    scale: Vector3 = field(default_factory=lambda: Vector3(1, 1, 1))


@typed_dataclass
class HandTransform(Transform):
    pose: HandPose = HandPose.allOpen
    visible: bool = False


@typed_dataclass
class Avatar(NAF):
    avatar_url: str = ""
    position: Vector3 = field(default_factory=Vector3)
    rotation: Rotation = field(default_factory=Rotation)
    scale: Vector3 = field(default_factory=lambda: Vector3(1, 1, 1))
    template: str = "#remote-avatar"
    avatar_type: AvatarType = AvatarType.SKINNABLE
    muted: bool = True
    sharing_avatar_camera: bool = False
    lefthand: HandTransform = field(default_factory=HandTransform)
    righthand: HandTransform = field(default_factory=HandTransform)
    head_transform: Transform = field(default_factory=lambda: Transform(position=Vector3(0, 1.6, 0)))

    @property
    def components(self) -> list:
        return [
            self.position.to_obj(),
            self.rotation.to_obj(),
            self.scale.to_obj(),
            {
                "avatarSrc": self.avatar_url,
                "avatarType": self.avatar_type.value,
                "muted": self.muted,
                "isSharingAvatarCamera": self.sharing_avatar_camera,
            },
            {"left_hand_pose": self.lefthand.pose.value, "right_hand_pose": self.righthand.pose.value},
            self.head_transform.position.to_obj(),
            self.head_transform.rotation.to_obj(),
            self.lefthand.position.to_obj(),
            self.lefthand.rotation.to_obj(),
            self.lefthand.visible,
            self.righthand.position.to_obj(),
            self.righthand.rotation.to_obj(),
            self.righthand.visible,
        ]

    @components.setter
    def components(self, value):
        if value == [] or value is None:
            return
        (
            self.position,
            self.rotation,
            self.scale,
            avatarinfo,
            handposes,
            self.head_transform.position,
            self.head_transform.rotation,
            self.lefthand.position,
            self.lefthand.rotation,
            self.lefthand.visible,
            self.righthand.position,
            self.righthand.rotation,
            self.righthand.visible,
        ) = value
        self.avatar_url = avatarinfo["avatarSrc"]
        self.avatar_type = avatarinfo["avatarType"]
        self.muted = avatarinfo["muted"]
        self.sharing_avatar_camera = avatarinfo["isSharingAvatarCamera"]
        self.lefthand.pose = handposes["left_hand_pose"]
        self.righthand.pose = handposes["right_hand_pose"]
