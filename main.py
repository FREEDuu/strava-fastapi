from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Body
from sqlalchemy import create_engine, MetaData, select
from sqlalchemy.ext.automap import automap_base
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Callable, AsyncGenerator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, and_, between, cast, DateTime
from fastapi import FastAPI, HTTPException, Depends, Query
import multiprocessing

from typing import List
import requests
from sqlalchemy import select, and_
import schemas
from sqlalchemy.exc import IntegrityError
from database import get_db, Runner, Activity
from dotenv import load_dotenv
import os 
import json
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

client_id = os.getenv("client_id")
client_secret = os.getenv("client_secret")
# Initialize FastAPI app
app = FastAPI()


URL = f'https://www.strava.com/oauth/token?client_id={client_id}&client_secret={client_secret}&grant_type=authorization_code'

origins = [
    "http://127.0.0.1:5174/home",  # Example: Your React app's URL
    "http://127.0.0.1:5174",  # Example: Your React app's URL
    "http://127.0.0.1:5174/login",  # Example: Your React app's URL
    # ... other origins
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (INSECURE FOR PRODUCTION)
    allow_credentials=True, # Only if you need credentials
    allow_methods=["*"],    # Allow all methods
    allow_headers=["*"],    # Allow all headers
)

@app.get("/runners/", response_model=List[schemas.Runner])
def get_runners(db: Session = Depends(get_db)):
    return db.execute(select(Runner)).scalars().all()

@app.get("/runners/{runner_id}", response_model=schemas.Runner)
def get_runner(runner_id: int, db: Session = Depends(get_db)):
    runner = db.execute(
        select(Runner).filter(Runner.id == runner_id)
    ).scalar_one_or_none()
    if not runner:
        raise HTTPException(status_code=404, detail="Runner not found")
    return runner

@app.get("/runners/{runner_id}/activities", response_model=List[schemas.Activity])
def get_runner_activities(runner_id: int, db: Session = Depends(get_db)):
    activities = db.execute(
        select(Activity).filter(Activity.runner_key == runner_id)
    ).scalars().all()
    return activities

@app.get("/activities/", response_model=List[schemas.Activity])
def get_activities(db: Session = Depends(get_db)):
    return db.execute(select(Activity)).scalars().all()

@app.get("/activities/{activity_id}", response_model=schemas.Activity)
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = db.execute(
        select(Activity).filter(Activity.id == activity_id)
    ).scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity

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
    
@app.post("/create_user/")
async def create_user(request: schemas.CreateUserRequest, db: Session = Depends(get_db)):
    print(f"Strava AUTH")

    try:
        strava_url = URL
        strava_data = schemas.CreateUserRequest(code=request.code) 
        response = await send_data_to_third_party(strava_data, strava_url)
        print(response)
        response_auth = schemas.StravaAuth(access_token=response['access_token'],
                                           refresh_token=response['refresh_token'],
                                           username= response['athlete']['username'],
                                           city=response['athlete']['city'],
                                           state=response['athlete']['state'],
                                           profile_image=response['athlete']['profile'],
                                           expires_at=response['expires_at'],)
        existing_runner = db.query(Runner).filter(Runner.username == response_auth.username).first()
        p = multiprocessing.Process(target=fetch_and_save_activities_process, args=(response_auth.access_token, existing_runner.id, str(DATABASE_URL)))
        p.start()
        if existing_runner:
            db.refresh(existing_runner) 
            existing_runner.access_token = response_auth.access_token
            existing_runner.refresh_token = response_auth.refresh_token
            
            print(f"Before commit: {existing_runner.access_token}, {existing_runner.refresh_token}")
            print(f"Before commit: {response_auth.access_token}, {response_auth.refresh_token}")
            
            db.flush()  # Ensure changes are staged before commit
            db.commit()
    
            print(f"After commit: {existing_runner.access_token}, {existing_runner.refresh_token}")
            
            db.refresh(existing_runner)  # Refresh object to load latest values
        else:
            new_runner = Runner(username = response_auth.username,
                                access_token = response_auth.access_token,
                                refresh_token = response_auth.refresh_token)
            db.add(new_runner)
            db.commit()
            db.refresh(new_runner)

        return response_auth.model_dump()
    except IntegrityError: 
        db.rollback()
        raise HTTPException(status_code=400, detail="Code already exists") # or other appropriate error message
    except HTTPException as e: 
        raise
    except Exception as e:
        db.rollback()
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/auth_runner_activities/{runner_username}/{runner_access}", response_model=List[schemas.Activity])  # Return a list of Activities
def get_activities(runner_username: str, runner_access: str, db: Session = Depends(get_db)):
    try:
        activities = db.execute(
            select(Activity).join(Runner).filter(
                and_(
                    Runner.username == runner_username,
                    Runner.access_token == runner_access 
                )
            )
        ).scalars().all()
        if not activities:
            raise HTTPException(status_code=404, detail="No activities found for this user with this access token")

        return activities  # Return the list of activities

    except Exception as e:  # Catch any potential exceptions
        print(f"An error occurred: {e}")  # Log the error for debugging
        raise HTTPException(status_code=500, detail="An error occurred while retrieving activities")
                

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

@app.get("/auth_runner_activities_limit/{runner_username}/{runner_access}", response_model=List[schemas.Activity])
def get_activities_limit(
    runner_username: str,
    runner_access: str,
    db: Session = Depends(get_db),
    limit: int = Query(10, description="Maximum number of activities to return"),  # Default limit of 10
):
    try:
        activities = db.execute(
            select(Activity).join(Runner).filter(
                and_(
                    Runner.username == runner_username,
                    Runner.access_token == runner_access
                )
            ).limit(limit)  # Add the limit
        ).scalars().all()

        if not activities:
            raise HTTPException(status_code=404, detail="No activities found for this user with this access token")

        return activities

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving activities")


@app.post("/auth_runner_activities_between/{runner_username}/{runner_access}", response_model=List[schemas.Activity]) # Changed to POST
def get_activities_between(
    runner_username: str,
    runner_access: str,
    db: Session = Depends(get_db),
    date_range: schemas.DateRange = Body(description="Date range for filtering activities"),  # Date range in the body
):
    try:
        query = select(Activity).join(Runner).filter(
            and_(
                Runner.username == runner_username,
                Runner.access_token == runner_access,
            )
        )

        if date_range.start_date:
            query = query.filter(cast(Activity.start_date_local, DateTime) >= cast(date_range.start_date, DateTime))

        if date_range.end_date:
            query = query.filter(cast(Activity.start_date_local, DateTime) <= cast(date_range.end_date, DateTime))

        activities = db.execute(query).scalars().all()

        if not activities:
            raise HTTPException(
                status_code=404,
                detail="No activities found for this user with this access token within the specified date range (if any)",
            )

        return activities

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving activities")