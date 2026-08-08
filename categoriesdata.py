from app.model import Category
def seed_categories(db):
    categories = [
        # High-risk (easy resale / expensive / fraud-heavy)
        {"name": "mobile_phones", "risk_score": 0.08},
        {"name": "computers", "risk_score": 0.07},
        {"name": "gaming_consoles", "risk_score": 0.06},
        {"name": "cameras", "risk_score": 0.06},
        {"name": "jewelry", "risk_score": 0.09},
        {"name": "watches", "risk_score": 0.08},
        {"name": "luxury_items", "risk_score": 0.07},

        {"name": "fashion", "risk_score": 0.03},
        {"name": "shoes", "risk_score": 0.03},
        {"name": "beauty_products", "risk_score": 0.02},
        {"name": "home_appliances", "risk_score": 0.04},
        {"name": "furniture", "risk_score": 0.03},
        {"name": "sports_equipment", "risk_score": 0.03},
        {"name": "automotive_parts", "risk_score": 0.04},

        {"name": "groceries", "risk_score": 0.01},
        {"name": "books", "risk_score": 0.01},
        {"name": "stationery", "risk_score": 0.01},
        {"name": "pet_supplies", "risk_score": 0.01},
        {"name": "baby_products", "risk_score": 0.02},
        {"name": "cleaning_supplies", "risk_score": 0.01},
    ]

    for cat in categories:
        existing = db.query(Category).filter_by(name=cat["name"]).first()
        if not existing:
            db.add(Category(**cat))
    db.commit()