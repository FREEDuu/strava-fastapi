from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Dict, Optional



class Runner(BaseModel):
    id: int
    username: str | None
    created_at: datetime

    class Config:
        from_attributes = True

class DateRange(BaseModel):  
    start_date: Optional[str] = None  
    end_date: Optional[str] = None  

class ActivityLevel(BaseModel):
    level: int

class ActivityGithub(BaseModel):
    data: Dict[str, ActivityLevel]

    class Config:
        from_attributes = True

class Activity(BaseModel):
    id: int
    name: str
    distance: float
    moving_time: int
    elapsed_time: int
    total_elevation_gain: float
    type: str
    sport_type: str
    start_date: str
    start_date_local: str
    timezone: str
    kudos_count: int
    athlete_count: int
    average_speed: float

    class Config:
        from_attributes = True
        model_config = ConfigDict(extra="ignore")  

class GroupedActivities(BaseModel):
    period: str  # 'day', 'week', or 'month'
    groups: Dict[str, List[Activity]]
    
class CreateUserRequest(BaseModel):
    code: str

class StravaAuth(BaseModel):
    access_token: str | None
    refresh_token: str | None
    username: str | None
    expires_at: int | None
    city: Optional[str]
    state: Optional[str]
    profile_image: Optional[str]