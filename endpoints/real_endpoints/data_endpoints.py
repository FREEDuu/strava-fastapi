import schemas
from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends, Body, status
from strava_api import send_data_to_third_party, fetch_and_save_activities_process
from database import get_db
import multiprocessing
from models import AthleteActivity, Athlete
from sqlalchemy import select
from utils.data_utils import get_user_from_access_token
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

    @app.post("/runner_activities", response_model=List[schemas.AthleteActivity]) 
    def get_activities(request: schemas.AccessTokenRequest, db: Session = Depends(get_db)):
        try:
            athlete_id = get_user_from_access_token(request.code, db)
            activities = db.execute(
                select(AthleteActivity).join(Athlete).filter(
                    and_(
                        AthleteActivity.athlete_id == athlete_id,
                    )
                )
            ).scalars().all()
            if not activities:
                raise HTTPException(status_code=404, detail="No activities found for this user with this access token")

            return activities  # Return the list of activities

        except Exception as e:  # Catch any potential exceptions
            print(f"An error occurred: {e}")  # Log the error for debugging
            raise HTTPException(status_code=500, detail="An error occurred while retrieving activities")
        
    @app.post("/runner_highlights_year", response_model=List[schemas.AthleteActivity])
    def get_longest_activities(
        request: schemas.AccessTokenRequestLimit,
        db: Session = Depends(get_db),
    ):
        try:
            athlete_id = get_user_from_access_token(request.code, db)
            activities = db.execute(
                select(AthleteActivity)
                .filter(
                    and_(
                        AthleteActivity.athlete_id == athlete_id,
                    )
                )
                .order_by(AthleteActivity.distance.desc()) 
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
    @app.post('/most_kudos', response_model=List[schemas.AthleteActivity])

    def most_kudos(
        request: schemas.AccessTokenRequestLimit,
        db: Session = Depends(get_db),
    ):
        try:
            athlete_id = get_user_from_access_token(request.code, db)
            activities = db.execute(
                select(AthleteActivity)
                .filter(
                    and_(
                        AthleteActivity.athlete_id == athlete_id,
                    )
                )
                .order_by(AthleteActivity.kudos_count.desc())  # Order by kudos count descending
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
    @app.post("/grouped_activities", response_model=List[schemas.GroupedActivities])
    def grouped_activities(
        request: schemas.AccessTokenRequest,
        db: Session = Depends(get_db),
    ):
        try:
            athlete_id = get_user_from_access_token(request.code, db)
            results = db.execute(
                select(
                    AthleteActivity.type.label("type_activity"),
                    func.count(AthleteActivity.id).label("activities_count")
                )
                .filter(
                    and_(
                        AthleteActivity.athlete_id == athlete_id,
                    )
                )
                .group_by(AthleteActivity.type)
                .order_by(func.count(AthleteActivity.id).desc())
            ).mappings().all()
            print(results)
            return results

        except Exception as e:
            print(f"An error occurred: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        
    @app.post("/runner_activities_csv", response_class=StreamingResponse)
    def get_activities_csv(request: schemas.AccessTokenRequest, db: Session = Depends(get_db)):
        try:
            athlete_id = get_user_from_access_token(request.code, db)
            activities = db.execute(
                select(AthleteActivity).filter(
                    and_(
                       AthleteActivity.athlete_id == athlete_id,

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
        request: schemas.AccessTokenRequest,
        db: Session = Depends(get_db),
    ):
        try:
            athlete_id = get_user_from_access_token(request.code, db)
            results = db.execute(
                select(
                    AthleteActivity.athlete_count.label("friend_count"),
                    func.count(AthleteActivity.id).label("activity_count")
                )
                .filter(
                    and_(
                        AthleteActivity.athlete_id == athlete_id,

                    )
                )
                .group_by(AthleteActivity.athlete_count)
                .order_by(func.count(AthleteActivity.id).desc())
            ).mappings().all()

            return results

        except Exception as e:
            print(f"An error occurred: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))