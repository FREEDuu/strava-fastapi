from fastapi import FastAPI
from dotenv import load_dotenv
import os 
from middleware import add_middleware
from endpoints.unprotected.unprotected_endpoints import add_unprotected
from endpoints.protected.protected_endpoints import add_protected
from endpoints.protected.charts_endpoint import add_charts_endpoint

load_dotenv()
client_id = os.getenv("client_id")
client_secret = os.getenv("client_secret")
DATABASE_URL = os.getenv("DATABASE_URL")
URL = f'https://www.strava.com/oauth/token?client_id={client_id}&client_secret={client_secret}&grant_type=authorization_code'

app = FastAPI()
add_middleware(app)
add_unprotected(app)
add_protected(app, URL, DATABASE_URL)
add_charts_endpoint(app)
