import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin
import logging
from pprint import pformat

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dsa_recon.log'),
        logging.StreamHandler()
    ]
)

class DSARecon:
    def __init__(self):
        self.base_url = "https://www.apps2.dgs.ca.gov/dsa/tracker/"
        self.session = requests.Session()
        # Add common headers to mimic browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        })

    def analyze_page_structure(self, client_id):
        """Analyze the structure of the project list page"""
        logging.info(f"Analyzing page structure for client ID: {client_id}")
        
        url = f"{self.base_url}ProjectList.aspx?ClientId={client_id}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Analyze form structure
            form = soup.find('form')
            if form:
                logging.info("Form details:")
                logging.info(f"Form ID: {form.get('id', 'Not found')}")
                logging.info(f"Form method: {form.get('method', 'Not found')}")
                
                # Find hidden inputs
                hidden_inputs = form.find_all('input', type='hidden')
                logging.info("Hidden form fields:")
                for inp in hidden_inputs:
                    logging.info(f"  {inp.get('name', 'No name')}: {inp.get('value', 'No value')}")

            # Analyze table structure
            table = soup.find('table', {'id': 'ProjectList'})
            if table:
                headers = [th.text.strip() for th in table.find_all('th')]
                logging.info(f"Table headers: {headers}")
                
                # Sample first row structure
                first_row = table.find('tr', {'class': ['GridRow', 'GridAltRow']})
                if first_row:
                    cells = first_row.find_all('td')
                    logging.info("First row structure:")
                    for i, cell in enumerate(cells):
                        logging.info(f"  Column {i}: {cell.text.strip()}")
                        if cell.find('a'):
                            logging.info(f"  Column {i} contains link: {cell.find('a')['href']}")

            return True
        except Exception as e:
            logging.error(f"Error analyzing page structure: {str(e)}", exc_info=True)
            return False

    def analyze_project_detail_page(self, client_id):
        """Analyze the structure of a project detail page"""
        logging.info("Analyzing project detail page")
        
        # First get a project link from the list page
        url = f"{self.base_url}ProjectList.aspx?ClientId={client_id}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find first project link
            project_link = soup.find('a', href=lambda x: x and 'ApplicationSummary.aspx' in x)
            if not project_link:
                logging.error("No project links found")
                return False
                
            # Analyze project detail page
            detail_url = urljoin(self.base_url, project_link['href'])
            logging.info(f"Analyzing detail page: {detail_url}")
            
            detail_response = self.session.get(detail_url)
            detail_response.raise_for_status()
            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
            
            # Look for key elements
            key_elements = {
                'Project Scope': detail_soup.find('span', {'id': 'ProjectScope'}),
                'Project Certification': detail_soup.find('span', {'id': 'ProjectCertification'}),
                'Application Status': detail_soup.find('span', {'id': 'ApplicationStatus'})
            }
            
            logging.info("Key elements found:")
            for name, element in key_elements.items():
                if element:
                    logging.info(f"  {name}: {element.get('id')} (Found)")
                    logging.info(f"  {name} parent structure: {element.parent.name} - {element.parent.get('class', 'No class')}")
                else:
                    logging.info(f"  {name}: Not found")

            return True
        except Exception as e:
            logging.error(f"Error analyzing project detail page: {str(e)}", exc_info=True)
            return False

    def test_rate_limits(self, client_id):
        """Test for rate limiting"""
        logging.info("Testing rate limits")
        
        url = f"{self.base_url}ProjectList.aspx?ClientId={client_id}"
        
        try:
            # Make 5 quick requests
            start_time = time.time()
            responses = []
            
            for i in range(5):
                response = self.session.get(url)
                responses.append({
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'content_length': len(response.content)
                })
                time.sleep(0.1)  # Very short delay
                
            end_time = time.time()
            
            logging.info(f"Rate limit test results (5 requests in {end_time - start_time:.2f} seconds):")
            for i, resp in enumerate(responses, 1):
                logging.info(f"  Request {i}:")
                logging.info(f"    Status: {resp['status_code']}")
                logging.info(f"    Response time: {resp['response_time']:.2f}s")
                logging.info(f"    Content length: {resp['content_length']} bytes")

            return True
        except Exception as e:
            logging.error(f"Error testing rate limits: {str(e)}", exc_info=True)
            return False

def main():
    # Test client ID (Yucaipa USD from your example)
    CLIENT_ID = "36-67"
    
    logging.info("Starting DSA website reconnaissance")
    logging.info("=" * 50)
    
    recon = DSARecon()
    
    # Run all analyses
    recon.analyze_page_structure(CLIENT_ID)
    time.sleep(1)  # Delay between tests
    
    recon.analyze_project_detail_page(CLIENT_ID)
    time.sleep(1)  # Delay between tests
    
    recon.test_rate_limits(CLIENT_ID)
    
    logging.info("=" * 50)
    logging.info("Reconnaissance complete. Check dsa_recon.log for full details")

if __name__ == "__main__":
    main()