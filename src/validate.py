from enum import Enum
from typing import List
from pydantic import BaseModel


class UserInfo(BaseModel):
    user_id: str
    connected_at: float
    message_count: int


class Distance(str, Enum):
    Near = "near"
    Far = "far"
    Extreme = "extreme"


class ThunderDistance(BaseModel):
    category: Distance


class UserListResponse(BaseModel):
    users: List[str]
