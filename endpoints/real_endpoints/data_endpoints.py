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
from datetime import datetime

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
                .order_by(AthleteActivity.start_date_local)
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
        
    @app.post("/activity_summary", response_model=schemas.ActivitySummary)
    def get_activity_summary(request: schemas.YearRequest,
            db: Session = Depends(get_db)
        ):
        try:
            year = request.year
            athlete_id = get_user_from_access_token(request.code, db)

            activities = db.execute(
                select(AthleteActivity)
                .filter(AthleteActivity.athlete_id == athlete_id)
            ).scalars().all()

            filtered_activities = []
            for activity in activities:
                try:
                    date_str = activity.start_date_local.replace('Z', '+00:00')
                    activity_datetime = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
                    activity_year = activity_datetime.year
                    if activity_year == year:
                        filtered_activities.append(activity)
                except ValueError:
                    # Handle cases where the string is not a valid ISO format
                    print(f"Invalid date format: {activity.start_date_local}")
                    continue

            if not filtered_activities:
                raise HTTPException(status_code=404, detail="No activities found for the specified athlete and year.")

            if not filtered_activities:
                        raise HTTPException(status_code=404, detail="No activities found for the specified athlete and year.")

            total_activities = len(filtered_activities)
            total_elevation_gain = sum(activity.total_elevation_gain for activity in filtered_activities)
            total_moving_time = sum(activity.moving_time for activity in filtered_activities)
            total_distance = sum(activity.distance for activity in filtered_activities)

            return schemas.ActivitySummary(
                total_activities=total_activities,
                total_elevation_gain=total_elevation_gain,
                total_moving_time=total_moving_time,
                total_distance=total_distance
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/github_contribution", response_model=List[schemas.GitHubContribution])
    def get_github_contribution(request: schemas.YearRequest, db: Session = Depends(get_db)):
        try:
            athlete_id = get_user_from_access_token(request.code, db)
            activities = db.execute(
                select(AthleteActivity)
                .filter(
                    and_(
                        AthleteActivity.athlete_id == athlete_id
                    )
                    )).scalars().all()

            date_kudos_map = {}  # Dictionary to store date and total kudos

            for activity in activities:
                try:
                    date_str = activity.start_date_local.replace('Z', '+00:00')
                    activity_datetime = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
                    date_key = activity_datetime.strftime("%Y-%m-%d")  # Extract date as string
                    if int(date_key.split('-')[0]) == request.year:
                        if date_key in date_kudos_map:
                            date_kudos_map[date_key] += activity.kudos_count
                        else:
                            date_kudos_map[date_key] = activity.kudos_count

                except ValueError:
                    print(f"Invalid date format: {activity.start_date_local}")
                    continue

            result = [schemas.GitHubContribution(date_activity=date, kudos_count=kudos) for date, kudos in date_kudos_map.items()]
            result.sort(key=lambda x: x.date_activity) #sort result by date

            return result

        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            db.close()