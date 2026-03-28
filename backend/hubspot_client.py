"""
HubSpot CRM integration for logging customer support sessions.

For every voice-chat session this module:
  1. Upserts a HubSpot Contact (by email, if available, else by name)
  2. Creates a Support Ticket linked to that contact
  3. Attaches the full conversation transcript as a Note

Required env var:
  HUBSPOT_ACCESS_TOKEN — from HubSpot > Settings > Integrations > Private apps
"""

import httpx
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN", "")
_BASE = "https://api.hubapi.com"
_HEADERS = {
    "Authorization": f"Bearer {_TOKEN}",
    "Content-Type": "application/json",
}


async def upsert_contact(
    email: str = "",
    firstname: str = "",
    lastname: str = "",
    phone: str = "",
) -> str | None:
    """
    Create or fetch a HubSpot contact.
    Returns the HubSpot contact ID, or None on failure.
    """
    if not _TOKEN:
        return None

    props: dict = {}
    if email:
        props["email"] = email
    if firstname:
        props["firstname"] = firstname
    if lastname:
        props["lastname"] = lastname
    if phone:
        props["phone"] = phone
    if not props:
        return None

    async with httpx.AsyncClient() as c:
        # Try to create
        r = await c.post(
            f"{_BASE}/crm/v3/objects/contacts",
            headers=_HEADERS,
            json={"properties": props},
            timeout=15,
        )
        if r.status_code == 201:
            return r.json().get("id")

        # 409 = already exists — extract the existing ID from the error message
        if r.status_code == 409:
            msg = r.json().get("message", "")
            if "existing ID: " in msg:
                existing_id = msg.split("existing ID: ")[-1].strip()
                return existing_id
            # Fall back: search by email
            if email:
                sr = await c.get(
                    f"{_BASE}/crm/v3/objects/contacts/search",
                    headers=_HEADERS,
                    params={"filterGroups": "", "query": email},
                    timeout=15,
                )
                results = sr.json().get("results", [])
                if results:
                    return results[0]["id"]

        print(f"HubSpot upsert_contact unexpected status {r.status_code}: {r.text[:200]}")
        return None


async def create_ticket(
    subject: str,
    body: str,
    contact_id: str | None = None,
    priority: str = "MEDIUM",
) -> str | None:
    """
    Create a HubSpot support ticket (pipeline stage: New).
    Returns the ticket ID, or None on failure.
    """
    if not _TOKEN:
        return None

    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{_BASE}/crm/v3/objects/tickets",
            headers=_HEADERS,
            json={
                "properties": {
                    "subject": subject,
                    "content": body,
                    "hs_ticket_priority": priority,
                    "hs_pipeline": "0",
                    "hs_pipeline_stage": "1",
                }
            },
            timeout=15,
        )
        if r.status_code not in (200, 201):
            print(f"HubSpot create_ticket error {r.status_code}: {r.text[:200]}")
            return None

        ticket_id = r.json().get("id")

        # Associate ticket → contact
        if ticket_id and contact_id:
            await c.post(
                f"{_BASE}/crm/v4/associations/ticket/contact/batch/create",
                headers=_HEADERS,
                json={
                    "inputs": [{
                        "from": {"id": ticket_id},
                        "to": {"id": contact_id},
                        "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 16}],
                    }]
                },
                timeout=15,
            )
        return ticket_id


async def log_conversation_note(
    contact_id: str,
    session_id: str,
    transcript: str,
) -> None:
    """Attach the full conversation transcript as a note on a HubSpot contact."""
    if not _TOKEN or not contact_id:
        return

    body = f"Support Session [{session_id}] — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n{transcript}"

    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{_BASE}/crm/v3/objects/notes",
            headers=_HEADERS,
            json={
                "properties": {
                    "hs_note_body": body,
                    "hs_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
                "associations": [{
                    "to": {"id": contact_id},
                    "types": [{
                        "associationCategory": "HUBSPOT_DEFINED",
                        "associationTypeId": 202,
                    }],
                }],
            },
            timeout=15,
        )
        if r.status_code not in (200, 201):
            print(f"HubSpot log_note error {r.status_code}: {r.text[:200]}")


async def log_support_session(
    session_id: str,
    customer_name: str,
    language: str,
    messages: list,  # list of LangChain message objects
) -> None:
    """
    High-level helper called at the end of each voice-chat turn:
    - Upserts a contact (by name when no email is available)
    - Creates a ticket for this session
    - Attaches a transcript note

    This is best-effort — failures are logged but never raise.
    """
    if not _TOKEN:
        return

    try:
        # Build transcript text
        lines = []
        for m in messages:
            role = "Customer" if m.__class__.__name__ == "HumanMessage" else "Agent"
            lines.append(f"{role}: {m.content}")
        transcript = "\n".join(lines)

        # Upsert contact by name (no email available from voice)
        parts = customer_name.split(" ", 1)
        contact_id = await upsert_contact(
            firstname=parts[0],
            lastname=parts[1] if len(parts) > 1 else "",
        )

        # Create ticket
        ticket_subject = f"Voice Support – {customer_name} [{language}]"
        ticket_body = f"Session ID: {session_id}\nLanguage: {language}\n\n{transcript[:2000]}"
        ticket_id = await create_ticket(
            subject=ticket_subject,
            body=ticket_body,
            contact_id=contact_id,
        )

        # Attach full note
        if contact_id:
            await log_conversation_note(contact_id, session_id, transcript)

    except Exception as e:
        print(f"HubSpot log_support_session error (non-fatal): {e}")
