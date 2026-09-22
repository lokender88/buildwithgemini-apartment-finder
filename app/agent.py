# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
import subprocess
import time
import urllib.request
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types
from google.oauth2.credentials import Credentials

try:
    from .a2ui_utils import a2ui_callback
except ImportError:
    from a2ui_utils import a2ui_callback

# HARDCODED PROJECT ID - Required because on Agent Platform GOOGLE_CLOUD_PROJECT
# and google.auth.default() return project numbers, which break Firestore client.
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-2679c4d7a8a5"
GCS_BUCKET_NAME = "apartment-finder-assets-qwiklabs-gcp-01-2679c4d7a8a5"
AGENT_ENGINE_RESOURCE_NAME = "projects/884999620990/locations/us-central1/reasoningEngines/1637396564374716416"





def get_firestore_client() -> firestore.Client:
    """Returns a Firestore client initialized with hardcoded project ID string."""
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


def get_apartment_listings(
    neighborhood: str = "", max_rent: float = 0.0, pet_friendly_only: bool = False
) -> str:
    """Reads available apartment listings directly from the Firestore database.

    Args:
        neighborhood: Optional filter for neighborhood (e.g., 'Midtown', 'Downtown', 'Uptown').
        max_rent: Optional maximum monthly rent budget in USD (0.0 means no limit).
        pet_friendly_only: If True, only returns pet-friendly listings.

    Returns:
        JSON formatted list of matching apartment listings stored in Firestore.
    """
    db = get_firestore_client()
    docs = db.collection("apartments").stream()
    listings = []
    for doc in docs:
        data = doc.to_dict()
        if not data.get("available", True):
            continue
        if neighborhood and neighborhood.lower() not in data.get("neighborhood", "").lower():
            continue
        if max_rent > 0 and data.get("monthly_rent", 0.0) > max_rent:
            continue
        if pet_friendly_only and not data.get("pet_friendly", False):
            continue
        listings.append(data)

    if not listings:
        return "No matching apartment listings found in Firestore."
    return json.dumps(listings, indent=2)


def add_apartment_listing(
    title: str,
    neighborhood: str,
    bedrooms: int,
    bathrooms: float,
    monthly_rent: float,
    pet_friendly: bool,
    address: str,
    amenities: str = "",
) -> str:
    """Writes a new apartment listing to the Firestore 'apartments' collection.

    Args:
        title: Property title (e.g., 'Midtown Modern Suite').
        neighborhood: Neighborhood name (e.g., 'Midtown').
        bedrooms: Number of bedrooms.
        bathrooms: Number of bathrooms.
        monthly_rent: Monthly rent in USD.
        pet_friendly: True if pets/dogs are allowed.
        address: Full street address.
        amenities: Comma-separated list of amenities (e.g., 'Balcony, Parking, Pool').

    Returns:
        Confirmation message with the created apartment ID in Firestore.
    """
    db = get_firestore_client()
    doc_id = f"apt-{int(time.time())}"
    amenities_list = [a.strip() for a in amenities.split(",") if a.strip()] if amenities else []
    data = {
        "id": doc_id,
        "title": title,
        "neighborhood": neighborhood,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "monthly_rent": monthly_rent,
        "pet_friendly": pet_friendly,
        "allows_dogs": pet_friendly,
        "amenities": amenities_list,
        "available": True,
        "address": address,
    }
    db.collection("apartments").document(doc_id).set(data)
    return f"Successfully saved apartment listing '{title}' with ID '{doc_id}' into Firestore."


def schedule_viewing_appointment(
    apartment_id: str,
    date: str,
    time_slot: str,
    contact_name: str,
    contact_email: str,
) -> str:
    """Schedules a property viewing appointment and saves it to Firestore.

    Args:
        apartment_id: The ID of the apartment listing to view (e.g., 'apt-101').
        date: Preferred date for the viewing (e.g., '2026-10-01' or 'next Tuesday').
        time_slot: Preferred time of day (e.g., '2:00 PM').
        contact_name: Full name of the user requesting the viewing.
        contact_email: Contact email address.

    Returns:
        Confirmation receipt string with booking reference ID.
    """
    db = get_firestore_client()
    booking_id = f"book-{int(time.time())}"
    appointment_data = {
        "booking_id": booking_id,
        "apartment_id": apartment_id,
        "date": date,
        "time_slot": time_slot,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "status": "CONFIRMED",
        "created_at": datetime.datetime.now(ZoneInfo("UTC")).isoformat(),
    }
    db.collection("viewing_appointments").document(booking_id).set(appointment_data)
    return (
        f"Viewing appointment successfully scheduled!\n"
        f"- Booking Reference: {booking_id}\n"
        f"- Apartment ID: {apartment_id}\n"
        f"- Date & Time: {date} at {time_slot}\n"
        f"- Contact: {contact_name} ({contact_email})"
    )


def lookup_zip_code_details(zip_code: str) -> str:
    """Fetches real location data (city, state, coordinates) for a US postal zip code via Zippopotam.us API.

    Args:
        zip_code: 5-digit US postal zip code (e.g., '30309').

    Returns:
        Location summary string containing place name, state, and geographic coordinates.
    """
    clean_zip = zip_code.strip()
    url = f"https://api.zippopotam.us/us/{clean_zip}"

    # Reads optional API key from environment variable if provided
    api_key = os.environ.get("ZIP_API_KEY")
    headers = {"User-Agent": "ApartmentFinderAgent/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                places = data.get("places", [])
                if places:
                    place = places[0]
                    return (
                        f"Zip Code {clean_zip} Location Details:\n"
                        f"- City/Place: {place.get('place name')}\n"
                        f"- State: {place.get('state')} ({place.get('state abbreviation')})\n"
                        f"- Coordinates: Lat {place.get('latitude')}, Long {place.get('longitude')}\n"
                        f"- Country: {data.get('country')}"
                    )
    except Exception as e:
        return f"Could not retrieve details for zip code '{clean_zip}': {e}"
    return f"No location data found for zip code '{clean_zip}'."


RAG_CORPUS_NAME = "projects/884999620990/locations/europe-west4/ragCorpora/2305843009213693952"


def consult_knowledge_base(query: str) -> str:
    """Searches the indexed knowledge base corpus (Culpeper's Herbal) for facts, remedies, and historical text passages.

    Args:
        query: The search topic or question to look up in the corpus (e.g., 'mint', 'herbal remedies').

    Returns:
        Matching text passages retrieved from the indexed knowledge base document.
    """
    import vertexai
    from vertexai.preview import rag

    try:
        vertexai.init(project="qwiklabs-gcp-01-2679c4d7a8a5", location="europe-west4")
        resp = rag.retrieval_query(
            text=query,
            rag_resources=[rag.RagResource(rag_corpus=RAG_CORPUS_NAME)],
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=5),
        )
        contexts = getattr(resp.contexts, "contexts", [])
        passages = [c.text.strip() for c in contexts if getattr(c, "text", "").strip()]
        if not passages:
            return "No relevant passages found in the knowledge base."
        return "\n\n---\n\n".join(passages)
    except Exception as e:
        return f"Knowledge base retrieval failed: {e}"


def generate_apartment_image(prompt: str, tool_context: ToolContext) -> str:
    """Generates a realistic image of an apartment interior, floor plan, amenity, or building exterior using gemini-3.1-flash-lite-image in the global region.

    Args:
        prompt: Detailed description of the apartment image to generate (e.g., 'Modern luxury apartment living room with balcony and city skyline view').
        tool_context: ADK ToolContext used to save session artifacts.

    Returns:
        Public Cloud Storage URL (https://storage.googleapis.com/<bucket>/<object>) where the image is hosted.
    """
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=f"Generate a realistic high-quality image of: {prompt}",
    )

    image_bytes = None
    mime_type = "image/jpeg"
    image_part = None

    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/jpeg"
                image_part = part
                break

    if not image_bytes:
        return "Failed to generate image: No image data returned from model."

    filename = f"apt_img_{int(time.time())}.jpg"

    # 1. Save with tool_context.save_artifact so it shows up in Playground's Artifacts panel
    try:
        if not image_part:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=image_part)
    except Exception as e:
        pass

    # 2. Upload same image bytes to public Cloud Storage bucket and return public https URL
    try:
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob_path = f"generated_images/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(image_bytes, content_type=mime_type)
        return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_path}"
    except Exception as e:
        return f"Image generated, but Cloud Storage upload failed: {e}"


def calculate_move_in_costs(monthly_rent: float, deposit_months: float = 1.0) -> str:
    """Calculates total estimated upfront move-in costs.

    Args:
        monthly_rent: The monthly rent amount in USD.
        deposit_months: Number of months rent required for security deposit (default 1.0).

    Returns:
        Breakdown of upfront move-in costs.
    """
    security_deposit = monthly_rent * deposit_months
    application_fee = 50.0
    total = monthly_rent + security_deposit + application_fee
    return (
        f"Move-in Cost Breakdown:\n"
        f"- First Month's Rent: ${monthly_rent:,.2f}\n"
        f"- Security Deposit ({deposit_months}x): ${security_deposit:,.2f}\n"
        f"- Application Fee: ${application_fee:,.2f}\n"
        f"Total Estimated Upfront Cost: ${total:,.2f}"
    )


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback triggered after each turn to save cross-session facts to Vertex AI Memory Bank."""
    await callback_context.add_session_to_memory()
    return None


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are an expert Apartment Finder AI Assistant with a real-time Firestore backend, RAG knowledge base, "
        "and sandboxed Python code execution capabilities via AgentEngineSandboxCodeExecutor. You help users "
        "search, query, and add rental properties stored in the 'apartments' Firestore collection, schedule "
        "viewing appointments, lookup zip codes, answer questions from the knowledge base, generate property photos, "
        "and calculate move-in costs."
    ),
    workflow_description=(
        "Analyze the request, use tools when necessary, and return structured A2UI when appropriate."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use Table or Heading (unsupported), "
        "or Buttons, actions, or forms (they do nothing in adk web). You may include one Image component, but only "
        "when you have a public https URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an Image at a bare filename, an artifact name, '
        "or a non-http(s) path. If you do not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in <a2a_datapart_json> tags or "
        "'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME,
    ),
    instruction=a2ui_instruction,
    tools=[
        get_apartment_listings,
        add_apartment_listing,
        schedule_viewing_appointment,
        lookup_zip_code_details,
        consult_knowledge_base,
        generate_apartment_image,
        calculate_move_in_costs,
        PreloadMemoryTool(),
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)


app = App(
    root_agent=root_agent,
    name="app",
)



