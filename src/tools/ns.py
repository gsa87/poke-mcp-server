import requests
from fastmcp import FastMCP

NS_BASE_URL = "https://gateway.apiportal.ns.nl/reisinformatie-api/api/v2"

def register(mcp: FastMCP):

    @mcp.tool(description="Get train departures for a station (e.g., UT, ASDM, RTA, AMS)")
    def ns_get_departures(station: str, key: str) -> dict:
        url = f"{NS_BASE_URL}/departures"
        headers = {"Ocp-Apim-Subscription-Key": key}
        params = {"station": station.upper()}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    @mcp.tool(description="Get train arrivals for a station")
    def ns_get_arrivals(station: str, key: str) -> dict:
        url = f"{NS_BASE_URL}/arrivals"
        headers = {"Ocp-Apim-Subscription-Key": key}
        params = {"station": station.upper()}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    @mcp.tool(description="List all NS stations")
    def ns_get_stations(key: str) -> dict:
        url = f"{NS_BASE_URL}/stations"
        headers = {"Ocp-Apim-Subscription-Key": key}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
