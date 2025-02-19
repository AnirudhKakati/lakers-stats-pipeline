import json
import boto3
import requests
from datetime import datetime

#S3 bucket details
BUCKET_NAME = "lakers-stats-pipeline-bucket"
S3_KEY = "schedule/lakers_schedule.json"

#ESPN API URL for Lakers schedule
LAKERS_ID = 13
ESPN_SCHEDULE_URL = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{LAKERS_ID}/schedule"

def fetch_lakers_schedule():
    """
    Fetches the Lakers' regular season schedule from ESPN's API.

    This function:
    - Sends a GET request to the ESPN API to retrieve the Lakers' schedule.
    - Filters out non-regular season games.
    - Parses the game date/time and converts it to UTC.
    - Returns a list of games with their game_id and game_time in ISO format.

    Returns:
        list[dict]: A list of dictionaries where each dictionary contains:
            - game_id (str): The unique game identifier from ESPN.
            - game_time (str): The UTC date and time of the game in ISO format.

    Raises:
        requests.RequestException: If the API request fails.
    """

    try:
        response = requests.get(ESPN_SCHEDULE_URL)
        response.raise_for_status()
        data = response.json()
        
        games = []
        for event in data.get('events', []):
            if event.get('seasonType', {}).get("name") != 'Regular Season':
                continue  #we ignore non-regular season games
            
            game_time = datetime.strptime(event['date'], '%Y-%m-%dT%H:%MZ')  #convert to UTC
            
            games.append({
                'game_id': event['id'],
                'game_time': game_time.isoformat() + 'Z'  #ISO format
            })
        
        return games if games else None
    
    except requests.RequestException as e:
        print(f"Error fetching schedule: {e}")
        return None

def upload_to_s3(data, bucket, key):
    """
    Uploads the given data to an S3 bucket as a JSON file.

    This function:
    - Converts the given data to JSON format.
    - Uploads the JSON file to the specified S3 bucket under the given key.
    - Sets the content type to `application/json`.

    Parameters:
        data (dict): The data to be uploaded to S3.
        bucket (str): The name of the S3 bucket.
        key (str): The S3 object key (file path within the bucket).

    Raises:
        Exception: If there is an error uploading the file to S3.
    """

    s3 = boto3.client('s3')
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data, indent=4),
            ContentType='application/json'
        )
        print(f"Successfully uploaded schedule to s3://{bucket}/{key}")
    except Exception as e:
        print(f"Error uploading to S3: {e}")

def lambda_handler(event, context):
    """
    AWS Lambda handler function to fetch the Lakers schedule and upload it to S3.

    This function:
    - Calls `fetch_lakers_schedule()` to retrieve the latest schedule.
    - If successful, formats the data and uploads it to S3 using `upload_to_s3()`.
    - Returns a status code indicating success or failure.

    Parameters:
        event (dict): AWS Lambda event data (not used in this function).
        context (object): AWS Lambda context object (not used in this function).

    Returns:
        dict: A dictionary containing:
            - statusCode (int): HTTP status code (200 if successful, 500 if failed).
            - body (str): A message indicating the result.
    """
    print("Fetching Lakers schedule...")
    schedule = fetch_lakers_schedule()

    if schedule:
        schedule_data = {"games": schedule}
        upload_to_s3(schedule_data, BUCKET_NAME, S3_KEY)
        return {"statusCode": 200, "body": "Schedule uploaded successfully"}
    
    return {"statusCode": 500, "body": "Failed to fetch schedule"}