from enum import Enum


class InsensitiveEnum(Enum):
    """Str enum that is case insensitive. Values must be lowercase."""

    def __new__(cls, value, *args, **kwargs):
        obj = object.__new__(cls)
        if isinstance(value, str):
            value = value.lower()
        obj._value_ = value
        return obj

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            value = value.lower()
        return cls._value2member_map_.get(value)

    @classmethod
    def is_member(cls, value) -> bool:
        if isinstance(value, str):
            value = value.lower()
        return value in cls._value2member_map_
