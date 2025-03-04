import requests
import schemas
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import AthleteActivity
from utils.data_utils import process_activities

BASE_URL = 'https://www.strava.com/api/v3/athlete/activities?access_token='
PAGES_URL = '&per_page=200&page=' 

async def send_data_to_third_party(data: schemas.AccessTokenRequest, third_party_url: str):
    print(f"Strava AUTH {data.code}")
    try:
        response = requests.post(third_party_url, params=data.model_dump())
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        return response.json()
    except requests.exceptions.RequestException as e:
        return {'Error' : 'Something wrong with validation'}
    
def fetch_and_save_activities_process(token: str, athlete_id: int, db_url: str): # new function for the process
    engine = create_engine(db_url, echo=False, future=True)
    with Session(engine) as db: # sync session inside the process
        page = 0

        seen_strava_ids_db = set() # Set to track strava_ids already in the database
        existing_strava_ids_query = select(AthleteActivity.id).where(AthleteActivity.athlete_id == athlete_id)
        for strava_id in db.scalars(existing_strava_ids_query):
            seen_strava_ids_db.add(strava_id)

        while True:
            response = requests.get(
                url=f'{BASE_URL}{token}{PAGES_URL}{page+1}',
            ).json()

            if not response:
                break

            page += 1

            activities, activities_to_insert = process_activities(response, athlete_id, seen_strava_ids_db)

            seen_strava_ids_db.update(activity.id for activity in activities if activity.id is not None)

            try:
                db.add_all(activities_to_insert)
                db.commit()
                print(f"Process: Page {page} committed with {len(activities_to_insert)} unique activities.")

            except Exception as e:
                print(e)

