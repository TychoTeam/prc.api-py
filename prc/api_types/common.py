from typing import List, Dict, TypedDict, Union, TypeVar

V = TypeVar("V")

# Since the API uses "maps", which are supposed to be dicts
# but when empty are actually sent as lists.
_APIMap = Union[Dict[str, V], List[None]]


class C_MapsResponse(TypedDict):
    maps: List[str]
