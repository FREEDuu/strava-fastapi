import requests
from schemas import Activity

async def get_activities():
    
    page = 0
    while(True):

        response = requests.get(
            url = f'https://www.strava.com/api/v3/athlete/activities?access_token=fde028047a336c8acaf26f6768b72c1cfce05b4b&per_page={200}&page={page+1}',
        )
        if not response.json():
            break
        page += 1
        activities = [Activity.model_construct(**{k: v for k, v in run.items() if k in Activity.model_fields}) for run in response.json()]
        return activities
