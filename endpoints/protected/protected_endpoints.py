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

def add_protected(app, URL, DATABASE_URL):
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

    @app.post("/auth_runner_activities", response_model=List[schemas.Activity]) 
    def get_activities(request: schemas.AuthRunnerRequest, db: Session = Depends(get_db)):
        try:
            activities = db.execute(
                select(Activity).join(Runner).filter(
                    and_(
                        Runner.username == request.username,
                        Runner.access_token == request.access_token  
                    )
                )
            ).scalars().all()
            if not activities:
                raise HTTPException(status_code=404, detail="No activities found for this user with this access token")

            return activities  # Return the list of activities

        except Exception as e:  # Catch any potential exceptions
            print(f"An error occurred: {e}")  # Log the error for debugging
            raise HTTPException(status_code=500, detail="An error occurred while retrieving activities")

    @app.get("/auth_runner_activities_limit", response_model=List[schemas.Activity])
    def get_activities_limit(
        request: schemas.AuthRunnerLimitRequest,
        db: Session = Depends(get_db),
    ):
        try:
            activities = db.execute(
                select(Activity)
                .join(Runner)
                .filter(
                    and_(
                        Runner.username == request.username,
                        Runner.access_token == request.access_token
                    )
                )
                .limit(request.limit) 
            ).scalars().all()
            
            if not activities:
                raise HTTPException(
                    status_code=404,
                    detail="No activities found for this user with this access token"
                )
            
            return activities
            
        except HTTPException as he:
            # Re-raise HTTP exceptions as-is
            raise he
        except Exception as e:
            print(f"An error occurred: {e}")
            raise HTTPException(
                status_code=500,
                detail="An error occurred while retrieving activities"
            )

    @app.post("/auth_runner_activities_between/{runner_username}/{runner_access}", response_model=List[schemas.Activity])
    def get_activities_between(
        runner_username: str,
        runner_access: str,
        db: Session = Depends(get_db),
        date_range: schemas.DateRange = Body(description="Date range for filtering activities"),
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
        
    @app.post("/auth_runner_highlights_year", response_model=List[schemas.Activity])
    def get_longest_activities(
        request: schemas.AuthRunnerLimitRequest,
        db: Session = Depends(get_db),
    ):
        try:
            activities = db.execute(
                select(Activity)
                .join(Runner)
                .filter(
                    and_(
                        Runner.username == request.username,
                        Runner.access_token == request.access_token,
                    )
                )
                .order_by(Activity.distance.desc())  # Order by distance descending
                .limit(request.limit)
            ).scalars().all()

            if not activities:
                raise HTTPException(
                    status_code=404,
                    detail="No activities found"
                )

            return activities

        except HTTPException as he:
            raise he
        except Exception as e:
            print(f"An error occurred: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while retrieving activities: {str(e)}"
            )
        

    @app.post('/most_kudos', response_model=List[schemas.Activity])
    def most_kudos(
        request: schemas.AuthRunnerLimitRequest,
        db: Session = Depends(get_db),
    ):
        try:
            activities = db.execute(
                select(Activity)
                .join(Runner)
                .filter(
                    and_(
                        Runner.username == request.username,
                        Runner.access_token == request.access_token,
                    )
                )
                .order_by(Activity.kudos_count.desc())  # Order by kudos count descending
                .limit(request.limit)
            ).scalars().all()

            if not activities:
                raise HTTPException(
                    status_code=404,
                    detail="No activities found"
                )

            return activities

        except HTTPException as he:
            raise he
        except Exception as e:
            print(f"An error occurred: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while retrieving activities: {str(e)}"
            )

    @app.post("/grouped_activities", response_model=List[schemas.GroupedActivity])
    def grouped_activities(
        request: schemas.AuthRunnerRequest,
        db: Session = Depends(get_db),
    ):
        try:
            results = db.execute(
                select(
                    Activity.type.label("type_activity"),
                    func.count(Activity.id).label("activities_count")
                )
                .join(Runner)
                .filter(
                    and_(
                        Runner.username == request.username,
                        Activity.runner_key == Runner.id,
                    )
                )
                .group_by(Activity.type)
                .order_by(func.count(Activity.id).desc())
            ).mappings().all()

            return results

        except Exception as e:
            print(f"An error occurred: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
