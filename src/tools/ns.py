import os
import requests
from fastmcp import FastMCP

NS_BASE_URL = "https://gateway.apiportal.ns.nl/reisinformatie-api/api/v2"

def register(mcp: FastMCP):

    def _headers():
        key = os.environ.get("NS_API_KEY")
        if not key:
            return {"error": "NS_API_KEY environment variable missing"}
        return {"Ocp-Apim-Subscription-Key": key}

    @mcp.tool(description="Get train departures for a station")
    def ns_get_departures(station: str) -> dict:
        headers = _headers()
        if "error" in headers:
            return headers
        url = f"{NS_BASE_URL}/departures"
        params = {"station": station.upper()}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    @mcp.tool(description="Get train arrivals for a station")
    def ns_get_arrivals(station: str) -> dict:
        headers = _headers()
        if "error" in headers:
            return headers
        url = f"{NS_BASE_URL}/arrivals"
        params = {"station": station.upper()}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    @mcp.tool(description="List all NS stations")
    def ns_get_stations() -> dict:
        headers = _headers()
        if "error" in headers:
            return headers
        url = f"{NS_BASE_URL}/stations"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
