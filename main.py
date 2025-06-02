from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import random
import requests
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Environment variables
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')

# Groq client initialization
if not GROQ_API_KEY:
    raise Exception("GROQ_API_KEY is missing from .env")
client = Groq(api_key=GROQ_API_KEY)

LLAMA_MODEL = "llama-3.1-8b-instant"

# Restaurant details
RESTAURANT_NAME = "Hari Krushna Dal Pakwan"
RESTAURANT_ADDRESS = "24, Ambika Pinakal, Lajamni Chowk, Maruti Dham Society, Mota Varachha, Surat, Gujarat 394101"

def load_keywords():
    return {
        "user_keywords": [
            "delicious", "amazing", "fantastic", "excellent", "outstanding",
            "tasty", "authentic", "fresh", "crispy", "spicy",
            "flavorful", "traditional", "hygienic", "affordable", "quick service",
            "friendly staff", "clean", "homely", "perfect", "mouth-watering"
        ],
        "backend_keywords": [
            "highly recommend", "great experience", "will visit again", "worth trying",
            "exceeded expectations", "perfect taste", "amazing quality", "best in surat",
            "authentic gujarati", "reasonable price", "excellent service", "fresh preparation"
        ],
        "seo_keywords": [
            {"word": "dal pakwan", "weight": 10},
            {"word": "gujarati food", "weight": 9},
            {"word": "surat restaurant", "weight": 8},
            {"word": "street food", "weight": 7},
            {"word": "traditional", "weight": 6},
            {"word": "authentic", "weight": 8},
            {"word": "quality", "weight": 7},
            {"word": "taste", "weight": 9},
            {"word": "snacks", "weight": 5},
            {"word": "mota varachha", "weight": 4}
        ]
    }

def select_weighted_seo(seo_keywords, count=2):
    words = [k["word"] for k in seo_keywords]
    weights = [k["weight"] for k in seo_keywords]
    return random.choices(words, weights=weights, k=count)

def generate_prompt(user_keywords, keyword_data):
    backend = random.sample(keyword_data["backend_keywords"], 2)
    seo = select_weighted_seo(keyword_data["seo_keywords"], 2)
    all_keywords = user_keywords + backend + seo
    random.shuffle(all_keywords)
    return (
        f"You're a satisfied customer leaving a short review (under 50 words) about '{RESTAURANT_NAME}' - "
        f"a popular dal pakwan restaurant in Surat, Gujarat. Make it sound human, sincere, and natural. "
        f"Use the following keywords organically in the review:\n{', '.join(all_keywords)}.\n"
        "Keep the tone friendly and helpful. Focus on the food quality, taste, and dining experience. "
        "Mention specific items like dal pakwan if appropriate."
    )

def get_google_place_id():
    if not GOOGLE_PLACES_API_KEY:
        print("Google Places API key not configured")
        return None
    try:
        url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        params = {
            'input': f"{RESTAURANT_NAME} {RESTAURANT_ADDRESS}",
            'inputtype': 'textquery',
            'fields': 'place_id,name,formatted_address',
            'key': GOOGLE_PLACES_API_KEY
        }
        resp = requests.get(url, params=params)
        data = resp.json()
        if data.get("status") == "OK" and data.get("candidates"):
            return data["candidates"][0]["place_id"]
        else:
            print("Google Places API returned no results:", data.get("status"))
    except Exception as e:
        print("Google Places API Error:", e)
    return None

@app.route("/api/generate-review", methods=["POST"])
def generate_review():
    try:
        data = request.get_json()
        selected = data.get("selectedKeywords", [])
        if not selected:
            return jsonify({"error": "No keywords provided"}), 400

        keywords = load_keywords()
        prompt = generate_prompt(selected, keywords)

        response = client.chat.completions.create(
            model=LLAMA_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant who writes authentic restaurant reviews for Gujarati cuisine, especially dal pakwan."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=150
        )

        review = response.choices[0].message.content.strip()
        place_id = get_google_place_id()
        
        # Create Google review URL
        if place_id:
            google_review_url = f"https://search.google.com/local/writereview?placeid={place_id}"
        else:
            # Fallback to search URL
            google_review_url = f"https://www.google.com/search?q={requests.utils.quote(RESTAURANT_NAME + ' ' + RESTAURANT_ADDRESS + ' write review')}"

        return jsonify({
            "review": review,
            "prompt": prompt,
            "restaurant_name": RESTAURANT_NAME,
            "restaurant_address": RESTAURANT_ADDRESS,
            "place_id": place_id,
            "google_review_url": google_review_url
        })

    except Exception as e:
        print("Error in /api/generate-review:", e)
        return jsonify({"error": f"Review generation failed: {str(e)}"}), 500

@app.route("/api/restaurant-info", methods=["GET"])
def get_restaurant_info():
    place_id = get_google_place_id()
    
    # Create Google review URL
    if place_id:
        google_review_url = f"https://search.google.com/local/writereview?placeid={place_id}"
    else:
        google_review_url = f"https://www.google.com/search?q={requests.utils.quote(RESTAURANT_NAME + ' ' + RESTAURANT_ADDRESS + ' write review')}"
    
    return jsonify({
        "name": RESTAURANT_NAME,
        "address": RESTAURANT_ADDRESS,
        "place_id": place_id,
        "google_search_url": f"https://www.google.com/search?q={requests.utils.quote(RESTAURANT_NAME + ' ' + RESTAURANT_ADDRESS + ' write review')}",
        "google_review_url": google_review_url
    })

@app.route("/api/keywords", methods=["GET"])
def get_keywords():
    return jsonify(load_keywords())

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "restaurant": RESTAURANT_NAME})

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

if __name__ == "__main__":
    app.run(debug=True, port=5000)