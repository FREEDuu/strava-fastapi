from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends
import schemas
from typing import List
from database import get_db, Runner, Activity
from sqlalchemy import select

def add_unprotected(app):

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
