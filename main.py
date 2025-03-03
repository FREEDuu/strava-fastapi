from fastapi import FastAPI
from dotenv import load_dotenv
import os 
from middleware import add_middleware
from endpoints.real_endpoints.auth_endpoint import auth_endpoints
from endpoints.real_endpoints.data_endpoints import data_endpoints
load_dotenv()
client_id = os.getenv("client_id")
client_secret = os.getenv("client_secret")
DATABASE_URL = os.getenv("DATABASE_URL")
URL = f'https://www.strava.com/oauth/token?client_id={client_id}&client_secret={client_secret}&grant_type=authorization_code'

app = FastAPI()
add_middleware(app)
auth_endpoints(app, URL, DATABASE_URL)
data_endpoints(app)