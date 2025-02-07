import schemas
from typing import List
from database import get_db, Runner, Activity
from fastapi import HTTPException, Depends, Body
from sqlalchemy import and_, select, func, cast, DateTime
from sqlalchemy.orm import Session
from typing import Literal
from datetime import datetime, timedelta, date
import sqlalchemy

def get_years_to_analyze(current_year: int, num_years: int) -> List[int]:
    """Return a list of years to analyze, starting from current_year going backwards."""
    return list(range(current_year, current_year - num_years, -1))

def get_daily_activities(db: Session, runner_username: str, runner_access: str, year: int):
    """Get all activities for a specific year, ordered by date."""
    return db.execute(
        select(
            func.date(Activity.start_date_local).label('activity_date'),
            func.sum(Activity.distance).label('distance'),
            func.sum(Activity.total_elevation_gain).label('elevation_gain')
        )
        .join(Runner)
        .filter(
            and_(
                Runner.username == runner_username,
                Runner.access_token == runner_access,
                # Changed this line to cast the string to timestamp first
                func.date_part('year', func.cast(Activity.start_date_local, sqlalchemy.DateTime)) == year
            )
        )
        .group_by(func.date(Activity.start_date_local))
        .order_by('activity_date')
    ).all()

def get_date_range(latest_date: datetime, period: str, activity_count: int, db: Session, runner_username: str, runner_access: str) -> list[datetime]:
    """
    Generate a list of dates that spans from the latest activity to cover all dates needed to include
    the specified number of activities.
    """
    # First, get the date of the Nth activity to determine our date range
    oldest_activity = db.execute(
        select(Activity)
        .join(Runner)
        .filter(
            and_(
                Runner.username == runner_username,
                Runner.access_token == runner_access,
            )
        )
        .order_by(Activity.start_date_local.desc())
        .offset(activity_count - 1)
        .limit(1)
    ).scalar_one_or_none()

    if not oldest_activity:
        # If we don't have enough activities, get the oldest one we have
        oldest_activity = db.execute(
            select(Activity)
            .join(Runner)
            .filter(
                and_(
                    Runner.username == runner_username,
                    Runner.access_token == runner_access,
                )
            )
            .order_by(Activity.start_date_local.asc())
            .limit(1)
        ).scalar_one_or_none()

    if not oldest_activity:
        return [latest_date]  # Return just today if no activities found

    # Parse the oldest activity date
    oldest_date = datetime.strptime(oldest_activity.start_date_local.split('T')[0], '%Y-%m-%d')
    
    if period == 'day':
        # Generate all dates between oldest and latest
        days_between = (latest_date - oldest_date).days + 1
        return [latest_date - timedelta(days=i) for i in range(days_between)]
    
    elif period == 'week':
        # Start from the Monday of the latest week
        latest_monday = latest_date - timedelta(days=latest_date.weekday())
        # Start from the Monday of the oldest week
        oldest_monday = oldest_date - timedelta(days=oldest_date.weekday())
        weeks_between = ((latest_monday - oldest_monday).days // 7) + 1
        return [latest_monday - timedelta(weeks=i) for i in range(weeks_between)]
    
    else:  # month
        # Start from the first of the latest month
        months = []
        current_date = latest_date.replace(day=1)
        oldest_first = oldest_date.replace(day=1)
        
        while current_date >= oldest_first:
            months.append(current_date)
            # Move to previous month
            if current_date.month == 1:
                current_date = current_date.replace(year=current_date.year - 1, month=12)
            else:
                current_date = current_date.replace(month=current_date.month - 1)
        
        return sorted(months)

def format_period_key(date: datetime, period: str) -> str:
    """Format the date according to the period type."""
    if period == 'day':
        return date.strftime('%Y-%m-%d')
    elif period == 'week':
        monday = date
        sunday = monday + timedelta(days=6)
        return f"{monday.strftime('%Y-%m-%d')} to {sunday.strftime('%Y-%m-%d')}"
    else:  # month
        return date.strftime('%B %Y')

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
    

    @app.get("/main_chart/{runner_username}/{runner_access}/{limit}/{period}", response_model=schemas.GroupedMetrics)
    def main_chart(
            runner_username: str,
            runner_access: str,
            limit: int,
            period: Literal['day', 'week', 'month'],
            db: Session = Depends(get_db),
        ):
        try:
            # Get the most recent activity to determine the date range
            latest_activity = db.execute(
                select(Activity)
                .join(Runner)
                .filter(
                    and_(
                        Runner.username == runner_username,
                        Runner.access_token == runner_access,
                    )
                )
                .order_by(Activity.start_date_local.desc())
                .limit(1)
            ).scalar_one_or_none()

            if not latest_activity:
                raise HTTPException(
                    status_code=404,
                    detail="No activities found"
                )

            # Get the date ranges we want to show
            latest_date = datetime.strptime(latest_activity.start_date_local.split('T')[0], '%Y-%m-%d')
            date_ranges = get_date_range(latest_date, period, limit, db, runner_username, runner_access)

            # Initialize result dictionary with zeros for all periods
            grouped_metrics = {}
            for date in date_ranges:
                key = format_period_key(date, period)
                grouped_metrics[key] = {
                    "total_distance": 0.0,
                    "total_elevation_gain": 0.0
                }

            # Build date filtering based on period
            for i in range(len(date_ranges)):
                start_date = date_ranges[i]
                end_date = None
                
                if period == 'day':
                    end_date = start_date + timedelta(days=1)
                elif period == 'week':
                    end_date = start_date + timedelta(days=7)
                else:  # month
                    if start_date.month == 12:
                        end_date = start_date.replace(year=start_date.year + 1, month=1)
                    else:
                        end_date = start_date.replace(month=start_date.month + 1)

                # Query for aggregated metrics in this period
                metrics = db.execute(
                    select(
                        func.sum(Activity.distance).label('total_distance'),
                        func.sum(Activity.total_elevation_gain).label('total_elevation_gain')
                    )
                    .join(Runner)
                    .filter(
                        and_(
                            Runner.username == runner_username,
                            Runner.access_token == runner_access,
                            Activity.start_date_local >= start_date.strftime('%Y-%m-%d'),
                            Activity.start_date_local < end_date.strftime('%Y-%m-%d')
                        )
                    )
                ).first()

                if metrics and metrics.total_distance is not None:
                    key = format_period_key(start_date, period)
                    grouped_metrics[key] = {
                        "total_distance": round(metrics.total_distance / 1000, 2),  # Convert to kilometers
                        "total_elevation_gain": round(metrics.total_elevation_gain, 2)
                    }

            return schemas.GroupedMetrics(
                period=period,
                metrics=grouped_metrics
            )

        except HTTPException as he:
            raise he
        except Exception as e:
            print(f"An error occurred: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"An error occurred while retrieving activities: {str(e)}"
            )
    @app.get("/cumulative_chart/{runner_username}/{runner_access}/{num_years}", response_model=schemas.YearlyCumulativeMetrics)
    def cumulative_chart(
            runner_username: str,
            runner_access: str,
            num_years: int,
            db: Session = Depends(get_db),
        ):
        try:
            # Get current year and list of years to analyze
            current_year = datetime.now().year
            years_to_analyze = get_years_to_analyze(current_year, num_years)
            
            # Initialize result dictionary
            yearly_metrics = {}
            
            for year in years_to_analyze:
                # Get all activities for this year
                activities = get_daily_activities(db, runner_username, runner_access, year)
                
                if not activities:
                    # Initialize the year with zeros if no activities
                    start_date = date(year, 1, 1)
                    end_date = date(year, 12, 31)
                    daily_metrics = {}
                    
                    current_date = start_date
                    while current_date <= end_date:
                        daily_metrics[current_date.strftime('%Y-%m-%d')] = {
                            "cumulative_distance": 0.0,
                            "cumulative_elevation_gain": 0.0
                        }
                        current_date += timedelta(days=1)
                    
                    yearly_metrics[str(year)] = daily_metrics
                    continue
                
                # Initialize cumulative values
                cumulative_distance = 0.0
                cumulative_elevation = 0.0
                daily_metrics = {}
                
                # Start from January 1st
                current_date = date(year, 1, 1)
                activity_index = 0
                
                # Go through each day of the year
                while current_date <= date(year, 12, 31):
                    # Check if we have an activity for this day
                    if (activity_index < len(activities) and 
                        activities[activity_index].activity_date == current_date):
                        # Add today's activities to cumulative totals
                        cumulative_distance += activities[activity_index].distance / 1000  # Convert to km
                        cumulative_elevation += activities[activity_index].elevation_gain
                        activity_index += 1
                    
                    # Store the cumulative values for this day
                    daily_metrics[current_date.strftime('%Y-%m-%d')] = {
                        "cumulative_distance": round(cumulative_distance, 2),
                        "cumulative_elevation_gain": round(cumulative_elevation, 2)
                    }
                    
                    current_date += timedelta(days=1)
                
                yearly_metrics[str(year)] = daily_metrics

            return schemas.YearlyCumulativeMetrics(
                years=yearly_metrics
            )

        except Exception as e:
            print(f"An error occurred: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while retrieving cumulative metrics: {str(e)}"
            )
