from fastmcp import FastMCP

# NOTE: The MCP instance will be passed in during registration
def register(mcp: FastMCP):
    @mcp.tool
    def weather_forecast(latitude: float, longitude: float):
        """
        Get current weather + 24h forecast from Open-Meteo.
        """
        import requests
        
        BASE_URL = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": True,
            "hourly": "temperature_2m,precipitation,weather_code",
        }

        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
