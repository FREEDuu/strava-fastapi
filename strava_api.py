import requests
import schemas
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from database import Activity

async def send_data_to_third_party(data: schemas.CreateUserRequest, third_party_url: str):
    print(f"Strava AUTH {data.code}")
    try:
        response = requests.post(third_party_url, params=data.model_dump())
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print(f"Successfully sent data to third party: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to third party: {e}")
        # Handle the error appropriately (e.g., logging, retrying, etc.)
        return {'Error' : 'Something wrong with validation'}
    
def fetch_and_save_activities_process(access_token: str, runner_key: int, db_url: str): # new function for the process
    engine = create_engine(db_url, echo=False, future=True)
    with Session(engine) as db: # sync session inside the process
        page = 0
        seen_strava_ids_db = set() # Set to track strava_ids already in the database

        # Efficiently pre-load existing strava_ids from the database into the set
        existing_strava_ids_query = select(Activity.id).where(Activity.runner_key == runner_key)
        for strava_id in db.scalars(existing_strava_ids_query):
            seen_strava_ids_db.add(strava_id)
        while True:
            response = requests.get(
                url=f'https://www.strava.com/api/v3/athlete/activities?access_token={access_token}&per_page=200&page={page+1}',
            )

            data = response.json()
            if not data:
                break

            page += 1
            print(response.json())
            activities = [
                schemas.Activity.model_construct(
                    **{k: v for k, v in run.items() if k in schemas.Activity.model_fields}
                ) for run in data
            ]

            activities_to_insert = []

            for activity in activities:
                strava_id = activity.id

                if strava_id is not None and strava_id not in seen_strava_ids_db:  # Check against DB and current batch
                    seen_strava_ids_db.add(strava_id)  # Mark as seen (in DB or current batch)

                    activity_data = activity.model_dump()
                    activity_to_insert = Activity(**activity_data, runner_key=runner_key)
                    activities_to_insert.append(activity_to_insert)

            try:
                db.add_all(activities_to_insert)
                db.commit()
                print(f"Process: Page {page} committed with {len(activities_to_insert)} unique activities.")

            except Exception as e:
                print(e)

def fetch_and_save_activities_process_partial(access_token: str, runner_key: int, db_url: str): # new function for the process
    engine = create_engine(db_url, echo=False, future=True)
    with Session(engine) as db: # sync session inside the process
        page = 0
        seen_strava_ids_db = set() # Set to track strava_ids already in the database

        # Efficiently pre-load existing strava_ids from the database into the set
        existing_strava_ids_query = select(Activity.id).where(Activity.runner_key == runner_key)
        for strava_id in db.scalars(existing_strava_ids_query):
            seen_strava_ids_db.add(strava_id)
       
        response = requests.get(
            url=f'https://www.strava.com/api/v3/athlete/activities?access_token={access_token}&per_page=200&page={page+1}',
        )

        data = response.json()
        if not data:
            return

        page += 1
        print(response.json())
        activities = [
            schemas.Activity.model_construct(
                **{k: v for k, v in run.items() if k in schemas.Activity.model_fields}
            ) for run in data
        ]

        activities_to_insert = []

        for activity in activities:
            strava_id = activity.id

            if strava_id is not None and strava_id not in seen_strava_ids_db:  # Check against DB and current batch
                seen_strava_ids_db.add(strava_id)  # Mark as seen (in DB or current batch)

                activity_data = activity.model_dump()
                activity_to_insert = Activity(**activity_data, runner_key=runner_key)
                activities_to_insert.append(activity_to_insert)

        try:
            db.add_all(activities_to_insert)
            db.commit()
            print(f"Process: Page {page} committed with {len(activities_to_insert)} unique activities.")

        except Exception as e:
            print(e)