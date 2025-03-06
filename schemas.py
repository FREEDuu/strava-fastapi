from pydantic import BaseModel
from typing import Optional, List

class GitHubContribution(BaseModel):
    date_activity: str
    kudos_count: int

class YearRequest(BaseModel):
    year: int
    code: str

class ActivitySummary(BaseModel):
    total_activities: int
    total_elevation_gain: float
    total_moving_time: int
    total_distance: float

class Map(BaseModel):
    id: Optional[str] = None
    summary_polyline: Optional[str] = None
    resource_state: Optional[int] = None

class AthleteActivityBase(BaseModel):
    id: int
    resource_state: Optional[int] = None
    athlete_id: int
    name: Optional[str] = None
    distance: Optional[float] = None
    moving_time: Optional[int] = None
    elapsed_time: Optional[int] = None
    total_elevation_gain: Optional[float] = None
    type: Optional[str] = None
    sport_type: Optional[str] = None
    workout_type: Optional[int] = None
    start_date: Optional[str] = None
    start_date_local: Optional[str] = None
    timezone: Optional[str] = None
    utc_offset: Optional[float] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_country: Optional[str] = None
    achievement_count: Optional[int] = None
    kudos_count: Optional[int] = None
    comment_count: Optional[int] = None
    athlete_count: Optional[int] = None
    photo_count: Optional[int] = None
    map: Optional[Map] = None  
    trainer: Optional[bool] = None
    commute: Optional[bool] = None
    manual: Optional[bool] = None
    private: Optional[bool] = None
    visibility: Optional[str] = None
    flagged: Optional[bool] = None
    gear_id: Optional[str] = None
    start_latlng: Optional[List[float]] = None
    end_latlng: Optional[List[float]] = None
    average_speed: Optional[float] = None
    max_speed: Optional[float] = None
    average_cadence: Optional[float] = None
    has_heartrate: Optional[bool] = None
    average_heartrate: Optional[float] = None
    max_heartrate: Optional[float] = None
    heartrate_opt_out: Optional[bool] = None
    display_hide_heartrate_option: Optional[bool] = None
    elev_high: Optional[float] = None
    elev_low: Optional[float] = None
    upload_id: Optional[int] = None
    upload_id_str: Optional[str] = None
    external_id: Optional[str] = None
    from_accepted_tag: Optional[bool] = None
    pr_count: Optional[int] = None
    total_photo_count: Optional[int] = None
    has_kudoed: Optional[bool] = None

class AthleteActivityCreate(AthleteActivityBase):
    pass

class AthleteActivity(AthleteActivityBase):
    class Config:
        orm_mode = True

class AthleteBase(BaseModel):
    id: int
    username: Optional[str] = None
    resource_state: Optional[int] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    sex: Optional[str] = None
    premium: Optional[bool] = None
    summit: Optional[bool] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    badge_type_id: Optional[int] = None
    weight: Optional[float] = None
    profile_medium: Optional[str] = None
    profile: Optional[str] = None
    friend: Optional[str] = None
    follower: Optional[str] = None

class AthleteCreate(AthleteBase):
    pass

class Athlete(AthleteBase):
    class Config:
        orm_mode = True

class TokenResponse(BaseModel):
    token_type: str
    expires_at: int
    expires_in: int
    refresh_token: str
    access_token: str
    athlete: Athlete

class ActivitySchema(BaseModel):
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
        orm_mode = True

class ActivityCreate(BaseModel):
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

class AccessTokenRequest(BaseModel):
    code: str

class AccessTokenRequestLimit(BaseModel):
    code: str
    limit: int
    
class GroupedActivities(BaseModel):
    type_activity: str
    activities_count: int

class FriendActivity(BaseModel):
    friend_count: int
    activity_count: int

