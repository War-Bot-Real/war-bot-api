import os
import requests
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

def broadcast(topic, event, payload):
    url = f"{SUPABASE_URL}/realtime/v1/api/broadcast/{quote(topic, safe='')}/events/{quote(event, safe='')}"

    response = requests.post(
        url,
        headers={
            "apikey": SUPABASE_KEY,
            "Content-Type": "application/json"
        },
        params={"private": "true"},
        json=payload
    )

    if not response.ok:
        raise Exception(f"Realtime broadcast failed: {response.status_code} {response.text}")