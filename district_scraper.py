from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
from typing import List, Dict
import time
import random

def setup_driver():
    """Set up Chrome driver with appropriate options."""
    chrome_options = Options()
    
    # Set up as a regular browser
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--start-maximized')
    
    # Add user agent
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def random_sleep(min_seconds=1, max_seconds=3):
    """Sleep for a random amount of time."""
    time.sleep(random.uniform(min_seconds, max_seconds))

def wait_for_element(driver, by, value, timeout=20, condition='presence'):
    """Wait for an element with better error handling."""
    try:
        wait = WebDriverWait(driver, timeout)
        if condition == 'presence':
            return wait.until(EC.presence_of_element_located((by, value)))
        elif condition == 'clickable':
            return wait.until(EC.element_to_be_clickable((by, value)))
        elif condition == 'visible':
            return wait.until(EC.visibility_of_element_located((by, value)))
    except TimeoutException:
        print(f"Timeout waiting for element: {value}")
        print("Current URL:", driver.current_url)
        print("Page source:", driver.page_source[:1000])
        raise
    except Exception as e:
        print(f"Error waiting for element {value}: {str(e)}")
        raise

def get_districts_for_county(driver, county_code: str, county_name: str) -> List[Dict]:
    """Get districts for a specific county using the direct URL."""
    url = f"https://www.apps2.dgs.ca.gov/dsa/tracker/CountySchoolProjects.aspx?County={county_code}"
    districts = []
    
    try:
        print(f"\nScraping districts for {county_name} (County {county_code})...")
        driver.get(url)
        random_sleep(3, 5)
        
        print("Waiting for districts table...")
        table = wait_for_element(
            driver, By.TAG_NAME, "table",
            condition='visible'
        )
        
        print("Processing table rows...")
        # Get all rows from the table (skip header row)
        rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
        
        for row in rows:
            try:
                # Get the district code and name cells
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    district_code = cells[1].text.strip()
                    district_name = cells[2].text.strip()
                    
                    if district_code and district_name:
                        district_data = {
                            'CountyCode': county_code,
                            'CountyName': county_name,
                            'DistrictCode': district_code,
                            'DistrictName': district_name
                        }
                        print(f"Found district: {district_data}")
                        districts.append(district_data)
            except Exception as e:
                print(f"Error processing row: {str(e)}")
                continue
        
        print(f"Found {len(districts)} districts in {county_name}")
        return districts
    
    except Exception as e:
        print(f"Error getting districts for {county_name} (County {county_code}): {str(e)}")
        print("Current URL:", driver.current_url)
        print("Page source:", driver.page_source[:1000])
        return []

def scrape_all_districts():
    """Scrape all districts from all California counties."""
    all_districts = []
    driver = None
    
    # California counties with their codes
    california_counties = {
        '1': 'Alameda',
        '2': 'Alpine',
        '3': 'Amador',
        '4': 'Butte',
        '5': 'Calaveras',
        '6': 'Colusa',
        '7': 'Contra Costa',
        '8': 'Del Norte',
        '9': 'El Dorado',
        '10': 'Fresno',
        '11': 'Glenn',
        '12': 'Humboldt',
        '13': 'Imperial',
        '14': 'Inyo',
        '15': 'Kern',
        '16': 'Kings',
        '17': 'Lake',
        '18': 'Lassen',
        '19': 'Los Angeles',
        '20': 'Madera',
        '21': 'Marin',
        '22': 'Mariposa',
        '23': 'Mendocino',
        '24': 'Merced',
        '25': 'Modoc',
        '26': 'Mono',
        '27': 'Monterey',
        '28': 'Napa',
        '29': 'Nevada',
        '30': 'Orange',
        '31': 'Placer',
        '32': 'Plumas',
        '33': 'Riverside',
        '34': 'Sacramento',
        '35': 'San Benito',
        '36': 'San Bernardino',
        '37': 'San Diego',
        '38': 'San Francisco',
        '39': 'San Joaquin',
        '40': 'San Luis Obispo',
        '41': 'San Mateo',
        '42': 'Santa Barbara',
        '43': 'Santa Clara',
        '44': 'Santa Cruz',
        '45': 'Shasta',
        '46': 'Sierra',
        '47': 'Siskiyou',
        '48': 'Solano',
        '49': 'Sonoma',
        '50': 'Stanislaus',
        '51': 'Sutter',
        '52': 'Tehama',
        '53': 'Trinity',
        '54': 'Tulare',
        '55': 'Tuolumne',
        '56': 'Ventura',
        '57': 'Yolo',
        '58': 'Yuba'
    }
    
    try:
        print("Setting up Chrome driver...")
        driver = setup_driver()
        
        for county_code, county_name in california_counties.items():
            districts = get_districts_for_county(driver, county_code, county_name)
            if districts:
                all_districts.extend(districts)
            random_sleep(2, 4)  # Add delay between counties
        
        if all_districts:
            df = pd.DataFrame(all_districts)
            df = df.sort_values(['CountyCode', 'DistrictCode'])
            
            # Save to CSV with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f'california_districts_{timestamp}.csv'
            df.to_csv(filename, index=False)
            
            print(f"\nSuccessfully scraped {len(all_districts)} districts total")
            print(f"Data saved to {filename}")
            
            # Print summary by county
            print("\nSummary by county:")
            county_summary = df.groupby(['CountyCode', 'CountyName']).size()
            for (code, name), count in county_summary.items():
                print(f"County {code} ({name}): {count} districts")
            
            return df
        else:
            print("\nNo districts found")
            return None
            
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    scrape_all_districts() 