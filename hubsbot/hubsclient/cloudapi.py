from typing import Literal, Callable, Any
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
import requests
import json
from .utils import typed_dataclass, inf


@typed_dataclass
class RoomInfo:
    id: str
    name: str
    description: str
    url: str
    scene_id: str
    room_size: int
    lobby_count: int
    member_count: int
    user_data: dict
    is_public: bool
    preview_image_url: str

    @classmethod
    def from_obj(cls, data: dict):
        if not data.get("type") == "room":
            return data
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            url=data.get("url", ""),
            scene_id=data.get("scene_id", ""),
            room_size=data.get("room_size") or 0,
            lobby_count=data.get("lobby_count") or 0,
            member_count=data.get("member_count") or 0,
            user_data=data.get("user_data") or {},
            is_public=data.get("is_public", True),
            preview_image_url=data.get("images", {}).get("preview", {}).get("url") or "",
        )


@typed_dataclass
class AvatarInfo:
    id: str
    name: str
    description: str
    url: str
    preview_images: dict
    gltfs: dict
    attributions: dict
    allow_remixing: bool

    @classmethod
    def from_obj(cls, data: dict):
        if not data.get("type") == "avatar_listing":
            return data
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            url=data.get("url", ""),
            preview_images=dict(data.get("images", {})).get("preview") or {},
            gltfs=data.get("gltfs") or {},
            attributions=data.get("attributions") or {},
            allow_remixing=data.get("allow_remixing", True),
        )


class CloudAPI:
    def __init__(self, host: str, app_token: str = None, user_token: str = None, user_id: str = None):
        """Hubs Cloud API client.

        :param host: The host of the room, e.g. "hubs.mozilla.com"
        :param app_token: The API key app token (from https://<host>/token)
        :param user_token: The API key user token (from https://<host>/token)
        """
        self.host = host
        self.gqlapp_transport = None
        self.gqlapp_client = None
        self.app_token = app_token
        if app_token is not None:
            self._gql_app_connect()
        self.gqluser_transport = None
        self.gqluser_client = None
        self.user_token = user_token
        if user_token is not None:
            self._gql_user_connect()
        self.user_id = user_id

    def _gql_app_connect(self, app_token: str = None):
        self.app_token = app_token or self.app_token
        self.gqlapp_transport = RequestsHTTPTransport(
            url=f"https://{self.host}/api/v2_alpha/graphiql",
            use_json=True,
            headers={
                "Content-type": "application/json",
                "Authorization": "Bearer " + app_token,
            },
            verify=True,
            retries=3,
        )
        self.gqlapp_client = Client(transport=self.gqlapp_transport, fetch_schema_from_transport=True)

    def _gql_user_connect(self, user_token: str = None):
        self.user_token = user_token or self.user_token
        self.gqluser_transport = RequestsHTTPTransport(
            url=f"https://{self.host}/api/v2_alpha/graphiql",
            use_json=True,
            headers={
                "Content-type": "application/json",
                "Authorization": "Bearer " + user_token,
            },
            verify=True,
            retries=3,
        )
        self.gqluser_client = Client(transport=self.gqluser_transport, fetch_schema_from_transport=True)

    def _v1api_query(self, route: str, params: dict = {}, method: Literal["GET", "POST"] = "GET"):
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'HubsClient/0.1.0',
        }
        if self.user_token is not None:
            headers['Authorization'] = f'Bearer {self.user_token}'
        match method:
            case "GET":
                return requests.get(f"https://{self.host}/api/v1/{route}", params=params, headers=headers)
            case "POST":
                return requests.post(
                    f"https://{self.host}/api/v1/{route}",
                    data=json.dumps(params).encode('utf-8'),
                    headers=headers & {'Content-Type': 'application/json'},
                )

    def media_search(
        self,
        type: Literal["rooms", "scene_listings", "avatar_listings", "scenes", "avatars", "favorites", "assets"],
        query: str = None,
        _parser: Callable[[dict], Any] | None = None,
        page_limit = None,
        **kwargs,
    ):
        entries = []
        cursor = 1
        while (cursor or inf) < (page_limit or inf) + 1:
            resp = self._v1api_query(
                "media/search", params={"source": type, "q": query, "user": self.user_id, "cursor": cursor, **kwargs}
            ).json(object_hook=_parser)
            cursor = resp["meta"]["next_cursor"]
            entries.extend(resp["entries"])
        return entries

    def get_public_rooms(self, **kwargs):
        return self.media_search("rooms", filter="public", _parser=RoomInfo.from_obj, **kwargs)

    def get_avatars(self, **kwargs):
        return self.media_search("avatar_listings", _parser=AvatarInfo.from_obj, **kwargs)
