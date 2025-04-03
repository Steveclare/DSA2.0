import requests
from bs4 import BeautifulSoup
import json
from fake_useragent import UserAgent
import re
from urllib.parse import urljoin
import time

def probe_certification_page(url):
    ua = UserAgent()
    headers = {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    base_url = "https://www.apps2.dgs.ca.gov/dsa/tracker/"
    if not url.startswith('http'):
        url = urljoin(base_url, url)
    
    print(f"\nProbing Project Certification URL: {url}")
    
    # Create a session
    session = requests.Session()
    
    try:
        # Step 1: Get the main tracker page
        print("\nStep 1: Getting main tracker page...")
        main_response = session.get(base_url, headers=headers)
        main_response.raise_for_status()
        
        # Step 2: Get the project list page first
        print("\nStep 2: Getting project list page...")
        project_list_url = urljoin(base_url, "ProjectList.aspx?ClientId=36-67")
        list_response = session.get(project_list_url, headers=headers)
        list_response.raise_for_status()
        
        # Step 3: Get the application summary page
        print("\nStep 3: Getting application summary page...")
        app_summary_url = urljoin(base_url, f"ApplicationSummary.aspx?OriginId=04&AppId=103556")
        summary_response = session.get(app_summary_url, headers=headers)
        summary_response.raise_for_status()
        
        # Step 4: Finally get the certification page
        print("\nStep 4: Getting certification page...")
        cert_response = session.get(url, headers=headers)
        cert_response.raise_for_status()
        
        # Parse the certification page
        soup = BeautifulSoup(cert_response.text, 'lxml')
        
        # Save the HTML for inspection
        with open('certification_page.html', 'w', encoding='utf-8') as f:
            f.write(cert_response.text)
        print("\nSaved HTML to certification_page.html for inspection")
        
        # Print all table cells and their contents
        print("\nAnalyzing all table cells:")
        tables = soup.find_all('table')
        for i, table in enumerate(tables):
            print(f"\nTable {i+1}:")
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if cells:
                    print("\nRow contents:")
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        if text:
                            print(f"Cell: {text}")
        
        # Look for specific certification information
        print("\nLooking for certification information:")
        cert_fields = [
            ('Last Certification Letter Type:', 'td'),
            ('Last Certification Date:', 'td'),
            ('Certification Status:', 'td'),
            ('Project Certification', 'a'),
            ('#1-Certification & Close of File', 'td'),
            ('DSA 301P Notification', 'td')
        ]
        
        for field, tag in cert_fields:
            elements = soup.find_all(tag, string=re.compile(field, re.I))
            if elements:
                print(f"\nFound {field}:")
                for elem in elements:
                    print(f"Text: {elem.get_text(strip=True)}")
                    if tag == 'td':
                        next_cell = elem.find_next('td')
                        if next_cell:
                            print(f"Next cell: {next_cell.get_text(strip=True)}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    # Test with a sample URL
    test_url = "ProjectCloseout.aspx?OriginId=04&AppId=103556"
    probe_certification_page(test_url) 