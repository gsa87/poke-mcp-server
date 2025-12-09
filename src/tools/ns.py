import os
import requests
import json
from fastmcp import FastMCP

def register_ns(mcp: FastMCP):
    """
    Registers NS (Dutch Railways) tools with the MCP server.
    """
    
    BASE_URL = "https://gateway.apiportal.ns.nl"
    
    def get_headers():
        # Retrieve the API key from environment variables
        api_key = os.environ.get("NS_API_KEY")
        if not api_key:
            print("CRITICAL: NS_API_KEY is missing from environment variables.")
            raise ValueError("NS_API_KEY environment variable is missing.")
            
        return {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": "application/json",
            # Mimic a real Chrome browser to avoid 500/403 blocks
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def resolve_station_code(station_name: str) -> str:
        """
        Helper to resolve a station name (e.g., "Rotterdam Centraal") to its code (e.g., "RTD").
        Returns None if resolution fails.
        """
        # If it looks like a short code already (2-6 chars, all caps usually), assume it is a code
        clean_name = station_name.strip()
        if len(clean_name) <= 6 and clean_name.isupper():
            return clean_name

        print(f"DEBUG: Resolving code for station name: {station_name}")
        endpoint = f"{BASE_URL}/nsapp-stations/v3"
        params = {"q": station_name, "limit": 1}
        
        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # FIX: The API wraps results in a "payload" list. 
            # We must check for this wrapper to avoid a crash.
            results = data.get("payload") if "payload" in data else data
            
            if results and isinstance(results, list) and len(results) > 0:
                # The first result is the best match found by the NS search algorithm
                first_match = results[0]
                code = first_match.get("code") # We use the 'code' (RTD), but 'UICCode' (8400530) would also work.
                
                print(f"DEBUG: Resolved '{station_name}' to code '{code}'")
                return code
                
        except Exception as e:
            print(f"WARNING: Could not resolve station code: {e}")
        
        # STRICT MODE: Return None if we couldn't find a code. 
        return None

    @mcp.tool
    def ns_plan_trip(origin: str, destination: str, date_time: str = None, is_arrival: bool = False):
        """
        Plan a train journey between two stations.
        """
        print(f"DEBUG: Starting ns_plan_trip from {origin} to {destination}")
        
        origin_code = resolve_station_code(origin)
        if not origin_code:
            return f"Error: Could not find station code for origin '{origin}'."
            
        dest_code = resolve_station_code(destination)
        if not dest_code:
             return f"Error: Could not find station code for destination '{destination}'."

        endpoint = f"{BASE_URL}/reisinformatie-api/api/v3/trips"
        
        params = {
            "fromStation": origin_code,
            "toStation": dest_code,
        }
        
        if date_time:
            params["dateTime"] = date_time
            params["searchForArrival"] = str(is_arrival).lower()

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            trips = data.get("trips", [])
            print(f"DEBUG: Success. Found {len(trips)} trips.")
            return trips
        except Exception as e:
            return f"Error in ns_plan_trip: {str(e)}"

    @mcp.tool
    def ns_get_departures(station: str, lang: str = "nl"):
        """
        Get real-time departure information for a specific station.
        """
        print(f"DEBUG: Starting ns_get_departures for {station}")
        
        station_code = resolve_station_code(station)
        
        if not station_code:
            return f"Error: Could not find a station code for '{station}'. Please check the spelling or provide the station code (e.g., 'ASD')."
        
        endpoint = f"{BASE_URL}/reisinformatie-api/api/v2/departures"
        
        params = {
            "station": station_code,
            "lang": lang,
            "maxJourneys": 15 
        }

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            
            # Catch 500 specific errors to give a better hint
            if response.status_code == 500:
                return f"NS API returned 500 Internal Server Error. The station code '{station_code}' might be invalid."

            response.raise_for_status()
            data = response.json()
            departures = data.get("payload", {}).get("departures", [])
            print(f"DEBUG: Success. Found {len(departures)} departures.")
            return departures
        except Exception as e:
            print(f"ERROR: ns_get_departures failed: {str(e)}")
            return f"Error in ns_get_departures: {str(e)}"

    @mcp.tool
    def ns_get_arrivals(station: str, lang: str = "nl"):
        """
        Get real-time arrival information for a specific station.
        """
        print(f"DEBUG: Starting ns_get_arrivals for {station}")
        
        station_code = resolve_station_code(station)
        
        if not station_code:
             return f"Error: Could not find a station code for '{station}'. Please check the spelling."

        endpoint = f"{BASE_URL}/reisinformatie-api/api/v2/arrivals"
        
        params = {
            "station": station_code,
            "lang": lang,
            "maxJourneys": 15
        }

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            arrivals = data.get("payload", {}).get("arrivals", [])
            print(f"DEBUG: Success. Found {len(arrivals)} arrivals.")
            return arrivals
        except Exception as e:
            print(f"ERROR: ns_get_arrivals failed: {str(e)}")
            return f"Error in ns_get_arrivals: {str(e)}"

    @mcp.tool
    def ns_check_disruptions(station: str = None, active: bool = True):
        """
        Check for current engineering work or disruptions.
        """
        print(f"DEBUG: Starting ns_check_disruptions for {station or 'entire network'}")
        
        if station:
            resolved_code = resolve_station_code(station)
            if resolved_code:
                station = resolved_code
            else:
                return f"Error: Could not find station code for '{station}' to check disruptions."

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
        except Exception as e:
            print(f"ERROR: ns_check_disruptions failed: {str(e)}")
            return f"Error in ns_check_disruptions: {str(e)}"

    @mcp.tool
    def ns_get_prices(origin: str, destination: str, date: str = None, travel_class: str = "SECOND_CLASS"):
        """
        Get ticket price information for a journey.
        """
        print(f"DEBUG: Starting ns_get_prices {origin}->{destination}")
        
        origin_code = resolve_station_code(origin)
        if not origin_code:
            return f"Error: Could not find station code for origin '{origin}'."
            
        dest_code = resolve_station_code(destination)
        if not dest_code:
             return f"Error: Could not find station code for destination '{destination}'."

        endpoint = f"{BASE_URL}/reisinformatie-api/api/v3/price"
        
        params = {
            "fromStation": origin_code,
            "toStation": dest_code,
            "travelClass": travel_class,
            "travelType": "single",
            "adults": 1
        }
        
        if date:
            params["dateTime"] = date

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"ERROR: ns_get_prices failed: {str(e)}")
            return f"Error in ns_get_prices: {str(e)}"

    @mcp.tool
    def ns_get_ov_fiets(station_code: str):
        """
        Check availability of OV-fiets (rental bikes) at a specific station.
        """
        resolved = resolve_station_code(station_code)
        if not resolved:
             return f"Error: Could not find station code for '{station_code}' to check OV-fiets."

        print(f"DEBUG: Starting ns_get_ov_fiets for {resolved}")
        endpoint = f"{BASE_URL}/places-api/v2/ovfiets"
        
        params = {
            "station_code": resolved
        }

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"ERROR: ns_get_ov_fiets failed: {str(e)}")
            return f"Error in ns_get_ov_fiets: {str(e)}"

    @mcp.tool
    def ns_search_stations(query: str):
        """
        Search for station details. Useful for finding the 'station_code'.
        """
        print(f"DEBUG: Starting ns_search_stations for {query}")
        endpoint = f"{BASE_URL}/nsapp-stations/v3"
        
        params = {
            "q": query,
            "limit": 5
        }

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"ERROR: ns_search_stations failed: {str(e)}")
            return f"Error in ns_search_stations: {str(e)}"