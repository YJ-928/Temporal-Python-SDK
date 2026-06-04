"""
Email Sender Agent Service

A self-contained FastAPI application that simulates email sending.
This is a MOCK service - no actual SMTP, Gmail, or external provider.
Sent emails are persisted to JSON for testing purposes.

Port: 11002
Endpoint: POST /execute

Example Request:
    POST http://localhost:11002/execute
    {"to": "user@gmail.com", "subject": "Welcome", "body": "Hello"}

Example Response:
    {"success": true, "message_id": "550e8400-e29b-41d4-a716-446655440000"}
"""
import json
import uuid
import uvicorn
from datetime import datetime, UTC
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# Import project logger
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.config import get_logger


logger = get_logger(__name__)

app = FastAPI(
    title="Email Sender Agent Service",
    description="Mock email sending service with JSON persistence",
    version="1.0.0"
)


# Path to sent emails storage
SENT_EMAILS_PATH = Path(__file__).parent.parent / "data" / "runtime_data" / "sent_emails.json"


def load_sent_emails() -> list:
    """Load sent emails from JSON file."""
    try:
        if SENT_EMAILS_PATH.exists():
            with open(SENT_EMAILS_PATH, "r") as f:
                return json.load(f)
        return []
    except json.JSONDecodeError:
        logger.error("Invalid JSON in sent_emails.json, returning empty list")
        return []


def save_sent_email(email_data: dict) -> None:
    """Persist a sent email to JSON file."""
    try:
        emails = load_sent_emails()
        emails.append(email_data)
        with open(SENT_EMAILS_PATH, "w") as f:
            json.dump(emails, f, indent=2)
        logger.info(f"Email saved to {SENT_EMAILS_PATH}")
    except Exception as e:
        logger.error(f"Failed to save email: {e}")
        raise


# Pydantic Models
class EmailSendRequest(BaseModel):
    """Email sending request."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "to": "user@gmail.com",
                "subject": "Welcome",
                "body": "Hello, welcome to our service!"
            }
        }
    )

    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body content")


class EmailSendResponse(BaseModel):
    """Email sending response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )

    success: bool = Field(..., description="Whether the email was sent successfully")
    message_id: Optional[str] = Field(None, description="Unique message identifier")
    message: Optional[str] = Field(None, description="Status or error message")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Email Sender Agent",
        "status": "running",
        "port": 11002,
        "endpoint": "/execute",
        "storage": str(SENT_EMAILS_PATH)
    }


@app.get("/sent")
async def list_sent_emails():
    """List all sent emails from storage."""
    emails = load_sent_emails()
    return {
        "sent_emails": emails,
        "count": len(emails)
    }


@app.post("/execute", response_model=EmailSendResponse)
async def execute(request: EmailSendRequest) -> EmailSendResponse:
    """
    Mock email sending with JSON persistence.

    Args:
        request: EmailSendRequest with to, subject, and body

    Returns:
        EmailSendResponse with message_id
    """
    logger.info(f"Email send request to: {request.to}, subject: {request.subject}")

    # Generate unique message ID
    message_id = str(uuid.uuid4())

    # Create email record
    email_record = {
        "message_id": message_id,
        "to": request.to,
        "subject": request.subject,
        "body": request.body,
        "timestamp": datetime.now(UTC).isoformat(),
        "status": "sent"
    }

    try:
        # Persist to JSON
        save_sent_email(email_record)

        logger.info(f"Email sent successfully: {message_id}")

        return EmailSendResponse(
            success=True,
            message_id=message_id,
            message=f"Email sent to {request.to}"
        )

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {str(e)}"
        )


if __name__ == "__main__":
    logger.info("Starting Email Sender Agent Service on port 11002...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=11002,
        log_level="info"
    )
