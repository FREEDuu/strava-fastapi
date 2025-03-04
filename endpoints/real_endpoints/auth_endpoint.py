from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends
from strava_api import send_data_to_third_party, fetch_and_save_activities_process
from database import get_db
from models import Athlete, Token
import multiprocessing
import schemas
from utils.data_utils import save_athlete, save_refresh_token

def auth_endpoints(app, URL, DATABASE_URL):
    
    @app.post("/create_refresh_user/")
    async def create_user(request: schemas.AccessTokenRequest, db: Session = Depends(get_db)) -> schemas.TokenResponse:

        try:
            strava_data = schemas.AccessTokenRequest(code=request.code) 
            response = await send_data_to_third_party(strava_data, URL)
            athlete_instance = schemas.AthleteBase(**response["athlete"])
            token_response = schemas.TokenResponse(**response)    

            existing_runner = db.query(Athlete).filter(Athlete.username == athlete_instance.username).first()

            if not existing_runner:
                get_activities_process = multiprocessing.Process(
                    target=fetch_and_save_activities_process, args=(
                                                                token_response.access_token, 
                                                                athlete_instance.id, 
                                                                str(DATABASE_URL)))
                get_activities_process.start()

                save_athlete(athlete_instance, db)
            return save_refresh_token(token_response, db)
            
        except HTTPException as e: 
            raise
        except Exception as e:
            db.rollback()
            print(f"An unexpected error occurred: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.post("/refresh_activities/")
    async def refresh_activities(request: schemas.AccessTokenRequest, db: Session = Depends(get_db)):

        try:
            existing_token = db.query(Token).filter(Token.access_token == request.code).first()

            if existing_token:
                get_activities_process = multiprocessing.Process(
                    target=fetch_and_save_activities_process, args=(
                                                                existing_token.access_token, 
                                                                existing_token.athlete_id,
                                                                str(DATABASE_URL)))
                get_activities_process.start()

                return {"message": "Activities are being refreshed"}
            
            raise HTTPException(status_code=400, detail="Token does not exist")
        except HTTPException as e: 
            raise
        except Exception as e:
            db.rollback()
            print(f"An unexpected error occurred: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.post("/refresh_token/")
    async def refresh_token(request: schemas.AccessTokenRequest, db: Session = Depends(get_db)):
        pass
    #TODO: Implement the refresh token endpoint
    #This endpoint should take a refresh token and return a new access token.

    