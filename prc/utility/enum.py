from typing import Type, TypeVar
from enum import Enum, IntEnum


class InsensitiveEnum(Enum):
    """
    String enum that is case insensitive. Values must be lowercase.
    """

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


T = TypeVar("T", bound="DisplayNameEnum")


class DisplayNameEnum(IntEnum):
    """
    Modified int enum that adds display names.
    """

    display_name: str

    def __new__(cls, value: int, display_name: str):
        obj = int.__new__(cls)
        obj._value_ = value
        obj.display_name = display_name
        return obj

    @classmethod
    def parse(cls: Type[T], display_name: str) -> T:
        for member in cls:
            if member.display_name.lower() == display_name.lower():
                return member
        raise ValueError(f"Unknown {cls.__name__} display_name: '{display_name}'")

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Enum):
            return self.value == other.value
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        return self.display_name
