from flask import Flask, render_template, request
from google.cloud import storage
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
API_KEY = os.getenv("WEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

def save_to_gcs(data, bucket_name="weather-dashboard-prithvi"):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    city = data["city"].lower()
    filename = f"{city}_{timestamp}.json"
    blob = bucket.blob(filename)
    blob.upload_from_string(
        json.dumps(data, indent=2),
        content_type="application/json"
    )
    print(f"✅ Saved to GCS: {filename}")
    return filename

@app.route("/", methods=["GET", "POST"])
def index():
    weather_data = None
    error = None
    if request.method == "POST":
        city = request.form.get("city")
        response = requests.get(BASE_URL, params={
            "q": city,
            "appid": API_KEY,
            "units": "metric"
        })
        if response.status_code == 200:
            data = response.json()
            weather_data = {
                "city": data["name"],
                "country": data["sys"]["country"],
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "description": data["weather"][0]["description"],
                "wind_speed": data["wind"]["speed"]
            }
            save_to_gcs(weather_data)
        else:
            error = "City not found. Please try again."
    return render_template("index.html", weather=weather_data, error=error)

@app.route("/history")
def history():
    client = storage.Client()
    bucket = client.bucket("weather-dashboard-prithvi")
    blobs = bucket.list_blobs()
    
    snapshots = []
    for blob in blobs:
        data = json.loads(blob.download_as_string())
        parts = blob.name.replace(".json", "").split("_")
        timestamp = parts[-2] + " " + parts[-1].replace("-", ":")
        snapshots.append({
            "city": data["city"],
            "temperature": data["temperature"],
            "timestamp": timestamp
        })
    
    snapshots.sort(key=lambda x: x["timestamp"])
    return render_template("history.html", snapshots=snapshots)

if __name__ == "__main__":
    app.run(debug=True)