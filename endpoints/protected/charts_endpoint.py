import schemas
from database import get_db, Runner, Activity
from fastapi import HTTPException, Depends, Body
from sqlalchemy import and_, select, func, cast, DateTime
from sqlalchemy.orm import Session
from typing import Literal
from datetime import datetime, timedelta

def get_week_range(date_str: str) -> str:
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    monday = date_obj - timedelta(days=date_obj.weekday())
    sunday = monday + timedelta(days=6)
    return f"{monday.strftime('%Y-%m-%d')} to {sunday.strftime('%Y-%m-%d')}"

def format_month(date_str: str) -> str:
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    return date_obj.strftime('%B %Y')  

def format_day(date_str: str) -> str:
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    return date_obj.strftime('%d')  

def add_charts_endpoint(app):
    @app.post("/gh_chart/{runner_username}/{runner_access}", response_model=schemas.ActivityGithub)
    def gh_chart(
        runner_username: str,
        runner_access: str,
        db: Session = Depends(get_db),
        date_range: schemas.DateRange = Body(description="Date range for filtering activities"),
    ):
        try:
            # Query to count activities per day
            query = (
                select(
                    func.date(Activity.start_date_local).label('activity_date'),
                    func.count(Activity.id).label('activity_count')
                )
                .join(Runner)
                .filter(
                    and_(
                        Runner.username == runner_username,
                        Runner.access_token == runner_access,
                    )
                )
                .group_by(func.date(Activity.start_date_local))
            )

            if date_range.start_date:
                query = query.filter(cast(Activity.start_date_local, DateTime) >= cast(date_range.start_date, DateTime))

            if date_range.end_date:
                query = query.filter(cast(Activity.start_date_local, DateTime) <= cast(date_range.end_date, DateTime))

            results = db.execute(query).all()

            if not results:
                raise HTTPException(
                    status_code=404,
                    detail="No activities found for this user with this access token within the specified date range"
                )

            # Convert to GitHub-like format
            activity_data = {}
            
            # Function to determine activity level based on count
            def get_activity_level(count: int) -> int:
                if count == 0:
                    return 0
                elif count == 1:
                    return 1
                elif count <= 3:
                    return 2
                elif count <= 5:
                    return 3
                else:
                    return 4

            # Format the data
            for date_obj, count in results:
                date_str = date_obj.strftime('%Y-%m-%d')
                activity_data[date_str] = {"level": get_activity_level(count)}

            return schemas.ActivityGithub(data=activity_data)

        except HTTPException as he:
            raise he
        except Exception as e:
            print(f"An error occurred: {e}")
            raise HTTPException(status_code=500, detail="An error occurred while retrieving activities")
    

    @app.get("/main_chart/{runner_username}/{runner_access}/{limit}/{period}", response_model=schemas.GroupedActivities)
    def main_chart(
            runner_username: str,
            runner_access: str,
            limit: int,
            period: Literal['day', 'week', 'month'],
            db: Session = Depends(get_db),
        ):
            try:
                # Use distinct to prevent duplicates
                base_query = (
                select((Activity))
                .join(Runner)
                .filter(
                    and_(
                        Runner.username == runner_username,
                        Runner.access_token == runner_access,
                    )
                )
                .order_by(Activity.start_date_local.desc())
                .limit(limit)
            )

                activities = db.execute(base_query).scalars().all()

                if not activities:
                    raise HTTPException(
                        status_code=404,
                        detail="No activities found"
                    )

                # Group activities based on period
                grouped_data = {}
                print(activities)
                for activity in activities: 
                    # Get the date part of the string (before the 'T')
                    date_str = activity.start_date_local.split('T')[0]
                    
                    if period == 'day':
                        # Use the day number
                        group_key = format_day(date_str)
                    
                    elif period == 'week':
                        # Use date range for the week
                        group_key = get_week_range(date_str)
                    
                    elif period == 'month':
                        # Use month name and year
                        group_key = format_month(date_str)

                    # Initialize group if it doesn't exist
                    if group_key not in grouped_data:
                        grouped_data[group_key] = []

                    # Add activity to its group
                    grouped_data[group_key].append(activity)

                return schemas.GroupedActivities(
                    period=period,
                    groups=grouped_data
                )

            except HTTPException as he:
                raise he
            except Exception as e:
                print(f"An error occurred: {e}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"An error occurred while retrieving activities: {str(e)}"
                )