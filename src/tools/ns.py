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
            # Log this critical error
            print("CRITICAL: NS_API_KEY is missing from environment variables.")
            raise ValueError("NS_API_KEY environment variable is missing. Please check your Render settings.")
            
        return {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": "application/json",
            # mimic a standard browser to avoid being blocked/throttled
            "User-Agent": "Mozilla/5.0 (compatible; NS-MCP-Server/1.0)" 
        }

    @mcp.tool
    def ns_plan_trip(origin: str, destination: str, date_time: str = None, is_arrival: bool = False):
        """
        Plan a train journey between two stations (Travel Advice).
        """
        print(f"DEBUG: Starting ns_plan_trip from {origin} to {destination}")
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
            trips = data.get("trips", [])
            print(f"DEBUG: Success. Found {len(trips)} trips.")
            return trips
        except Exception as e:
            print(f"ERROR: ns_plan_trip failed: {str(e)}")
            return f"Error in ns_plan_trip: {str(e)}"

    @mcp.tool
    def ns_get_departures(station: str, lang: str = "nl"):
        """
        Get real-time departure information for a specific station.
        """
        print(f"DEBUG: Starting ns_get_departures for {station}")
        endpoint = f"{BASE_URL}/reisinformatie-api/api/v2/departures"
        
        params = {
            "station": station,
            "lang": lang,
            "maxJourneys": 15 # Limit results to prevent timeouts on large payloads
        }

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
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
        endpoint = f"{BASE_URL}/reisinformatie-api/api/v2/arrivals"
        
        params = {
            "station": station,
            "lang": lang,
            "maxJourneys": 15 # Limit results to prevent timeouts
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
        Check for current engineering work (werkzaamheden) or disruptions (storingen).
        """
        print(f"DEBUG: Starting ns_check_disruptions for {station or 'entire network'}")
        endpoint = f"{BASE_URL}/disruptions/v3"
        
        params = {
            "isActive": str(active).lower()
        }
        if station:
            params["station"] = station

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            print("DEBUG: Success. Found disruptions data.")
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
        endpoint = f"{BASE_URL}/reisinformatie-api/api/v3/price"
        
        params = {
            "fromStation": origin,
            "toStation": destination,
            "travelClass": travel_class,
            "travelType": "single",
            "adults": 1
        }
        
        if date:
            params["dateTime"] = date

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            print("DEBUG: Success. Found price data.")
            return response.json()
        except Exception as e:
            print(f"ERROR: ns_get_prices failed: {str(e)}")
            return f"Error in ns_get_prices: {str(e)}"

    @mcp.tool
    def ns_get_ov_fiets(station_code: str):
        """
        Check availability of OV-fiets (rental bikes) at a specific station.
        """
        print(f"DEBUG: Starting ns_get_ov_fiets for {station_code}")
        endpoint = f"{BASE_URL}/places-api/v2/ovfiets"
        
        params = {
            "station_code": station_code
        }

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            print("DEBUG: Success. Found OV-fiets data.")
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
            print("DEBUG: Success. Found station search results.")
            return response.json()
        except Exception as e:
            print(f"ERROR: ns_search_stations failed: {str(e)}")
            return f"Error in ns_search_stations: {str(e)}"