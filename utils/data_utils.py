import schemas
from models import Token, Athlete
from sqlalchemy.orm import Session
from models import AthleteActivity as AthleteActivityDB

def get_user_from_access_token(access_token: str, db: Session) -> int:
    token = db.query(Token).filter(Token.access_token == access_token).first()
    if not token:
        raise Exception("Token not found")
    return token.athlete_id

def extract_token(token_response: schemas.TokenResponse):
    token_data = token_response.model_dump()
    athlete_data = token_data.pop("athlete") #remove the athlete dictionary from token_data, and save it.

    token_data["athlete_id"] = athlete_data["id"] #add the athlete id to the token data.
    token_data["id"] = None #or what ever id you want to add.
    print(f"Token data: {token_data}")
    return Token(**token_data)

def save_athlete(athlete_instance: schemas.AthleteBase,db : Session) -> None:
    new_athlete = Athlete(**athlete_instance.model_dump())
    db.add(new_athlete)
    db.commit()
    db.refresh(new_athlete)


def save_refresh_token(token_response: schemas.TokenResponse, db : Session) -> schemas.TokenResponse:
    new_token = extract_token(token_response)
    existing_token = db.query(Token).filter(Token.access_token == new_token.access_token).first()
    if existing_token:
        db.delete(existing_token)
    db.add(new_token)
    db.commit()
    db.refresh(new_token)
    return token_response.model_dump()

def process_activities(response, runner_id, seen_strava_ids_db):
    """Processes activity data, adding runner_id and filtering."""

    activities = []
    for run in response:
        activity_data = {k: v for k, v in run.items() if k in schemas.AthleteActivity.model_fields}
        activity_data['athlete_id'] = runner_id

        # Directly assign the map dictionary if it exists
        if 'map' in run:
            activity_data['map'] = run['map']

        activity = schemas.AthleteActivity.model_construct(**activity_data)
        activities.append(activity)

    activities_to_insert = [
        AthleteActivityDB(**activity.model_dump())
        for activity in activities
        if activity.id is not None and activity.id not in seen_strava_ids_db
    ]

    seen_strava_ids_db.update(activity.id for activity in activities if activity.id is not None)

    return activities, activities_to_insert