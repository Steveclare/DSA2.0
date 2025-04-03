import requests
from bs4 import BeautifulSoup
import json
from fake_useragent import UserAgent
from urllib.parse import urljoin
import re

def probe_dsa_page(url):
    ua = UserAgent()
    headers = {'User-Agent': ua.random}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'lxml')
    
    print("\nChecking for cost/budget information:")
    cost_patterns = [
        'Estimated Amt',
        'Contracted Amt',
        'Final Project Cost',
        'Budget',
        'Cost',
        'Amount'
    ]
    
    for pattern in cost_patterns:
        cells = soup.find_all('td', string=re.compile(pattern, re.I))
        for cell in cells:
            print(f"\nFound cost-related cell: {cell.get_text(strip=True)}")
            next_cell = cell.find_next('td')
            if next_cell:
                print(f"Content: {next_cell.get_text(strip=True)}")
    
    print("\nAll table headers and their next cells:")
    all_cells = soup.find_all('td')
    for cell in all_cells:
        text = cell.get_text(strip=True)
        next_cell = cell.find_next('td')
        if next_cell and any(cost_word in text.lower() for cost_word in ['amount', 'cost', 'budget', 'estimate']):
            print(f"Header: {text} -> Content: {next_cell.get_text(strip=True)}")
    
    # Look specifically for certification information
    print("\nSearching for certification information:")
    cert_related = soup.find_all('td', string=lambda x: x and 'certif' in x.lower())
    for cell in cert_related:
        print(f"\nFound certification-related cell: {cell.get_text(strip=True)}")
        next_cell = cell.find_next('td')
        if next_cell:
            print(f"Content: {next_cell.get_text(strip=True)}")
    
    # Look for any status information
    print("\nSearching for status information:")
    status_related = soup.find_all('td', string=lambda x: x and 'status' in x.lower())
    for cell in status_related:
        print(f"\nFound status-related cell: {cell.get_text(strip=True)}")
        next_cell = cell.find_next('td')
        if next_cell:
            print(f"Content: {next_cell.get_text(strip=True)}")

if __name__ == "__main__":
    # Test with a sample URL from the CSV
    test_url = "https://www.apps2.dgs.ca.gov/dsa/tracker/ApplicationSummary.aspx?OriginId=04&AppId=103556"
    print(f"Probing URL: {test_url}")
    probe_dsa_page(test_url) 