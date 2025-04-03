import requests
from bs4 import BeautifulSoup
import json
from fake_useragent import UserAgent
import re

def probe_app_summary(url):
    ua = UserAgent()
    headers = {'User-Agent': ua.random}
    
    print(f"\nProbing Application Summary URL: {url}")
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'lxml')
    
    # Find all tables and their IDs
    print("\nAll table IDs found:")
    tables = soup.find_all('table')
    for table in tables:
        table_id = table.get('id', 'No ID')
        print(f"Table ID: {table_id}")
        
        # Print first row of each table to understand structure
        rows = table.find_all('tr')
        if rows:
            print("First row cells:")
            cells = rows[0].find_all(['th', 'td'])
            for cell in cells:
                print(f"  - {cell.get_text(strip=True)}")
    
    # Look for links to other pages
    print("\nLinks to other pages:")
    links = soup.find_all('a')
    for link in links:
        href = link.get('href', '')
        if 'ProjectCloseout.aspx' in href or 'Certification' in href:
            print(f"Found certification link: {href}")
            print(f"Link text: {link.get_text(strip=True)}")
    
    # Look for hidden fields that might contain certification info
    print("\nHidden fields:")
    hidden_fields = soup.find_all('input', {'type': 'hidden'})
    for field in hidden_fields:
        print(f"Field ID: {field.get('id', 'No ID')}, Name: {field.get('name', 'No Name')}")
    
    # Look for any certification-related text
    print("\nCertification-related text:")
    cert_patterns = [
        r'#\d+-Certification & Close of File',
        r'DSA 301P Notification',
        r'Close of File',
        r'Certification Status',
        r'Project Certification'
    ]
    
    for pattern in cert_patterns:
        matches = soup.find_all(string=re.compile(pattern, re.I))
        if matches:
            print(f"\nMatches for pattern '{pattern}':")
            for match in matches:
                # Get parent element
                parent = match.parent
                print(f"Text: {match.strip()}")
                print(f"Parent tag: {parent.name}")
                print(f"Parent ID: {parent.get('id', 'No ID')}")
                # Try to get next cell if in table
                if parent.name == 'td':
                    next_cell = parent.find_next('td')
                    if next_cell:
                        print(f"Next cell content: {next_cell.get_text(strip=True)}")

if __name__ == "__main__":
    # Test with a sample URL
    test_url = "https://www.apps2.dgs.ca.gov/dsa/tracker/ApplicationSummary.aspx?OriginId=04&AppId=103556"
    probe_app_summary(test_url) 