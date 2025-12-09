import os
import requests
import json
import difflib
from fastmcp import FastMCP

def register_ns(mcp: FastMCP):
    """
    Registers NS (Dutch Railways) tools with the MCP server.
    """
    
    BASE_URL = "https://gateway.apiportal.ns.nl"
    
    def get_headers():
        api_key = os.environ.get("NS_API_KEY")
        if not api_key:
            print("CRITICAL: NS_API_KEY is missing from environment variables.")
            raise ValueError("NS_API_KEY environment variable is missing.")
            
        return {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def resolve_station_code(station_name: str) -> str:
        """
        Robustly resolve a station name to its code.
        Strategy:
        1. Direct Bypass: If it looks like a code (UIC digits or short uppercase), use it directly.
        2. API Search: Query the NS Stations API.
        3. Local Fallback: Fetch all stations and fuzzy match if API search fails.
        """
        if not station_name:
            return None
            
        clean_name = station_name.strip()
        
        # --- STRATEGY 1: DIRECT BYPASS ---
        # If it is a UIC Code (all digits), trust it immediately.
        if clean_name.isdigit():
            print(f"DEBUG: '{clean_name}' detected as UIC code. Bypassing resolution.")
            return clean_name
            
        # If it is a short, uppercase string (e.g. "ASD", "RTD", "UT"), treat as Station Code.
        if len(clean_name) <= 6 and clean_name.isupper():
            print(f"DEBUG: '{clean_name}' detected as Station Code. Bypassing resolution.")
            return clean_name

        # --- STRATEGY 2: API SEARCH ---
        print(f"DEBUG: Resolving station name '{clean_name}' via API...")
        endpoint = f"{BASE_URL}/nsapp-stations/v3"
        
        try:
            params = {"q": clean_name, "limit": 1}
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Robustly unwrap the response (API wraps list in "payload" object)
            results = data.get("payload") if "payload" in data else data
            
            if results and isinstance(results, list) and len(results) > 0:
                code = results[0].get("code")
                print(f"DEBUG: API Search resolved '{clean_name}' -> '{code}'")
                return code
            else:
                print(f"DEBUG: API Search returned no results for '{clean_name}'.")
                
        except Exception as e:
            print(f"WARNING: API search failed: {e}")

        # --- STRATEGY 3: LOCAL FALLBACK (Fuzzy Match) ---
        print(f"DEBUG: Attempting local fuzzy match fallback for '{clean_name}'...")
        try:
            # Fetch all stations (no 'q' param)
            response = requests.get(endpoint, headers=get_headers(), timeout=10)
            response.raise_for_status()
            data = response.json()
            all_stations = data.get("payload") if "payload" in data else data
            
            if not all_stations:
                print("ERROR: Failed to retrieve station list for fallback.")
                return None

            # Build a local search index
            station_map = {}
            for s in all_stations:
                code = s.get("code")
                names = s.get("namen", {})
                if names.get("lang"): station_map[names.get("lang").lower()] = code
                if names.get("middel"): station_map[names.get("middel").lower()] = code
                if names.get("kort"): station_map[names.get("kort").lower()] = code
                for syn in s.get("synoniemen", []):
                    station_map[syn.lower()] = code

            search_key = clean_name.lower()
            
            # Exact Match
            if search_key in station_map:
                return station_map[search_key]

            # Fuzzy Match
            matches = difflib.get_close_matches(search_key, station_map.keys(), n=1, cutoff=0.6)
            if matches:
                found_code = station_map[matches[0]]
                print(f"DEBUG: Local Fuzzy Match found: '{clean_name}' -> '{found_code}'")
                return found_code

        except Exception as e:
            print(f"ERROR: Local fallback logic failed: {e}")

        return None

    @mcp.tool
    def ns_plan_trip(origin: str, destination: str, date_time: str = None, is_arrival: bool = False):
        """
        Plan a train journey between two stations. 
        Prioritizes Intercity Direct (ICD) and EuroCity (ECC) trains if available.
        """
        print(f"DEBUG: Starting ns_plan_trip {origin} -> {destination}")
        
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

            # --- SMART SORTING LOGIC ---
            # We want to boost ICD (Intercity Direct) and ECC (EuroCity) to the top.
            # We also want to push cancelled trains to the bottom.
            preferred_codes = ["ICD", "ECC"]

            def get_trip_score(trip):
                # 1. Check Cancellation Status
                # "status" field is usually "NORMAL" or "CANCELLED"
                is_cancelled = trip.get("status") == "CANCELLED"
                
                # 2. Check for Preferred Train Types in any leg of the journey
                has_preferred = False
                for leg in trip.get("legs", []):
                    prod = leg.get("product", {})
                    # Check both code and name just to be safe
                    cat_code = prod.get("categoryCode", "")
                    if cat_code in preferred_codes:
                        has_preferred = True
                        break
                
                # Scoring Logic (Higher is better)
                if has_preferred and not is_cancelled:
                    return 3 # Best: High Speed & Running
                elif not has_preferred and not is_cancelled:
                    return 2 # Good: Normal Train & Running (Fallback)
                elif has_preferred and is_cancelled:
                    return 1 # Bad: High Speed but Cancelled
                else:
                    return 0 # Worst: Normal & Cancelled

            # Sort trips based on the score, descending. 
            # Python's sort is stable, so original time order is preserved within groups.
            trips.sort(key=get_trip_score, reverse=True)

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
            return f"Error: Could not find a station code for '{station}'."
        
        endpoint = f"{BASE_URL}/reisinformatie-api/api/v2/departures"
        params = {
            "station": station_code,
            "lang": lang,
            "maxJourneys": 15 
        }

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            if response.status_code == 500:
                return f"NS API returned 500 Error. The code '{station_code}' might be invalid."
            
            response.raise_for_status()
            data = response.json()
            return data.get("payload", {}).get("departures", [])
        except Exception as e:
            return f"Error in ns_get_departures: {str(e)}"

    @mcp.tool
    def ns_get_arrivals(station: str, lang: str = "nl"):
        """
        Get real-time arrival information for a specific station.
        """
        print(f"DEBUG: Starting ns_get_arrivals for {station}")
        station_code = resolve_station_code(station)
        if not station_code:
             return f"Error: Could not find a station code for '{station}'."

        endpoint = f"{BASE_URL}/reisinformatie-api/api/v2/arrivals"
        params = { "station": station_code, "lang": lang, "maxJourneys": 15 }

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("payload", {}).get("arrivals", [])
        except Exception as e:
            return f"Error in ns_get_arrivals: {str(e)}"

    @mcp.tool
    def ns_check_disruptions(station: str = None, active: bool = True):
        """
        Check for disruptions.
        """
        print(f"DEBUG: Starting ns_check_disruptions")
        if station:
            resolved = resolve_station_code(station)
            if resolved:
                station = resolved
            else:
                return f"Error: Could not find station '{station}' to check disruptions."

        endpoint = f"{BASE_URL}/disruptions/v3"
        params = { "isActive": str(active).lower() }
        if station:
            params["station"] = station

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return f"Error in ns_check_disruptions: {str(e)}"

    @mcp.tool
    def ns_get_prices(origin: str, destination: str, date: str = None, travel_class: str = "SECOND_CLASS"):
        """
        Get ticket prices.
        """
        print(f"DEBUG: Starting ns_get_prices {origin} -> {destination}")
        
        origin_code = resolve_station_code(origin)
        if not origin_code: return f"Error: Invalid origin '{origin}'"
        
        dest_code = resolve_station_code(destination)
        if not dest_code: return f"Error: Invalid destination '{destination}'"

        endpoint = f"{BASE_URL}/reisinformatie-api/api/v3/price"
        params = {
            "fromStation": origin_code,
            "toStation": dest_code,
            "travelClass": travel_class,
            "travelType": "single",
            "adults": 1
        }
        if date: params["dateTime"] = date

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return f"Error in ns_get_prices: {str(e)}"

    @mcp.tool
    def ns_get_ov_fiets(station_code: str):
        """
        Check availability of OV-fiets (rental bikes) at a specific station.
        """
        print(f"DEBUG: Starting ns_get_ov_fiets for {station_code}")
        resolved = resolve_station_code(station_code)
        if not resolved:
             return f"Error: Could not find station code for '{station_code}'."

        endpoint = f"{BASE_URL}/places-api/v2/ovfiets"
        params = { "station_code": resolved }

        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return f"Error in ns_get_ov_fiets: {str(e)}"

    @mcp.tool
    def ns_search_stations(query: str):
        """
        Search for station details.
        """
        endpoint = f"{BASE_URL}/nsapp-stations/v3"
        params = { "q": query, "limit": 5 }
        try:
            response = requests.get(endpoint, headers=get_headers(), params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return f"Error in ns_search_stations: {str(e)}"