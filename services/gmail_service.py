import base64
from googleapiclient.discovery import build
from services.oauth_service import build_google_credentials
from config import Config
from utils.helpers import logger

def fetch_gmail_emails(credentials_dict, user_email=None, max_results=15):
    """
    Fetches recent emails from Google Gmail API.
    If Config.MOCK_MODE is enabled or credentials_dict is dummy, returns mock emails.
    """
    if Config.MOCK_MODE or not credentials_dict or credentials_dict.get("token") == "mock_access_token":
        logger.info("MOCK_MODE: Simulating fetch_gmail_emails.")
        return _get_mock_gmail_data()
        
    try:
        creds = build_google_credentials(credentials_dict, user_email=user_email)
        if not creds:
            logger.warning("No valid OAuth credentials found. Falling back to mock data.")
            return _get_mock_gmail_data()
            
        service = build("gmail", "v1", credentials=creds)
        
        # 1. Fetch recent message list
        results = service.users().messages().list(userId="me", maxResults=max_results).execute()
        messages = results.get("messages", [])
        
        fetched_emails = []
        for msg in messages:
            try:
                # 2. Fetch full email details
                msg_detail = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
                email_data = parse_gmail_message(msg_detail)
                fetched_emails.append(email_data)
            except Exception as inner_e:
                logger.error(f"Error fetching detail for message {msg['id']}: {inner_e}")
                
        return fetched_emails
        
    except Exception as e:
        logger.error(f"Error connecting to Gmail API: {e}")
        # If API fails due to quota or invalid setup, we fallback gracefully to mock details
        logger.warning("Falling back to mock email feed due to Gmail API failure.")
        return _get_mock_gmail_data()

def parse_gmail_message(msg_detail):
    """Parses raw Gmail API message detail into a simplified dictionary structure."""
    gmail_id = msg_detail.get("id")
    thread_id = msg_detail.get("threadId")
    internal_date = int(msg_detail.get("internalDate", 0)) / 1000.0  # Unix timestamp
    
    payload = msg_detail.get("payload", {})
    headers = payload.get("headers", [])
    
    # Extract headers
    sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown Sender")
    receiver = next((h["value"] for h in headers if h["name"].lower() == "to"), "Unknown Receiver")
    subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "(No Subject)")
    date_str = next((h["value"] for h in headers if h["name"].lower() == "date"), "")
    
    # Extract body content (text/plain preferred, fallback text/html)
    body_text = extract_body(payload)
    
    # Extract attachment metadata
    attachments = []
    extract_attachments(payload, attachments)
    
    return {
        "gmail_id": gmail_id,
        "thread_id": thread_id,
        "sender": sender,
        "receiver": receiver,
        "subject": subject,
        "body": body_text,
        "date": date_str,
        "attachments": attachments,
        "created_at": internal_date
    }

def extract_body(payload):
    """Recursively walks through Gmail parts and extracts the plain text or HTML body."""
    body = ""
    parts = payload.get("parts", [])
    mime_type = payload.get("mimeType", "")
    
    if not parts:
        # Leaf part
        if mime_type in ["text/plain", "text/html"]:
            data = payload.get("body", {}).get("data", "")
            if data:
                try:
                    decoded = base64.urlsafe_b64decode(data.encode("ASCII"))
                    body = decoded.decode("utf-8", errors="ignore")
                except Exception as e:
                    logger.error(f"Error decoding base64 payload: {e}")
    else:
        # Multipart structure. We seek plain text first
        plain_text_parts = []
        html_parts = []
        
        def recurse_parts(parts_list):
            for part in parts_list:
                part_mime = part.get("mimeType", "")
                if part.get("parts"):
                    recurse_parts(part.get("parts"))
                elif part_mime == "text/plain":
                    plain_text_parts.append(part)
                elif part_mime == "text/html":
                    html_parts.append(part)
                    
        recurse_parts(parts)
        
        # Read text/plain if available, else text/html
        target_parts = plain_text_parts if plain_text_parts else html_parts
        for part in target_parts:
            part_body = part.get("body", {}).get("data", "")
            if part_body:
                try:
                    decoded = base64.urlsafe_b64decode(part_body.encode("ASCII"))
                    body += decoded.decode("utf-8", errors="ignore") + "\n"
                except Exception as e:
                    logger.error(f"Error decoding nested part base64: {e}")
                    
    # Clean up excess whitespace
    return body.strip()

def extract_attachments(part, attachments_list):
    """Recursively parses email parts to build a list of attachment metadata."""
    parts = part.get("parts", [])
    if parts:
        for p in parts:
            extract_attachments(p, attachments_list)
    else:
        filename = part.get("filename")
        if filename:
            mime_type = part.get("mimeType", "")
            body = part.get("body", {})
            size = body.get("size", 0)
            attachment_id = body.get("attachmentId", "")
            attachments_list.append({
                "filename": filename,
                "mime_type": mime_type,
                "size": size,
                "attachment_id": attachment_id
            })

def _get_mock_gmail_data():
    """Generates supplementary mock emails for testing, simulating new arrivals."""
    import time
    current_time = time.time()
    
    # We will simulate the same base list but update timestamps to represent new emails
    return [
        {
            "gmail_id": "msg_001",
            "thread_id": "thread_001",
            "sender": "sarah.manager@company.com",
            "receiver": "demo@mailsort.ai",
            "subject": "Urgent: Q3 Project Deliverables review",
            "body": "Hi team, we need the final slides for the Q3 project review by 5:00 PM today. Please make sure the finance spreadsheets are updated and the Client feedback is incorporated. Thanks, Sarah.",
            "date": "Mon, 20 Jul 2026 14:00:00 -0400",
            "attachments": [],
            "created_at": current_time - 3600
        },
        {
            "gmail_id": "msg_002",
            "thread_id": "thread_002",
            "sender": "billing@cloudservices.com",
            "receiver": "demo@mailsort.ai",
            "subject": "Invoiced: Cloud Infrastructure usage - June 2026",
            "body": "Your invoice for Cloud Services in June 2026 is ready. Total due is $1,245.50. This will be automatically charged to your card ending in 4321 on July 25, 2026. If you have questions, please contact billing.",
            "date": "Mon, 20 Jul 2026 13:00:00 -0400",
            "attachments": [{"filename": "invoice_june.pdf", "mime_type": "application/pdf", "size": 152420}],
            "created_at": current_time - 7200
        },
        {
            "gmail_id": "msg_003",
            "thread_id": "thread_003",
            "sender": "john.client@partnercorp.com",
            "receiver": "demo@mailsort.ai",
            "subject": "Proposal request for integrations",
            "body": "Hey, we loved your demo yesterday. Can you send over a detailed pricing proposal for 250 seats with API access? We want to make a decision by Friday. Let me know if you need a quick call to align.",
            "date": "Mon, 20 Jul 2026 11:00:00 -0400",
            "attachments": [],
            "created_at": current_time - 14400
        },
        {
            "gmail_id": "msg_006", # New email simulated during refresh!
            "thread_id": "thread_006",
            "sender": "recruit@dreamjob.com",
            "receiver": "demo@mailsort.ai",
            "subject": "Interview scheduling for Senior Engineer position",
            "body": "Hello, we were highly impressed by your portfolio and would like to schedule a 45-minute technical interview this week. Please let us know your availability for Wednesday and Thursday between 9 AM and 3 PM. Best, Recruiter.",
            "date": "Mon, 20 Jul 2026 17:30:00 -0400",
            "attachments": [],
            "created_at": current_time
        }
    ]
