import os
import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path("backend").resolve()
sys.path.insert(0, str(backend_path))

from app.services.firebase_service import initialize_firebase, get_firestore_client
from firebase_admin import auth

app = initialize_firebase()
print(f"Connected to Firebase App: {app.name}, Project ID: {app.project_id}")

# List users in Firebase Auth
print("\n--- Firebase Auth Users ---")
page = auth.list_users()
users = []
for user in page.users:
    print(f"UID: {user.uid}, Email: {user.email}, Custom Claims: {user.custom_claims}")
    users.append(user)

# Check Firestore collections
db = get_firestore_client()
print("\n--- Firestore Collections ---")
cols = [c.id for c in db.collections()]
print(f"Existing Collections: {cols}")

if "users" in cols:
    print("\n--- Firestore users collection docs ---")
    for doc in db.collection("users").stream():
        d = doc.to_dict()
        print(f"Doc ID: {doc.id}, Email: {d.get('email')}, Role: {d.get('role')}")

if "incidents" in cols:
    print("\n--- Firestore incidents collection docs ---")
    for doc in db.collection("incidents").stream():
        d = doc.to_dict()
        print(f"Incident ID: {doc.id}, Title: {d.get('title')}, Severity: {d.get('severity')}, Reporter: {d.get('reporter_email')}")
