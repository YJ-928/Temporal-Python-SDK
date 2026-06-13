"""
Weather Agent Service

A self-contained FastAPI application that simulates an external weather service.
This agent can be called by the workflow executor over HTTP.

Port: 11000
Endpoint: POST /execute

Example Request:
    POST http://localhost:11000/execute
    {"city": "hyderabad"}

Example Response:
    {"success": true, "city": "Hyderabad", "temperature": 35, "condition": "Sunny"}
"""
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# Import project logger
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.config import get_logger


logger = get_logger(__name__)

app = FastAPI(
    title="Weather Agent Service",
    description="Demo agent service for weather data simulation",
    version="1.0.0"
)


# Load weather data from JSON file
def load_weather_data():
    """Load weather data from data/agent_data/weather_data.json"""
    data_path = Path(__file__).parent.parent / "data" / "agent_data" / "weather_data.json"
    try:
        with data_path.open("r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Weather data file not found: {data_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in weather data file: {e}")
        return {}


WEATHER_DATA = load_weather_data()


# Pydantic Models
class WeatherRequest(BaseModel):
    """Weather query request."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "city": "hyderabad"
            }
        }
    )

    city: str = Field(..., description="City name to query weather for")


class WeatherResponse(BaseModel):
    """Weather query response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "city": "Hyderabad",
                "temperature": 35,
                "condition": "Sunny"
            }
        }
    )

    success: bool = Field(..., description="Whether the request was successful")
    city: Optional[str] = Field(None, description="Capitalized city name")
    temperature: Optional[int] = Field(None, description="Temperature in Celsius")
    condition: Optional[str] = Field(None, description="Weather condition")
    message: Optional[str] = Field(None, description="Error message if request failed")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Weather Agent",
        "status": "running",
        "port": 11000,
        "endpoint": "/execute"
    }


@app.post("/execute", response_model=WeatherResponse)
async def execute(request: WeatherRequest) -> WeatherResponse:
    """
    Execute weather query for a given city.

    Args:
        request: WeatherRequest with city name

    Returns:
        WeatherResponse with weather data or error message

    Raises:
        HTTPException: 404 if city not found
    """
    city_lower = request.city.lower().strip()

    logger.info(f"Weather query received for city: {request.city}")

    # Check if city exists in our database
    if city_lower not in WEATHER_DATA:
        logger.warning(f"City not found: {request.city}")
        raise HTTPException(
            status_code=404,
            detail=f"City not found: {request.city}"
        )

    # Retrieve weather data
    weather = WEATHER_DATA[city_lower]
    city_capitalized = request.city.capitalize()

    response = WeatherResponse(
        success=True,
        city=city_capitalized,
        temperature=weather["temperature"],
        condition=weather["condition"]
    )

    logger.info(
        f"Weather data returned for {city_capitalized}: "
        f"{weather['temperature']}°C, {weather['condition']}"
    )

    return response


@app.get("/cities")
async def list_cities():
    """List all available cities in the weather database."""
    cities = [city.capitalize() for city in WEATHER_DATA]
    return {
        "available_cities": cities,
        "count": len(cities)
    }


if __name__ == "__main__":
    logger.info("Starting Weather Agent Service on port 11000...")
    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104
        port=11000,
        log_level="info"
    )
