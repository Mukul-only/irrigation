"""
Seed Indian plant profiles into any database (SQLite or PostgreSQL).
Usage:
  Local SQLite:  python seed_indian_plants.py
  Remote PG:     set DATABASE_URL=postgresql+asyncpg://... && python seed_indian_plants.py
"""

import os
import httpx
from datetime import datetime, timezone

TOKEN = "usr-hAyIXimDNFJ_IK2sNGuIo37ELm5odMaeQLvR68KVHlU"

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./irrigation.db")

# Normalize for sync SQLAlchemy (use psycopg2 driver)
if DB_URL.startswith("postgresql+asyncpg"):
    DB_URL = DB_URL.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)

from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.orm import sessionmaker

engine = create_engine(DB_URL, echo=False)
Session = sessionmaker(bind=engine)

# ── Family/type → cultivation parameter mapping ──────────────────────────
# Ranges based on Indian horticultural / agronomic data
FAMILY_PROFILES = {
    "Poaceae": {  # grasses & cereals
        "category": "grass",
        "moisture_min": 40,
        "moisture_max": 80,
        "ideal_moisture": 60,
        "temp_min": 15,
        "temp_max": 40,
        "humidity_min": 40,
        "humidity_max": 85,
        "avg_moisture_decay_per_hour": 2.5,
        "description": "Warm-season grasses and cereals common in Indian agriculture.",
    },
    "Fabaceae": {  # legumes / pulses
        "category": "legume",
        "moisture_min": 35,
        "moisture_max": 75,
        "ideal_moisture": 55,
        "temp_min": 18,
        "temp_max": 38,
        "humidity_min": 35,
        "humidity_max": 80,
        "avg_moisture_decay_per_hour": 2.2,
        "description": "Nitrogen-fixing legumes and pulses widely grown across India.",
    },
    "Asteraceae": {  # sunflower, marigold, weeds
        "category": "herb",
        "moisture_min": 30,
        "moisture_max": 70,
        "ideal_moisture": 50,
        "temp_min": 15,
        "temp_max": 42,
        "humidity_min": 30,
        "humidity_max": 80,
        "avg_moisture_decay_per_hour": 2.0,
        "description": "Diverse family including ornamentals, medicinal herbs, and oilseed crops.",
    },
    "Rosaceae": {  # rose, apple, strawberry
        "category": "shrub",
        "moisture_min": 45,
        "moisture_max": 80,
        "ideal_moisture": 60,
        "temp_min": 5,
        "temp_max": 35,
        "humidity_min": 40,
        "humidity_max": 85,
        "avg_moisture_decay_per_hour": 2.3,
        "description": "Fruit trees and ornamental shrubs in the rose family.",
    },
    "Solanaceae": {  # tomato, potato, brinjal, chilli
        "category": "vegetable",
        "moisture_min": 50,
        "moisture_max": 85,
        "ideal_moisture": 65,
        "temp_min": 18,
        "temp_max": 38,
        "humidity_min": 45,
        "humidity_max": 85,
        "avg_moisture_decay_per_hour": 3.0,
        "description": "Important vegetable crops including tomato, potato, brinjal, and chillies.",
    },
    "Brassicaceae": {  # mustard, cabbage, cauliflower
        "category": "vegetable",
        "moisture_min": 45,
        "moisture_max": 80,
        "ideal_moisture": 60,
        "temp_min": 10,
        "temp_max": 30,
        "humidity_min": 40,
        "humidity_max": 80,
        "avg_moisture_decay_per_hour": 2.5,
        "description": "Cool-season vegetable and oilseed crops like mustard, cabbage, and cauliflower.",
    },
    "Cucurbitaceae": {  # cucumber, pumpkin, watermelon, bitter gourd
        "category": "vegetable",
        "moisture_min": 55,
        "moisture_max": 90,
        "ideal_moisture": 70,
        "temp_min": 20,
        "temp_max": 40,
        "humidity_min": 50,
        "humidity_max": 90,
        "avg_moisture_decay_per_hour": 3.5,
        "description": "Summer vine crops requiring high moisture — cucumber, pumpkin, melons, gourds.",
    },
    "Apiaceae": {  # coriander, cumin, carrot
        "category": "herb",
        "moisture_min": 40,
        "moisture_max": 75,
        "ideal_moisture": 55,
        "temp_min": 10,
        "temp_max": 35,
        "humidity_min": 35,
        "humidity_max": 75,
        "avg_moisture_decay_per_hour": 2.0,
        "description": "Spice and vegetable herbs including coriander, cumin, and carrot.",
    },
    "Amaranthaceae": {  # amaranth, spinach (palak)
        "category": "leafy_green",
        "moisture_min": 50,
        "moisture_max": 85,
        "ideal_moisture": 65,
        "temp_min": 15,
        "temp_max": 38,
        "humidity_min": 45,
        "humidity_max": 85,
        "avg_moisture_decay_per_hour": 2.8,
        "description": "Leafy greens and amaranths, important for Indian kitchen gardens.",
    },
    "Malvaceae": {  # cotton, okra (bhindi), hibiscus
        "category": "crop",
        "moisture_min": 45,
        "moisture_max": 80,
        "ideal_moisture": 60,
        "temp_min": 20,
        "temp_max": 40,
        "humidity_min": 40,
        "humidity_max": 85,
        "avg_moisture_decay_per_hour": 2.5,
        "description": "Includes cotton, okra (bhindi), and ornamental hibiscus.",
    },
    "Rutaceae": {  # citrus — lemon, orange, lime
        "category": "tree",
        "moisture_min": 50,
        "moisture_max": 80,
        "ideal_moisture": 65,
        "temp_min": 15,
        "temp_max": 38,
        "humidity_min": 45,
        "humidity_max": 85,
        "avg_moisture_decay_per_hour": 2.0,
        "description": "Citrus trees — lemon, orange, lime — widely grown in India.",
    },
    "Myrtaceae": {  # guava, jamun, eucalyptus
        "category": "tree",
        "moisture_min": 40,
        "moisture_max": 75,
        "ideal_moisture": 55,
        "temp_min": 15,
        "temp_max": 42,
        "humidity_min": 40,
        "humidity_max": 85,
        "avg_moisture_decay_per_hour": 1.8,
        "description": "Fruit and timber trees including guava and jamun.",
    },
    "Moraceae": {  # fig, mulberry, banyan, peepal
        "category": "tree",
        "moisture_min": 35,
        "moisture_max": 70,
        "ideal_moisture": 50,
        "temp_min": 10,
        "temp_max": 45,
        "humidity_min": 30,
        "humidity_max": 80,
        "avg_moisture_decay_per_hour": 1.5,
        "description": "Large trees including banyan, peepal, fig, and mulberry.",
    },
    "Arecaceae": {  # coconut, date palm, areca nut
        "category": "palm",
        "moisture_min": 60,
        "moisture_max": 95,
        "ideal_moisture": 75,
        "temp_min": 22,
        "temp_max": 38,
        "humidity_min": 60,
        "humidity_max": 95,
        "avg_moisture_decay_per_hour": 3.0,
        "description": "Tropical palms — coconut, areca nut, and date palm — requiring high humidity.",
    },
    "Musaceae": {  # banana
        "category": "herb",
        "moisture_min": 65,
        "moisture_max": 95,
        "ideal_moisture": 80,
        "temp_min": 20,
        "temp_max": 38,
        "humidity_min": 60,
        "humidity_max": 95,
        "avg_moisture_decay_per_hour": 3.5,
        "description": "Banana — India's most important fruit crop, requiring high moisture and warmth.",
    },
    "Anacardiaceae": {  # mango, cashew
        "category": "tree",
        "moisture_min": 35,
        "moisture_max": 70,
        "ideal_moisture": 50,
        "temp_min": 20,
        "temp_max": 45,
        "humidity_min": 35,
        "humidity_max": 80,
        "avg_moisture_decay_per_hour": 1.5,
        "description": "Mango and cashew — India's leading fruit and nut trees.",
    },
    "Lamiaceae": {  # tulsi, mint, basil
        "category": "herb",
        "moisture_min": 45,
        "moisture_max": 80,
        "ideal_moisture": 60,
        "temp_min": 15,
        "temp_max": 38,
        "humidity_min": 40,
        "humidity_max": 85,
        "avg_moisture_decay_per_hour": 2.5,
        "description": "Aromatic herbs including tulsi (holy basil), mint, and culinary basil.",
    },
    "Zingiberaceae": {  # ginger, turmeric
        "category": "spice",
        "moisture_min": 60,
        "moisture_max": 90,
        "ideal_moisture": 75,
        "temp_min": 20,
        "temp_max": 35,
        "humidity_min": 60,
        "humidity_max": 95,
        "avg_moisture_decay_per_hour": 2.8,
        "description": "Rhizome spices — ginger and turmeric — requiring warm, moist conditions.",
    },
    "Piperaceae": {  # black pepper
        "category": "spice",
        "moisture_min": 65,
        "moisture_max": 95,
        "ideal_moisture": 80,
        "temp_min": 22,
        "temp_max": 35,
        "humidity_min": 65,
        "humidity_max": 95,
        "avg_moisture_decay_per_hour": 2.5,
        "description": "Black pepper — 'king of spices', native to the Western Ghats.",
    },
    "Theaceae": {  # tea
        "category": "shrub",
        "moisture_min": 60,
        "moisture_max": 95,
        "ideal_moisture": 75,
        "temp_min": 12,
        "temp_max": 30,
        "humidity_min": 60,
        "humidity_max": 95,
        "avg_moisture_decay_per_hour": 2.5,
        "description": "Tea plant — grown in Assam, Darjeeling, and Nilgiris.",
    },
    "Rubiaceae": {  # coffee
        "category": "shrub",
        "moisture_min": 55,
        "moisture_max": 85,
        "ideal_moisture": 70,
        "temp_min": 15,
        "temp_max": 28,
        "humidity_min": 55,
        "humidity_max": 90,
        "avg_moisture_decay_per_hour": 2.2,
        "description": "Coffee — grown in Karnataka, Kerala, and Tamil Nadu hills.",
    },
    "Euphorbiaceae": {  # castor, rubber
        "category": "crop",
        "moisture_min": 35,
        "moisture_max": 70,
        "ideal_moisture": 50,
        "temp_min": 18,
        "temp_max": 40,
        "humidity_min": 35,
        "humidity_max": 80,
        "avg_moisture_decay_per_hour": 2.0,
        "description": "Castor and rubber — important industrial and oilseed crops.",
    },
    "Convolvulaceae": {  # sweet potato, morning glory
        "category": "vegetable",
        "moisture_min": 45,
        "moisture_max": 80,
        "ideal_moisture": 60,
        "temp_min": 18,
        "temp_max": 38,
        "humidity_min": 40,
        "humidity_max": 85,
        "avg_moisture_decay_per_hour": 2.5,
        "description": "Sweet potato and ornamental morning glories.",
    },
    "Chenopodiaceae": {  # beet, spinach relatives
        "category": "leafy_green",
        "moisture_min": 40,
        "moisture_max": 75,
        "ideal_moisture": 55,
        "temp_min": 10,
        "temp_max": 35,
        "humidity_min": 35,
        "humidity_max": 75,
        "avg_moisture_decay_per_hour": 2.2,
        "description": "Beet and leafy greens in the goosefoot family.",
    },
    "Liliaceae": {  # onion, garlic, aloe
        "category": "vegetable",
        "moisture_min": 35,
        "moisture_max": 70,
        "ideal_moisture": 50,
        "temp_min": 10,
        "temp_max": 35,
        "humidity_min": 30,
        "humidity_max": 75,
        "avg_moisture_decay_per_hour": 1.8,
        "description": "Allium crops — onion and garlic — essential to Indian cuisine.",
    },
    "Orchidaceae": {  # orchids
        "category": "flower",
        "moisture_min": 60,
        "moisture_max": 90,
        "ideal_moisture": 75,
        "temp_min": 18,
        "temp_max": 35,
        "humidity_min": 60,
        "humidity_max": 95,
        "avg_moisture_decay_per_hour": 2.0,
        "description": "Orchids — popular ornamental flowers in Indian horticulture.",
    },
    "Bignoniaceae": {  # flame tree, jacaranda
        "category": "tree",
        "moisture_min": 30,
        "moisture_max": 65,
        "ideal_moisture": 45,
        "temp_min": 15,
        "temp_max": 42,
        "humidity_min": 30,
        "humidity_max": 75,
        "avg_moisture_decay_per_hour": 1.5,
        "description": "Ornamental trees like flame tree and jacaranda.",
    },
    "Meliaceae": {  # neem
        "category": "tree",
        "moisture_min": 25,
        "moisture_max": 60,
        "ideal_moisture": 40,
        "temp_min": 15,
        "temp_max": 48,
        "humidity_min": 25,
        "humidity_max": 75,
        "avg_moisture_decay_per_hour": 1.2,
        "description": "Neem — India's 'village pharmacy', drought-tolerant and medicinal.",
    },
    "Moringaceae": {  # drumstick / moringa
        "category": "tree",
        "moisture_min": 25,
        "moisture_max": 60,
        "ideal_moisture": 40,
        "temp_min": 20,
        "temp_max": 45,
        "humidity_min": 25,
        "humidity_max": 70,
        "avg_moisture_decay_per_hour": 1.5,
        "description": "Moringa (drumstick) — highly nutritious, drought-tolerant tree.",
    },
    "Sapindaceae": {  # lychee, rambutan
        "category": "tree",
        "moisture_min": 50,
        "moisture_max": 80,
        "ideal_moisture": 65,
        "temp_min": 18,
        "temp_max": 38,
        "humidity_min": 50,
        "humidity_max": 85,
        "avg_moisture_decay_per_hour": 1.8,
        "description": "Lychee and related tropical fruit trees.",
    },
    "default": {
        "category": "plant",
        "moisture_min": 35,
        "moisture_max": 70,
        "ideal_moisture": 50,
        "temp_min": 15,
        "temp_max": 38,
        "humidity_min": 35,
        "humidity_max": 80,
        "avg_moisture_decay_per_hour": 2.0,
        "description": "General plant profile with moderate growing conditions.",
    },
}

# ── Curated Indian plant list (fallback if API is slow) ──────────────────
INDIAN_PLANTS = [
    # (scientific_name, common_name, family)
    ("Oryza sativa", "Rice", "Poaceae"),
    ("Triticum aestivum", "Wheat", "Poaceae"),
    ("Zea mays", "Maize", "Poaceae"),
    ("Sorghum bicolor", "Jowar", "Poaceae"),
    ("Pennisetum glaucum", "Bajra", "Poaceae"),
    ("Eleusine coracana", "Ragi", "Poaceae"),
    ("Cicer arietinum", "Chickpea", "Fabaceae"),
    ("Cajanus cajan", "Pigeon Pea / Arhar", "Fabaceae"),
    ("Vigna radiata", "Moong", "Fabaceae"),
    ("Vigna mungo", "Urad Dal", "Fabaceae"),
    ("Lens culinaris", "Masoor Dal", "Fabaceae"),
    ("Glycine max", "Soybean", "Fabaceae"),
    ("Arachis hypogaea", "Groundnut", "Fabaceae"),
    ("Pisum sativum", "Garden Pea", "Fabaceae"),
    ("Solanum lycopersicum", "Tomato", "Solanaceae"),
    ("Solanum tuberosum", "Potato", "Solanaceae"),
    ("Solanum melongena", "Brinjal", "Solanaceae"),
    ("Capsicum annuum", "Chilli Pepper", "Solanaceae"),
    ("Capsicum frutescens", "Bird's Eye Chilli", "Solanaceae"),
    ("Cucumis sativus", "Cucumber", "Cucurbitaceae"),
    ("Cucurbita maxima", "Pumpkin", "Cucurbitaceae"),
    ("Citrullus lanatus", "Watermelon", "Cucurbitaceae"),
    ("Lagenaria siceraria", "Bottle Gourd", "Cucurbitaceae"),
    ("Momordica charantia", "Bitter Gourd", "Cucurbitaceae"),
    ("Luffa acutangula", "Ridge Gourd", "Cucurbitaceae"),
    ("Brassica juncea", "Indian Mustard", "Brassicaceae"),
    ("Brassica oleracea var. capitata", "Cabbage", "Brassicaceae"),
    ("Brassica oleracea var. botrytis", "Cauliflower", "Brassicaceae"),
    ("Raphanus sativus", "Radish", "Brassicaceae"),
    ("Coriandrum sativum", "Coriander", "Apiaceae"),
    ("Cuminum cyminum", "Cumin", "Apiaceae"),
    ("Daucus carota", "Carrot", "Apiaceae"),
    ("Amaranthus viridis", "Amaranth", "Amaranthaceae"),
    ("Abelmoschus esculentus", "Okra / Bhindi", "Malvaceae"),
    ("Gossypium hirsutum", "Cotton", "Malvaceae"),
    ("Citrus limon", "Lemon", "Rutaceae"),
    ("Citrus sinensis", "Sweet Orange", "Rutaceae"),
    ("Psidium guajava", "Guava", "Myrtaceae"),
    ("Syzygium cumini", "Jamun", "Myrtaceae"),
    ("Ficus benghalensis", "Banyan", "Moraceae"),
    ("Ficus religiosa", "Peepal", "Moraceae"),
    ("Mangifera indica", "Mango", "Anacardiaceae"),
    ("Anacardium occidentale", "Cashew", "Anacardiaceae"),
    ("Cocos nucifera", "Coconut", "Arecaceae"),
    ("Musa acuminata", "Banana", "Musaceae"),
    ("Ocimum tenuiflorum", "Tulsi / Holy Basil", "Lamiaceae"),
    ("Mentha spicata", "Mint / Pudina", "Lamiaceae"),
    ("Zingiber officinale", "Ginger", "Zingiberaceae"),
    ("Curcuma longa", "Turmeric", "Zingiberaceae"),
    ("Piper nigrum", "Black Pepper", "Piperaceae"),
    ("Camellia sinensis", "Tea", "Theaceae"),
    ("Coffea arabica", "Coffee", "Rubiaceae"),
    ("Azadirachta indica", "Neem", "Meliaceae"),
    ("Moringa oleifera", "Moringa / Drumstick", "Moringaceae"),
    ("Allium cepa", "Onion", "Liliaceae"),
    ("Allium sativum", "Garlic", "Liliaceae"),
    ("Saccharum officinarum", "Sugarcane", "Poaceae"),
    ("Helianthus annuus", "Sunflower", "Asteraceae"),
    ("Tagetes erecta", "Marigold", "Asteraceae"),
    ("Rosa indica", "Indian Rose", "Rosaceae"),
    ("Jasminum officinale", "Jasmine", "Oleaceae"),
    ("Nelumbo nucifera", "Lotus", "Nelumbonaceae"),
    ("Bambusa bambos", "Indian Bamboo", "Poaceae"),
    ("Boswellia serrata", "Salai / Indian Frankincense", "Burseraceae"),
    ("Terminalia chebula", "Haritaki", "Combretaceae"),
    ("Emblica officinalis", "Amla / Indian Gooseberry", "Phyllanthaceae"),
    ("Withania somnifera", "Ashwagandha", "Solanaceae"),
    ("Bacopa monnieri", "Brahmi", "Plantaginaceae"),
    ("Centella asiatica", "Gotu Kola", "Apiaceae"),
    ("Tinospora cordifolia", "Giloy", "Menispermaceae"),
    ("Saraca asoca", "Ashoka Tree", "Fabaceae"),
    ("Pongamia pinnata", "Karanj", "Fabaceae"),
    ("Dalbergia sissoo", "Shisham", "Fabaceae"),
    ("Santalum album", "Sandalwood", "Santalaceae"),
    ("Dioscorea bulbifera", "Air Potato", "Dioscoreaceae"),
    ("Colocasia esculenta", "Taro / Arbi", "Araceae"),
    ("Ipomoea batatas", "Sweet Potato", "Convolvulaceae"),
    ("Sesamum indicum", "Sesame / Til", "Pedaliaceae"),
    ("Ricinus communis", "Castor", "Euphorbiaceae"),
    ("Carica papaya", "Papaya", "Caricaceae"),
    ("Litchi chinensis", "Lychee", "Sapindaceae"),
    ("Annona squamosa", "Custard Apple / Sitaphal", "Annonaceae"),
    ("Phoenix sylvestris", "Date Palm", "Arecaceae"),
    ("Areca catechu", "Areca Nut / Supari", "Arecaceae"),
    ("Elettaria cardamomum", "Cardamom", "Zingiberaceae"),
    ("Cinnamomum verum", "Cinnamon", "Lauraceae"),
    ("Syzygium aromaticum", "Clove", "Myrtaceae"),
    ("Nymphaea nouchali", "Blue Water Lily", "Nymphaeaceae"),
    ("Hibiscus rosa-sinensis", "Hibiscus", "Malvaceae"),
    ("Bougainvillea spectabilis", "Bougainvillea", "Nyctaginaceae"),
    ("Plumeria rubra", "Frangipani / Champa", "Apocynaceae"),
    ("Nerium oleander", "Kaner", "Apocynaceae"),
    ("Delonix regia", "Gulmohar", "Fabaceae"),
    ("Jacaranda mimosifolia", "Jacaranda", "Bignoniaceae"),
    ("Cassia fistula", "Golden Shower / Amaltas", "Fabaceae"),
    ("Lagerstroemia speciosa", "Pride of India", "Lythraceae"),
    ("Alstonia scholaris", "Devil's Tree", "Apocynaceae"),
    ("Madhuca longifolia", "Mahua", "Sapotaceae"),
    ("Shorea robusta", "Sal Tree", "Dipterocarpaceae"),
    ("Tectona grandis", "Teak", "Lamiaceae"),
    ("Swietenia mahagoni", "Mahogany", "Meliaceae"),
    ("Eucalyptus globulus", "Eucalyptus", "Myrtaceae"),
]


# ── Fetch additional Indian plants from Trefle ──────────────────────────
def fetch_trefle_plants(query="india", max_pages=3):
    """Fetch plants from Trefle API filtered by distribution containing India."""
    plants = []
    for page in range(1, max_pages + 1):
        url = f"https://trefle.io/api/v1/plants?token={TOKEN}&filter[distribution]=india&per_page=30&page={page}"
        try:
            resp = httpx.get(url, timeout=15)
            data = resp.json().get("data", [])
            if not data:
                break
            for p in data:
                plants.append(
                    {
                        "scientific_name": p.get("scientific_name", ""),
                        "common_name": p.get("common_name")
                        or p.get("scientific_name", ""),
                        "family": p.get("family", ""),
                    }
                )
        except Exception as e:
            print(f"  API error on page {page}: {e}")
            break
    return plants


# ── Merge & deduplicate ─────────────────────────────────────────────────
def build_plant_list():
    """Combine curated Indian plants with Trefle API results."""
    seen = set()
    plants = []

    # Start with curated list
    for sci, common, family in INDIAN_PLANTS:
        key = sci.lower()
        if key not in seen:
            seen.add(key)
            plants.append(
                {
                    "scientific_name": sci,
                    "common_name": common,
                    "family": family,
                }
            )

    # Add from Trefle
    print("Fetching from Trefle API...")
    api_plants = fetch_trefle_plants()
    for p in api_plants:
        key = p["scientific_name"].lower()
        if key not in seen and p["scientific_name"]:
            seen.add(key)
            plants.append(p)

    print(f"Total unique plants: {len(plants)}")
    return plants


# ── Insert into DB ──────────────────────────────────────────────────────
def seed_database(plants):
    print(f"Seeding database: {DB_URL}")
    with engine.connect() as conn:
        # Ensure table exists
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS plant_profiles (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                category VARCHAR(50) NOT NULL,
                moisture_min FLOAT NOT NULL,
                moisture_max FLOAT NOT NULL,
                ideal_moisture FLOAT NOT NULL,
                temp_min FLOAT NOT NULL,
                temp_max FLOAT NOT NULL,
                humidity_min FLOAT NOT NULL,
                humidity_max FLOAT NOT NULL,
                avg_moisture_decay_per_hour FLOAT NOT NULL,
                description TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        )
        conn.commit()

        inserted = 0
        skipped = 0

        for p in plants:
            sci = p["scientific_name"]
            common = p["common_name"]
            family = p.get("family", "")

            profile = FAMILY_PROFILES.get(family, FAMILY_PROFILES["default"])

            name = common if common else sci
            description = profile["description"]
            if family:
                description += f" Family: {family}."
            description += f" Scientific name: {sci}."

            try:
                conn.execute(
                    text("""
                    INSERT INTO plant_profiles
                    (name, category, moisture_min, moisture_max, ideal_moisture,
                     temp_min, temp_max, humidity_min, humidity_max,
                     avg_moisture_decay_per_hour, description, created_at)
                    VALUES (:name, :category, :moisture_min, :moisture_max, :ideal_moisture,
                            :temp_min, :temp_max, :humidity_min, :humidity_max,
                            :decay, :description, :created_at)
                    ON CONFLICT (name) DO NOTHING
                """),
                    {
                        "name": name,
                        "category": profile["category"],
                        "moisture_min": profile["moisture_min"],
                        "moisture_max": profile["moisture_max"],
                        "ideal_moisture": profile["ideal_moisture"],
                        "temp_min": profile["temp_min"],
                        "temp_max": profile["temp_max"],
                        "humidity_min": profile["humidity_min"],
                        "humidity_max": profile["humidity_max"],
                        "decay": profile["avg_moisture_decay_per_hour"],
                        "description": description,
                        "created_at": datetime.now(timezone.utc),
                    },
                )
                inserted += 1
            except Exception as e:
                print(f"  Error inserting {sci}: {e}")
                skipped += 1

        conn.commit()
        print(f"\nDone! Inserted: {inserted}, Skipped (duplicate): {skipped}")


async def seed_database_sync():
    """Async version that uses the app's async database engine."""
    from app.database import AsyncSessionLocal
    from app.models import PlantProfile

    plants = build_plant_list()

    async with AsyncSessionLocal() as db:
        inserted = 0
        skipped = 0

        for p in plants:
            sci = p["scientific_name"]
            common = p["common_name"]
            family = p.get("family", "")

            profile = FAMILY_PROFILES.get(family, FAMILY_PROFILES["default"])

            name = common if common else sci
            description = profile["description"]
            if family:
                description += f" Family: {family}."
            description += f" Scientific name: {sci}."

            try:
                plant = PlantProfile(
                    name=name,
                    category=profile["category"],
                    moisture_min=profile["moisture_min"],
                    moisture_max=profile["moisture_max"],
                    ideal_moisture=profile["ideal_moisture"],
                    temp_min=profile["temp_min"],
                    temp_max=profile["temp_max"],
                    humidity_min=profile["humidity_min"],
                    humidity_max=profile["humidity_max"],
                    avg_moisture_decay_per_hour=profile["avg_moisture_decay_per_hour"],
                    description=description,
                )
                db.add(plant)
                await db.commit()
                inserted += 1
            except Exception as e:
                await db.rollback()
                print(f"  Error inserting {sci}: {e}")
                skipped += 1

        print(f"\nAsync seeding done! Inserted: {inserted}, Skipped: {skipped}")


if __name__ == "__main__":
    plants = build_plant_list()
    seed_database(plants)
