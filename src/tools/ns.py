import os
import requests
from fastmcp import FastMCP

def register_ns(mcp: FastMCP):
    """
    Registers NS (Dutch Railways) tools with the MCP server.
    Ported functionality from the JS NS-MCP-Server implementation.
    """
    
    # Base URL for all NS API calls
    BASE_URL = "https://gateway.apiportal.ns.nl"
    
    # Helper to get the API key safely
    def get_headers():
        api_key = os.environ.get("NS_API_KEY")
        if not api_key:
            raise ValueError("NS_API_KEY environment variable is not set on the server.")
        return {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": "application/json"
        }

    @mcp.tool
    def ns_plan_trip(origin: str, destination: str, date_time: str = None, is_arrival: bool = False):
        """
        Plan a train journey between two stations (Travel Advice).
        
        Args:
            origin: Name of the departure station (e.g., "Amsterdam Centraal")
            destination: Name of the arrival station (e.g., "Utrecht Centraal")
            date_time: (Optional) ISO 8601 formatted date/time (e.g., "2023-10-27T14:00:00"). Defaults to now.
            is_arrival: (Optional) If True, the date_time is the arrival time. Defaults to False (departure time).
        """
        endpoint = f"{BASE_URL}/reisinformatie-api/api/v3/trips"
        
        params = {
            "fromStation": origin,
            "toStation": destination,
        }
        
        if date_time:
            params["dateTime"] = date_time
            params["searchForArrival"] = str(is_arrival).lower()

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("trips", [])
        except requests.exceptions.RequestException as e:
            return f"Error connecting to NS API: {str(e)}"

    @mcp.tool
    def ns_get_departures(station: str, lang: str = "nl"):
        """
        Get real-time departure information for a specific station.
        
        Args:
            station: Name of the station (e.g., "Rotterdam Centraal")
            lang: Language for messages ('nl' or 'en'). Defaults to 'nl'.
        """
        endpoint = f"{BASE_URL}/reisinformatie-api/api/v2/departures"
        
        params = {
            "station": station,
            "lang": lang
        }

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("payload", {}).get("departures", [])
        except requests.exceptions.RequestException as e:
            return f"Error fetching departures: {str(e)}"

    @mcp.tool
    def ns_get_arrivals(station: str, lang: str = "nl"):
        """
        Get real-time arrival information for a specific station.
        
        Args:
            station: Name of the station (e.g., "Utrecht Centraal")
            lang: Language for messages ('nl' or 'en'). Defaults to 'nl'.
        """
        endpoint = f"{BASE_URL}/reisinformatie-api/api/v2/arrivals"
        
        params = {
            "station": station,
            "lang": lang
        }

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("payload", {}).get("arrivals", [])
        except requests.exceptions.RequestException as e:
            return f"Error fetching arrivals: {str(e)}"

    @mcp.tool
    def ns_check_disruptions(station: str = None, active: bool = True):
        """
        Check for current engineering work (werkzaamheden) or disruptions (storingen).
        
        Args:
            station: (Optional) Limit check to a specific station area. If empty, checks generic network status.
            active: (Optional) Only show active disruptions. Defaults to True.
        """
        endpoint = f"{BASE_URL}/disruptions/v3"
        
        params = {
            "isActive": str(active).lower()
        }
        if station:
            params["station"] = station

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return f"Error fetching disruptions: {str(e)}"

    @mcp.tool
    def ns_get_prices(origin: str, destination: str, date: str = None, travel_class: str = "SECOND_CLASS"):
        """
        Get ticket price information for a journey.
        
        Args:
            origin: Departure station
            destination: Arrival station
            date: (Optional) Date for pricing (ISO 8601 string). Defaults to today.
            travel_class: "FIRST_CLASS" or "SECOND_CLASS". Defaults to "SECOND_CLASS".
        """
        endpoint = f"{BASE_URL}/reisinformatie-api/api/v3/price"
        
        params = {
            "fromStation": origin,
            "toStation": destination,
            "travelClass": travel_class,
            "travelType": "single", # Defaulting to single trip for simplicity
            "adults": 1
        }
        
        # Note: Pricing often requires a date to determine peak/off-peak rates
        if date:
            params["dateTime"] = date

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return f"Error fetching prices: {str(e)}"

    @mcp.tool
    def ns_get_ov_fiets(station_code: str):
        """
        Check availability of OV-fiets (rental bikes) at a specific station.
        
        Args:
            station_code: The station code (e.g., 'ut' for Utrecht, 'asd' for Amsterdam).
        """
        endpoint = f"{BASE_URL}/places-api/v2/ovfiets"
        
        params = {
            "station_code": station_code
        }

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return f"Error fetching OV-fiets info: {str(e)}"

    @mcp.tool
    def ns_search_stations(query: str):
        """
        Search for station details, including location and facilities.
        Useful for finding the 'station_code' needed for OV-fiets lookups.
        
        Args:
            query: Search term (e.g., "Amsterdam" or "asd")
        """
        endpoint = f"{BASE_URL}/nsapp-stations/v3"
        
        params = {
            "q": query,
            "limit": 5
        }

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return f"Error searching stations: {str(e)}"