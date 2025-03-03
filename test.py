import requests

url = "http://127.0.0.1:8000/runner_activities_csv"  # Replace with your URL
data = {"username": "filbullo", "access_token": "8528c053f219241a05a68d9dd0560c541791dcd3"}

response = requests.post(url, json=data)

if response.status_code == 200:
    with open("downloaded_activities.csv", "wb") as f:
        f.write(response.content)
    print("CSV downloaded successfully.")
else:
    print(f"Error: {response.status_code}")