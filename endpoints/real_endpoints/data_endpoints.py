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
from utils.file_util import generate_csv
from fastapi.responses import StreamingResponse
import io

def data_endpoints(app):

    @app.post("/runner_activities", response_model=List[schemas.Activity]) 
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
        
    @app.post("/runner_highlights_year", response_model=List[schemas.Activity])
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
        
    @app.post("/runner_activities_csv", response_class=StreamingResponse)
    def get_activities_csv(request: schemas.AuthRunnerRequest, db: Session = Depends(get_db)):
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

            csv_content = generate_csv(activities)

            return StreamingResponse(
                io.StringIO(csv_content),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=runner_activities.csv"}
            )

        except Exception as e:
            print(f"An error occurred: {e}")
            raise HTTPException(status_code=500, detail="An error occurred while retrieving activities")
        
    @app.post("/friend_run", response_model=List[schemas.FriendActivity])
    def friend_run(
        request: schemas.AuthRunnerRequest,
        db: Session = Depends(get_db),
    ):
        try:
            results = db.execute(
                select(
                    Activity.athlete_count.label("friend_count"),
                    func.count(Activity.id).label("activity_count")
                )
                .join(Runner)
                .filter(
                    and_(
                        Runner.username == request.username,
                        Activity.runner_key == Runner.id,
                    )
                )
                .group_by(Activity.athlete_count)
                .order_by(func.count(Activity.id).desc())
            ).mappings().all()

            return results

        except Exception as e:
            print(f"An error occurred: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))