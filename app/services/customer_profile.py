from app.model import CustomerProfile

def update_customer_profile(db, phone_number, prediction, probability):
    profile = db.query(CustomerProfile).filter_by(phone_number=phone_number).first()

    if not profile:
        profile = CustomerProfile(
            phone_number=phone_number,
            total_orders=0,
            failed_deliveries=0,
            failure_rate=0.0
        )
        db.add(profile)

    #Safety guard (never remove)
    profile.total_orders = profile.total_orders or 0
    profile.failed_deliveries = profile.failed_deliveries or 0

    #Always increment total orders
    profile.total_orders += 1

    #ONLY count failure if model is CONFIDENT
    if prediction == 1 and probability > 0.7:
        profile.failed_deliveries += 1

    #Avoid division issues
    if profile.total_orders > 0:
        profile.failure_rate = profile.failed_deliveries / profile.total_orders
    else:
        profile.failure_rate = 0.0

    db.commit()

    return profile