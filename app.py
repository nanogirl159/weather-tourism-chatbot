from flask import Flask, render_template_string, request
import requests

app = Flask(__name__)

GEO_KEY = "2e64e356f56a4087b33e18a0b33163ba"   
USER_AGENT = "TravelChatbot/1.0 (aayushi310703@gmail.com)"


def detect_city(q):
    url = "https://api.geoapify.com/v1/geocode/search"
    params = {
        "text": q,
        "apiKey": GEO_KEY,
        "limit": 1
    }

    r = requests.get(url, params=params).json()

    feats = r.get("features", [])
    if not feats:
        return None, None, None

    props = feats[0]["properties"]
    lat = props["lat"]
    lon = props["lon"]
    name = props.get("city") or props.get("name") or "Selected City"

    return name, lat, lon



def get_weather(lat, lon):
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current_weather": True}
        ).json()
        return r["current_weather"]["temperature"]
    except:
        return None


def get_tourist_places(lat, lon):
    try:
        query = f"""
        [out:json];
        (
          node(around:7000,{lat},{lon})["tourism"~"attraction|museum|gallery|viewpoint|zoo"];
          node(around:7000,{lat},{lon})["historic"];
          node(around:7000,{lat},{lon})["amenity"="park"];
        );
        out center;
        """

        r = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            headers={"User-Agent": USER_AGENT}
        ).json()

        places = []
        for el in r.get("elements", []):
            name = el.get("tags", {}).get("name")
            if name:
                low = name.lower()
                if not any(x in low for x in ["hotel", "resid", "inn", "hostel"]):
                    places.append(name)

        return places[:10]

    except:
        return []



def process_message(msg):
    city, lat, lon = detect_city(msg)

    if not lat:
        return "❌ City not found. Try again."

    want_weather = any(k in msg.lower() for k in ["weather", "temperature"])
    want_places = any(k in msg.lower() for k in ["tourist", "visit", "places", "travel"])

    reply = []

    if want_weather:
        t = get_weather(lat, lon)
        reply.append(f"🌡️ Temperature in {city}: **{t}°C**")

    if want_places:
        p = get_tourist_places(lat, lon)
        if p:
            reply.append("🏞️ Tourist places:\n" + "\n".join(f"- {x}" for x in p))
        else:
            reply.append("No tourist places found.")

    if not reply:
        t = get_weather(lat, lon)
        p = get_tourist_places(lat, lon)

        reply.append(f"🌡️ Temperature in {city}: **{t}°C**")
        reply.append("🏞️ Tourist places:\n" + "\n".join(f"- {x}" for x in p))

    return "\n\n".join(reply)


html = """
<!DOCTYPE html>
<html>
<head><title>Travel Chatbot</title></head>
<body style="font-family: Arial; margin: 40px;">
    <h2>Travel & Weather Chatbot</h2>

    <form method="POST">
        <input name="msg" style="width: 60%; padding: 10px;" placeholder="tourist places in Mumbai">
        <button style="padding: 10px;">Send</button>
    </form>

    <h3>{{ reply | safe }}</h3>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    reply = ""
    if request.method == "POST":
        reply = process_message(request.form["msg"])
    return render_template_string(html, reply=reply)


if __name__ == "__main__":
    app.run(debug=True)
