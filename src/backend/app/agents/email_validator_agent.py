"""
Email Validator Agent Service

A self-contained FastAPI application that validates email addresses using regex patterns.
This agent can be called by the workflow executor over HTTP.

Port: 11001
Endpoint: POST /execute

Example Request:
    POST http://localhost:11001/execute
    {"email": "user@gmail.com"}

Example Response:
    {"success": true, "is_valid": true, "domain": "gmail.com"}
"""
import re
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# Import project logger
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.config import get_logger


logger = get_logger(__name__)

app = FastAPI(
    title="Email Validator Agent Service",
    description="Demo agent service for email validation",
    version="1.0.0"
)


# RFC 5322 compliant email regex (simplified for demo purposes)
EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)


# Pydantic Models
class EmailValidationRequest(BaseModel):
    """Email validation request."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@gmail.com"
            }
        }
    )

    email: str = Field(..., description="Email address to validate")


class EmailValidationResponse(BaseModel):
    """Email validation response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "is_valid": True,
                "domain": "gmail.com"
            }
        }
    )

    success: bool = Field(..., description="Whether the request was successful")
    is_valid: bool = Field(..., description="Whether the email is valid")
    domain: Optional[str] = Field(None, description="Email domain if valid")
    message: Optional[str] = Field(None, description="Error or info message")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Email Validator Agent",
        "status": "running",
        "port": 11001,
        "endpoint": "/execute"
    }


@app.post("/execute", response_model=EmailValidationResponse)
async def execute(request: EmailValidationRequest) -> EmailValidationResponse:
    """
    Validate an email address using regex patterns.

    Args:
        request: EmailValidationRequest with email address

    Returns:
        EmailValidationResponse with validation result
    """
    email = request.email.strip()

    logger.info(f"Email validation request for: {email}")

    # Validate email using regex
    is_valid = bool(EMAIL_REGEX.match(email))

    # Extract domain if valid
    domain = None
    if is_valid:
        domain = email.split("@")[1]
        logger.info(f"Email valid: {email} (domain: {domain})")
    else:
        logger.warning(f"Invalid email format: {email}")

    response = EmailValidationResponse(
        success=True,
        is_valid=is_valid,
        domain=domain,
        message="Email validated successfully" if is_valid else "Invalid email format"
    )

    return response


if __name__ == "__main__":
    logger.info("Starting Email Validator Agent Service on port 11001...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=11001,
        log_level="info"
    )
