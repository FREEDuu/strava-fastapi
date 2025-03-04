from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, ARRAY, BigInteger
from database import Base
from sqlalchemy.orm import relationship

from sqlalchemy import Column, BigInteger, Float, String, Boolean, ForeignKey, ARRAY
from database import Base
from sqlalchemy.orm import relationship

from sqlalchemy import Column, BigInteger, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.mutable import MutableDict
import json

class AthleteActivity(Base):
    __tablename__ = "athlete_activities"

    id = Column(BigInteger, primary_key=True, index=True)
    resource_state = Column(BigInteger, nullable=True)
    athlete_id = Column(BigInteger, ForeignKey("athletes.id"))
    name = Column(String, nullable=True)
    distance = Column(Float, nullable=True)
    moving_time = Column(BigInteger, nullable=True)
    elapsed_time = Column(BigInteger, nullable=True)
    total_elevation_gain = Column(Float, nullable=True)
    type = Column(String, nullable=True)
    sport_type = Column(String, nullable=True)
    workout_type = Column(BigInteger, nullable=True)
    start_date = Column(String, nullable=True)
    start_date_local = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    utc_offset = Column(Float, nullable=True)
    location_city = Column(String, nullable=True)
    location_state = Column(String, nullable=True)
    location_country = Column(String, nullable=True)
    achievement_count = Column(BigInteger, nullable=True)
    kudos_count = Column(BigInteger, nullable=True)
    comment_count = Column(BigInteger, nullable=True)
    athlete_count = Column(BigInteger, nullable=True)
    photo_count = Column(BigInteger, nullable=True)
    map = Column(MutableDict.as_mutable(JSONB), nullable=True) 
    trainer = Column(Boolean, nullable=True)
    commute = Column(Boolean, nullable=True)
    manual = Column(Boolean, nullable=True)
    private = Column(Boolean, nullable=True)
    visibility = Column(String, nullable=True)
    flagged = Column(Boolean, nullable=True)
    gear_id = Column(String, nullable=True)
    start_latlng = Column(ARRAY(Float), nullable=True)
    end_latlng = Column(ARRAY(Float), nullable=True)
    average_speed = Column(Float, nullable=True)
    max_speed = Column(Float, nullable=True)
    average_cadence = Column(Float, nullable=True)
    has_heartrate = Column(Boolean, nullable=True)
    average_heartrate = Column(Float, nullable=True)
    max_heartrate = Column(Float, nullable=True)
    heartrate_opt_out = Column(Boolean, nullable=True)
    display_hide_heartrate_option = Column(Boolean, nullable=True)
    elev_high = Column(Float, nullable=True)
    elev_low = Column(Float, nullable=True)
    upload_id = Column(BigInteger, nullable=True)
    upload_id_str = Column(String, nullable=True)
    external_id = Column(String, nullable=True)
    from_accepted_tag = Column(Boolean, nullable=True)
    pr_count = Column(BigInteger, nullable=True)
    total_photo_count = Column(BigInteger, nullable=True)
    has_kudoed = Column(Boolean, nullable=True)

    athlete = relationship("Athlete", back_populates="activities")

class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_type = Column(String)
    expires_at = Column(Integer)
    expires_in = Column(Integer)
    refresh_token = Column(String)
    access_token = Column(String)
    athlete_id = Column(Integer, ForeignKey("athletes.id"))

    athlete = relationship("Athlete", back_populates="token")

class Athlete(Base):
    __tablename__ = "athletes"

    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String, nullable=True)
    resource_state = Column(Integer, nullable=True)
    firstname = Column(String, nullable=True)
    lastname = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    sex = Column(String, nullable=True)
    premium = Column(Boolean, nullable=True)
    summit = Column(Boolean, nullable=True)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)
    badge_type_id = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)
    profile_medium = Column(String, nullable=True)
    profile = Column(String, nullable=True)
    friend = Column(String, nullable=True)
    follower = Column(String, nullable=True)

    token = relationship("Token", back_populates="athlete", uselist=False) #uselist=False if one to one
    activities = relationship("AthleteActivity", back_populates="athlete") #Corrected relationship name