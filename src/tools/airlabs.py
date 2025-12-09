import os
import requests
from fastmcp import FastMCP

def register_airlabs(mcp: FastMCP):
    """
    Registers AirLabs (Flight Data) tools with the MCP server.
    """
    
    BASE_URL = "https://airlabs.co/api/v9"
    
    def get_api_key():
        api_key = os.environ.get("AIRLABS_API_KEY")
        if not api_key:
            print("CRITICAL: AIRLABS_API_KEY is missing from environment variables.")
            raise ValueError("AIRLABS_API_KEY environment variable is missing.")
        return api_key

    @mcp.tool
    def airlabs_get_flight_status(flight_iata: str):
        """
        Get real-time status, departure, and arrival information for a specific flight.
        
        Args:
            flight_iata: The IATA flight number (e.g., "KL601", "UA960").
        """
        print(f"DEBUG: Getting flight status for {flight_iata}")
        endpoint = f"{BASE_URL}/flight"
        
        params = {
            "api_key": get_api_key(),
            "flight_iata": flight_iata
        }

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            
            if response.status_code == 403:
                return "Error: AirLabs API Key is invalid or expired."
            
            if response.status_code == 404:
                return f"Flight {flight_iata} is not currently active or tracked live. Try checking the schedule."

            response.raise_for_status()
            data = response.json()
            
            flight_info = data.get("response")
            
            if not flight_info:
                return f"No live tracking information found for flight {flight_iata}."
                
            if isinstance(flight_info, list) and len(flight_info) > 0:
                return flight_info[0]
            
            return flight_info

        except Exception as e:
            return f"Error fetching flight status: {str(e)}"

    @mcp.tool
    def airlabs_get_schedules(dep_iata: str = None, arr_iata: str = None, date: str = None):
        """
        Get flight schedules between two airports.
        
        Args:
            dep_iata: (Optional) Departure airport IATA code (e.g., "AMS").
            arr_iata: (Optional) Arrival airport IATA code (e.g., "SFO").
            date: (Optional) Date in YYYY-MM-DD format. Defaults to today.
        """
        print(f"DEBUG: Getting schedules for {dep_iata} -> {arr_iata}")
        endpoint = f"{BASE_URL}/schedules"
        
        params = {
            "api_key": get_api_key(),
        }
        if dep_iata: params["dep_iata"] = dep_iata
        if arr_iata: params["arr_iata"] = arr_iata
        if date: params["date"] = date
        
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("response", [])
        except Exception as e:
            return f"Error fetching schedules: {str(e)}"

    @mcp.tool
    def airlabs_search_airports(query: str):
        """
        Search for an airport by name, city, or code to get its IATA code.
        Useful when the user says 'London' instead of 'LHR'.
        
        Args:
            query: Name of city or airport (e.g. "New York", "Heathrow", "Paris")
        """
        print(f"DEBUG: Searching airports for '{query}'")
        # AirLabs doesn't have a fuzzy 'search' endpoint, so we use the 'suggest' endpoint
        # or we filter the airports DB. 'suggest' is usually better for autocomplete-style queries.
        endpoint = f"{BASE_URL}/suggest"
        
        params = {
            "api_key": get_api_key(),
            "q": query
        }

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # The suggest endpoint returns airports, cities, etc. We filter for airports.
            suggestions = data.get("response", {}).get("airports", [])
            return suggestions
        except Exception as e:
            return f"Error searching airports: {str(e)}"

    @mcp.tool
    def airlabs_get_airport_delays(airport_iata: str):
        """
        Get current delay information and delayed flights for a specific airport.
        
        Args:
            airport_iata: The IATA code of the airport (e.g., "AMS", "JFK").
        """
        print(f"DEBUG: Getting delays for {airport_iata}")
        endpoint = f"{BASE_URL}/delays"
        
        params = {
            "api_key": get_api_key(),
            "dep_iata": airport_iata, # Check departures from this airport
            "delay": 30 # Only show flights delayed by more than 30 mins
        }

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            delays = data.get("response", [])
            
            if not delays:
                return f"No significant delays (>30min) reported for departures from {airport_iata} right now."
            
            return delays
        except Exception as e:
            return f"Error fetching delays: {str(e)}"