import schemas
from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends, Body, status
from strava_api import send_data_to_third_party, fetch_and_save_activities_process, fetch_and_save_activities_process_partial
from database import get_db, Runner, Activity
import multiprocessing
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_, cast, DateTime
from typing import List
from fastapi import HTTPException, Depends
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

def auth_endpoints(app, URL, DATABASE_URL):
    
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

            if existing_runner:

                existing_activity = db.query(Activity).filter(Activity.runner_key == existing_runner.id).first()
                if existing_activity:
                    p = multiprocessing.Process(target=fetch_and_save_activities_process_partial, args=(response_auth.access_token, existing_runner.id, str(DATABASE_URL)))
                    p.start()
                else:
                    p = multiprocessing.Process(target=fetch_and_save_activities_process, args=(response_auth.access_token, existing_runner.id, str(DATABASE_URL)))
                    p.start()
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
                p = multiprocessing.Process(target=fetch_and_save_activities_process, args=(response_auth.access_token, existing_runner.id, str(DATABASE_URL)))
                p.start()
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
