"""Seed script for Firestore apartments collection.

HARDCODED PROJECT ID: 'qwiklabs-gcp-01-2679c4d7a8a5'
Do NOT read from google.auth.default() or GOOGLE_CLOUD_PROJECT as those return
the project number on Agent Platform, breaking Firestore resolution.
"""

import subprocess
from google.cloud import firestore
from google.oauth2.credentials import Credentials

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-2679c4d7a8a5"

SEEDED_APARTMENTS = [
    {
        "id": "apt-101",
        "title": "Midtown Luxury Suite",
        "neighborhood": "Midtown",
        "bedrooms": 2,
        "bathrooms": 2,
        "monthly_rent": 2400.0,
        "pet_friendly": True,
        "allows_dogs": True,
        "amenities": ["Parking", "Balcony", "Fitness Center", "In-unit Laundry"],
        "available": True,
        "address": "123 Peachtree St, Midtown",
    },
    {
        "id": "apt-102",
        "title": "Downtown Cozy Loft",
        "neighborhood": "Downtown",
        "bedrooms": 1,
        "bathrooms": 1,
        "monthly_rent": 1850.0,
        "pet_friendly": False,
        "allows_dogs": False,
        "amenities": ["Washer/Dryer", "Rooftop Deck", "Hardwood Floors"],
        "available": True,
        "address": "456 Main St, Downtown",
    },
    {
        "id": "apt-103",
        "title": "Uptown Garden Apartment",
        "neighborhood": "Uptown",
        "bedrooms": 2,
        "bathrooms": 1,
        "monthly_rent": 2200.0,
        "pet_friendly": True,
        "allows_dogs": True,
        "amenities": ["Garden", "Balcony", "Dog Park Access", "Dishwasher"],
        "available": True,
        "address": "789 Oak Ave, Uptown",
    },
    {
        "id": "apt-104",
        "title": "Midtown Executive Penthouse",
        "neighborhood": "Midtown",
        "bedrooms": 3,
        "bathrooms": 2.5,
        "monthly_rent": 3800.0,
        "pet_friendly": True,
        "allows_dogs": True,
        "amenities": ["Concierge", "EV Charging", "Private Elevator", "Pool"],
        "available": True,
        "address": "100 Skyline Blvd, Midtown",
    },
]


def get_firestore_client() -> firestore.Client:
    """Returns a Firestore client initialized with the hardcoded project ID."""
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"], stderr=subprocess.DEVNULL
        ).decode().strip()
        if token:
            creds = Credentials(token)
            return firestore.Client(project=FIRESTORE_PROJECT_ID, credentials=creds)
    except Exception:
        pass
    return firestore.Client(project=FIRESTORE_PROJECT_ID)


def seed():
    db = get_firestore_client()
    collection_ref = db.collection("apartments")

    print(f"Seeding Firestore collection 'apartments' in project '{FIRESTORE_PROJECT_ID}'...")
    for apt in SEEDED_APARTMENTS:
        doc_ref = collection_ref.document(apt["id"])
        doc_ref.set(apt)
        print(f"  Added document: {apt['id']} ({apt['title']})")

    print("Firestore seeding complete!")


if __name__ == "__main__":
    seed()
