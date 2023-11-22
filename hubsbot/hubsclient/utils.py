from dataclasses import KW_ONLY, Field, dataclass, field
from functools import wraps
from uuid import uuid4
from base64 import urlsafe_b64encode as b64encode


def gen_uuid():
    return b64encode(uuid4().bytes).decode("utf-8").strip("=")


def typed_dataclass(cls):
    cls = dataclass(cls)

    @wraps(cls, updated=())
    class _wrap(cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for field in cls.__dataclass_fields__.values():
                if not hasattr(self.__class__, field.name):
                    if not isinstance(getattr(self, field.name), field.type) and not isinstance(
                        getattr(self, field.name), Field
                    ):
                        self.__setattr__(field.name, getattr(self, field.name))

        def __setattr__(self, name, val):
            if name in cls.__dataclass_fields__:
                typ = cls.__dataclass_fields__[name].type
                if not isinstance(val, typ):
                    if isinstance(val, dict):
                        val = typ(**val)
                    elif isinstance(val, list) or isinstance(val, tuple):
                        val = typ(*val)
                    else:
                        val = typ(val)
            super().__setattr__(name, val)

    return _wrap


def indexable(cls):
    if not hasattr(cls, "__slots__"):
        if hasattr(cls, "__dataclass_fields__"):
            cls.__slots__ = tuple(cls.__dataclass_fields__.keys())
        else:
            cls = dataclass(cls, slots=True)

    @wraps(cls, updated=())
    class _wrap(cls):
        def __getitem__(self, ix):
            if isinstance(ix, int):
                return self.__getattribute__(list(self.__slots__)[ix])
            elif ix in self.__slots__:
                return self.__getattribute__(ix)
            else:
                return super().__getitem__(ix)

        def __setitem__(self, ix, val):
            if isinstance(ix, int):
                self.__setattr__(list(self.__slots__)[ix], val)
            elif ix in self.__slots__:
                self.__setattr__(ix, val)
            else:
                super().__setitem__(ix, val)

        def __iter__(self):
            for k in self.__slots__:
                yield self.__getattribute__(k)

        def __len__(self):
            return len(self.__slots__)

    return _wrap


def throw(exc=Exception):
    if not isinstance(exc, Exception):
        exc = Exception(exc)
    raise exc


@indexable
@typed_dataclass
class Vector3:
    x: float = 0
    y: float = 0
    z: float = 0
    _: KW_ONLY
    isVector3: bool = True

    def to_obj(self):
        return {"isVector3": True, "x": self.x, "y": self.y, "z": self.z}


@indexable
@typed_dataclass
class Rotation:
    x: float = 0
    y: float = 0
    z: float = 0

    def to_obj(self):
        return {"x": self.x, "y": self.y, "z": self.z}

inf = float('inf')
