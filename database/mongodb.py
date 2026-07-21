"""

Database layer for MailSort.

In MOCK_MODE (or when MongoDB is unreachable) an in-memory mock database
is used so the application runs without any external infrastructure.
Real MongoDB mode creates indexes for efficient query performance.
"""

import re
import time
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import Config
from utils.helpers import logger

# Active client and database references (module-level singletons)
_db_client = None
_db = None

# In-memory data stores shared across MockCollection instances
_mock_users = {}   # dict keyed by email address
_mock_emails = []  # flat list of email documents


class MockCollection:
    """
    In-memory substitute for a PyMongo collection.

    Supports the subset of MongoDB operations used by MailSort:
    find_one, update_one, insert_one, find, count_documents.
    """

    def __init__(self, name, data_store):
        self.name = name
        self.data_store = data_store

    def find_one(self, filter_dict):
        """Returns the first document matching all fields in filter_dict, or None."""
        if self.name == "users":
            email = filter_dict.get("email")
            return self.data_store.get(email)

        if self.name == "emails":
            for doc in self.data_store:
                if all(doc.get(k) == v for k, v in filter_dict.items()):
                    return doc

        return None

    def update_one(self, filter_dict, update_dict, upsert=False):
        """Applies a $set update to the first matching document."""
        data = update_dict.get("$set", {})

        if self.name == "users":
            email = filter_dict.get("email")
            if email:
                if email not in self.data_store:
                    self.data_store[email] = {"email": email}
                self.data_store[email].update(data)
                return True

        elif self.name == "emails":
            for idx, doc in enumerate(self.data_store):
                if all(doc.get(k) == v for k, v in filter_dict.items()):
                    self.data_store[idx].update(data)
                    return True
            if upsert:
                new_doc = dict(filter_dict)
                new_doc.update(data)
                self.data_store.append(new_doc)
                return True

        return False

    def insert_one(self, document):
        """Appends a document to the in-memory store."""
        if self.name == "emails":
            self.data_store.append(document)
            return True
        if self.name == "users":
            email = document.get("email")
            if email:
                self.data_store[email] = document
                return True
        return False

    def find(self, filter_dict=None):
        """
        Returns a mock Cursor over all documents matching filter_dict.

        Supports field equality checks and a simple $or clause with $regex.
        """
        filter_dict = filter_dict or {}
        results = []
        data = (
            self.data_store
            if isinstance(self.data_store, list)
            else self.data_store.values()
        )

        for item in data:
            match = True
            for key, value in filter_dict.items():
                if key == "$or":
                    # Evaluate each OR clause as a field regex match
                    or_match = any(
                        re.search(
                            clause_value.get("$regex", ""),
                            str(item.get(field, "")),
                            re.IGNORECASE,
                        )
                        for clause in value
                        for field, clause_value in clause.items()
                    )
                    if not or_match:
                        match = False
                elif item.get(key) != value:
                    match = False
            if match:
                results.append(item)

        return _MockCursor(results)

    def count_documents(self, filter_dict):
        """Returns the count of documents matching filter_dict."""
        return len(self.find(filter_dict).items)


class _MockCursor:
    """Minimal cursor returned by MockCollection.find(), supporting sort and iteration."""

    def __init__(self, items):
        self.items = items

    def sort(self, key_or_list, direction=None):
        """Sorts results by created_at descending (mirrors the app's primary sort)."""
        try:
            self.items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        except Exception:
            pass
        return self

    def __iter__(self):
        return iter(self.items)


class MockDatabase:
    """In-memory PyMongo database substitute for MOCK_MODE."""

    def __init__(self):
        self.users = MockCollection("users", _mock_users)
        self.emails = MockCollection("emails", _mock_emails)

    def __getitem__(self, name):
        if name == "users":
            return self.users
        if name == "emails":
            return self.emails
        raise KeyError(f"Collection '{name}' is not available in mock mode.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_db():
    """
    Initialises the database connection.

    Uses MockDatabase when MOCK_MODE is True or when MongoDB is unreachable.
    Creates performance indexes on first real MongoDB connection.
    """
    global _db_client, _db

    if Config.MOCK_MODE:
        logger.info("Initialising in-memory Mock Database (MOCK_MODE=True).")
        _db = MockDatabase()
        _seed_mock_data()
        return _db

    try:
        # Obfuscate credentials in log output by only showing the host portion
        host_display = Config.MONGO_URI.split('@')[-1]
        logger.info(f"Connecting to MongoDB at {host_display}...")
        _db_client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=3000)
        _db_client.admin.command('ping')  # Verify connectivity
        _db = _db_client.get_default_database()
        logger.info("Connected to MongoDB successfully.")

        # Compound and text indexes for query performance
        _db.emails.create_index("gmail_id", unique=True)
        _db.emails.create_index("user_email")
        _db.emails.create_index([("subject", "text"), ("body", "text")])
        _db.users.create_index("email", unique=True)

    except (ConnectionFailure, Exception) as e:
        logger.error(f"MongoDB connection failed: {e}")
        logger.warning("Falling back to in-memory Mock Database.")
        _db = MockDatabase()
        _seed_mock_data()

    return _db


def get_db():
    """Returns the active database instance, initialising it if necessary."""
    global _db
    if _db is None:
        init_db()
    return _db


# ---------------------------------------------------------------------------
# Mock data seeding
# ---------------------------------------------------------------------------

def _seed_mock_data():
    """Populates the mock database with representative demo emails and a demo user."""
    global _mock_emails
    if _mock_emails:
        return  # Already seeded

    now = time.time()

    _mock_emails.extend([
        {
            "gmail_id": "msg_001",
            "thread_id": "thread_001",
            "user_email": "demo@mailsort.ai",
            "sender": "sarah.manager@company.com",
            "receiver": "demo@mailsort.ai",
            "subject": "Urgent: Q3 Project Deliverables review",
            "body": (
                "Hi team, we need the final slides for the Q3 project review by 5:00 PM today. "
                "Please make sure the finance spreadsheets are updated and the Client feedback "
                "is incorporated. Thanks, Sarah."
            ),
            "date": "Mon, 20 Jul 2026 14:00:00 -0400",
            "attachments": [],
            "priority": "Urgent",
            "priority_score": 95,
            "category": "Manager",
            "summary": "Review and update Q3 slides and finance spreadsheets by 5:00 PM today.",
            "deadline": "Today, 5:00 PM",
            "action_items": [
                "Update finance spreadsheets",
                "Incorporate client feedback",
                "Submit final slides by 5:00 PM",
            ],
            "sentiment": "Neutral",
            "reason": (
                "Explicit deadline set for today (5:00 PM) by your direct manager, "
                "requiring prompt review."
            ),
            "suggested_reply": (
                "Hi Sarah,\n\nI am on it. I will update the spreadsheets and client comments, "
                "and have the final slides ready for your review well before the 5:00 PM "
                "deadline.\n\nBest regards,\nDemo"
            ),
            "status": "unread",
            "created_at": now - 3600,
        },
        {
            "gmail_id": "msg_002",
            "thread_id": "thread_002",
            "user_email": "demo@mailsort.ai",
            "sender": "billing@cloudservices.com",
            "receiver": "demo@mailsort.ai",
            "subject": "Invoiced: Cloud Infrastructure usage - June 2026",
            "body": (
                "Your invoice for Cloud Services in June 2026 is ready. Total due is $1,245.50. "
                "This will be automatically charged to your card ending in 4321 on July 25, 2026. "
                "If you have questions, please contact billing."
            ),
            "date": "Mon, 20 Jul 2026 13:00:00 -0400",
            "attachments": [
                {"filename": "invoice_june.pdf", "mime_type": "application/pdf", "size": 152420}
            ],
            "priority": "Read Later",
            "priority_score": 45,
            "category": "Finance",
            "summary": "June cloud usage invoice of $1,245.50 to be auto-charged on July 25, 2026.",
            "deadline": "2026-07-25",
            "action_items": [
                "Verify invoice details against usage dashboard",
                "Ensure credit card funds are available",
            ],
            "sentiment": "Neutral",
            "reason": (
                "Transactional invoice email. Automatic payment scheduled, "
                "no immediate manual action needed."
            ),
            "suggested_reply": "",
            "status": "read",
            "created_at": now - 7200,
        },
        {
            "gmail_id": "msg_003",
            "thread_id": "thread_003",
            "user_email": "demo@mailsort.ai",
            "sender": "john.client@partnercorp.com",
            "receiver": "demo@mailsort.ai",
            "subject": "Proposal request for integrations",
            "body": (
                "Hey, we loved your demo yesterday. Can you send over a detailed pricing proposal "
                "for 250 seats with API access? We want to make a decision by Friday. "
                "Let me know if you need a quick call to align."
            ),
            "date": "Mon, 20 Jul 2026 11:00:00 -0400",
            "attachments": [],
            "priority": "Reply Now",
            "priority_score": 85,
            "category": "Client",
            "summary": "Client requesting a pricing proposal for 250 seats with API access for decision by Friday.",
            "deadline": "Friday",
            "action_items": [
                "Draft pricing proposal for 250 seats",
                "Schedule alignment call if needed",
            ],
            "sentiment": "Positive",
            "reason": (
                "High business value proposal requested by a positive client. "
                "Decision timeline set for Friday."
            ),
            "suggested_reply": (
                "Hi John,\n\nThanks for the positive feedback! I'm glad you liked the demo. "
                "I am preparing the 250-seat proposal with API access and will send it over "
                "shortly. Would a brief call tomorrow morning at 10 AM help us align?\n\n"
                "Best,\nDemo"
            ),
            "status": "unread",
            "created_at": now - 14400,
        },
        {
            "gmail_id": "msg_004",
            "thread_id": "thread_004",
            "user_email": "demo@mailsort.ai",
            "sender": "newsletter@techtalk.io",
            "receiver": "demo@mailsort.ai",
            "subject": "Weekly Tech Digest: AI Agents, PyTorch 2.5, and Serverless databases",
            "body": (
                "Welcome to your weekly digest. This week, we cover the rise of autonomous "
                "coding assistants, model fine-tuning on a budget, and comparing serverless "
                "MongoDB with Postgres options. Read the full post on our blog."
            ),
            "date": "Sun, 19 Jul 2026 09:00:00 -0400",
            "attachments": [],
            "priority": "Ignore",
            "priority_score": 10,
            "category": "Newsletter",
            "summary": (
                "Weekly technology newsletter discussing autonomous coding tools, "
                "model fine-tuning, and serverless databases."
            ),
            "deadline": "",
            "action_items": [],
            "sentiment": "Positive",
            "reason": "Promotional weekly digest with educational content. Safe to read at leisure.",
            "suggested_reply": "",
            "status": "read",
            "created_at": now - 86400,
        },
        {
            "gmail_id": "msg_005",
            "thread_id": "thread_005",
            "user_email": "demo@mailsort.ai",
            "sender": "hr-alerts@company.com",
            "receiver": "demo@mailsort.ai",
            "subject": "Action Required: Complete Annual Security Compliance Training",
            "body": (
                "All employees are required to complete the 2026 Security Compliance module "
                "by July 30. It takes approximately 45 minutes. Failure to complete will result "
                "in access suspensions. Click here to launch the portal."
            ),
            "date": "Sat, 18 Jul 2026 10:00:00 -0400",
            "attachments": [],
            "priority": "Reply Now",
            "priority_score": 78,
            "category": "HR",
            "summary": (
                "Annual security compliance training must be completed by July 30 "
                "to avoid access suspension."
            ),
            "deadline": "2026-07-30",
            "action_items": ["Complete 45-minute Security Compliance training"],
            "sentiment": "Neutral",
            "reason": (
                "Mandatory HR action required with access suspension warning. "
                "Deadline is July 30."
            ),
            "suggested_reply": (
                "Hi HR Team,\n\nThank you for the reminder. I will complete the security "
                "compliance training before the July 30 deadline.\n\nBest,\nDemo"
            ),
            "status": "unread",
            "created_at": now - 172800,
        },
    ])

    _mock_users["demo@mailsort.ai"] = {
        "email": "demo@mailsort.ai",
        "name": "Demo User",
        "picture": "https://lh3.googleusercontent.com/a/default-user=s96-c",
        "credentials": {
            "token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "mock_client_id",
            "client_secret": "mock_client_secret",
            "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
        },
    }

    logger.info("Mock database seeded with demo data.")
