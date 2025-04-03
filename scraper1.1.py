import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import logging
import re
import json
import traceback
from urllib.parse import urljoin, urlparse, parse_qs
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dsa_scraper.log')
    ]
)

def validate_url(url):
    """Validate URL structure and parameters"""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL structure"
            
        if "ClientId=ClientId=" in url:
            return False, "Duplicate ClientId parameter"
            
        if "ClientId" not in params:
            return False, "Missing ClientId parameter"
            
        return True, None
    except Exception as e:
        return False, f"URL validation error: {str(e)}"

def log_request_details(response, context=""):
    """Log detailed information about HTTP requests/responses"""
    debug_info = f"\n=== {context} ===\n"
    debug_info += f"URL: {response.url}\n"
    debug_info += f"Status Code: {response.status_code}\n"
    debug_info += f"Headers: {json.dumps(dict(response.headers), indent=2)}\n"
    debug_info += f"Cookies: {json.dumps(dict(response.cookies), indent=2)}\n"
    debug_info += f"Content Length: {len(response.content)}\n"
    debug_info += "First 500 chars of content:\n"
    debug_info += response.text[:500]
    logging.debug(debug_info)
    return debug_info

def log_parsing_results(soup, context=""):
    """Log detailed information about HTML parsing results"""
    debug_info = f"\n=== {context} ===\n"
    
    # Check for common table IDs
    table_ids = ['ProjectList', 'projectList', 'project-list', 'projects']
    for table_id in table_ids:
        table = soup.find('table', {'id': table_id})
        if table:
            debug_info += f"Found table with ID: {table_id}\n"
            break
    else:
        debug_info += "No table found with expected IDs\n"
        debug_info += "Available tables:\n"
        for table in soup.find_all('table'):
            debug_info += f"Table ID: {table.get('id', 'None')}, Class: {table.get('class', 'None')}\n"
    
    # Check page structure
    debug_info += "\nPage Structure:\n"
    for tag in ['form', 'div', 'table', 'script']:
        elements = soup.find_all(tag)
        debug_info += f"Number of {tag} elements: {len(elements)}\n"
    
    logging.debug(debug_info)
    return debug_info

class DSAScraper:
    def __init__(self, use_proxy=False, proxy=None):
        self.base_url = "https://www.apps2.dgs.ca.gov/dsa/tracker/"
        self.client_id = "36-67"  # Hardcoded client ID
        self.session = self._create_session()
        self.debug_info = []
        self.use_proxy = use_proxy
        self.proxy = proxy
        
    def _create_session(self):
        """Create a requests session with retries and rotating user agents"""
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set up rotating user agent
        ua = UserAgent()
        session.headers.update({
            'User-Agent': ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        return session
        
    def _make_request(self, url, method='get', data=None, retries=3):
        """Make HTTP request with proxy support and error handling"""
        for attempt in range(retries):
            try:
                kwargs = {}
                if self.use_proxy and self.proxy:
                    kwargs['proxies'] = {
                        'http': self.proxy,
                        'https': self.proxy
                    }
                
                if method.lower() == 'post':
                    response = self.session.post(url, data=data, **kwargs)
                else:
                    response = self.session.get(url, **kwargs)
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    wait_time = int(e.response.headers.get('Retry-After', 60))
                    logging.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                raise
            except Exception as e:
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
                
        raise Exception(f"Failed after {retries} attempts")

    def get_project_list(self, progress_bar=None, status_text=None, debug_mode=False):
        """Get list of all projects with enhanced error handling and debugging"""
        url = f"{self.base_url}ProjectList.aspx?ClientId={self.client_id}"
        
        try:
            response = self._make_request(url)
            
            if debug_mode:
                self.debug_info.append(log_request_details(response, "Initial Project List Request"))
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if debug_mode:
                self.debug_info.append(log_parsing_results(soup, "Project List Parsing"))
            
            # Find the specific project table by ID
            table = soup.find('table', {'id': 'ctl00_MainContent_gdvsch'})
                    
            if not table:
                error_msg = "Project table not found in response"
                logging.error(error_msg)
                self.debug_info.append(error_msg)
                if debug_mode:
                    self.debug_info.append("Raw HTML:\n" + response.text)
                return []
                
            projects = []
            # Process each row in the table
            rows = table.find_all('tr')
            total_rows = len(rows)
            
            for i, row in enumerate(rows):
                try:
                    # Find all links in the row
                    links = row.find_all('a')
                    if not links:
                        continue
                        
                    for link in links:
                        href = link.get('href', '')
                        if 'ApplicationSummary.aspx' in href:
                            # Extract the text content
                            text = row.get_text(strip=True, separator=' ')
                            
                            # Parse the text into components
                            # Expected format: "DSA AppId PTN Project Name"
                            parts = text.split(None, 3)  # Split into max 4 parts
                            
                            if len(parts) >= 3:
                                app_id = f"{parts[0]} {parts[1]}"
                                ptn = parts[2] if len(parts) > 2 else ""
                                name = parts[3] if len(parts) > 3 else ""
                                
                                project = {
                                    'Link': urljoin(self.base_url, href),
                                    'App ID': app_id.strip(),
                                    'PTN': ptn.strip(),
                                    'Project Name': name.strip(),
                                    'Project Scope': '',
                                    'Project Cert Type': ''
                                }
                                projects.append(project)
                                
                                if progress_bar:
                                    progress_bar.progress((i + 1) / total_rows)
                                if status_text:
                                    status_text.text(f"Processing project {i+1} of {total_rows}: {name}")
                            break  # Only process the first valid link in each row
                            
                except Exception as e:
                    error_info = f"Error processing row {i+1}: {str(e)}\n{traceback.format_exc()}"
                    logging.error(error_info)
                    self.debug_info.append(error_info)
                    continue
                    
            return projects
            
        except Exception as e:
            error_info = f"Error fetching project list: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_info)
            self.debug_info.append(error_info)
            raise

    def get_project_details(self, url, retries=3, debug_mode=False):
        """Get project details with enhanced error handling and debugging"""
        for attempt in range(retries):
            try:
                response = self._make_request(url)
                
                if debug_mode:
                    self.debug_info.append(log_request_details(response, f"Project Details Request (Attempt {attempt + 1})"))
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                if debug_mode:
                    self.debug_info.append(log_parsing_results(soup, f"Project Details Parsing (Attempt {attempt + 1})"))
                
                # Look for project scope in a table cell
                scope = ""
                scope_cell = soup.find('td', string=re.compile(r'Project\s+Scope', re.I))
                if scope_cell:
                    next_cell = scope_cell.find_next('td')
                    if next_cell:
                        scope = next_cell.get_text(strip=True)
                
                # Look for certification status
                cert_type = ""
                cert_cell = soup.find('td', string=re.compile(r'Certification\s+Status', re.I))
                if cert_cell:
                    next_cell = cert_cell.find_next('td')
                    if next_cell:
                        cert_type = next_cell.get_text(strip=True)
                
                return {
                    'Project Scope': scope,
                    'Project Cert Type': cert_type
                }
                
            except Exception as e:
                error_info = f"Error (Attempt {attempt + 1}): {str(e)}\n{traceback.format_exc()}"
                logging.warning(error_info)
                self.debug_info.append(error_info)
                
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                    
        return {
            'Project Scope': '',
            'Project Cert Type': ''
        }

def main():
    st.set_page_config(page_title="DSA Project Scraper", layout="wide")
    
    st.title("DSA Project Scraper")
    st.markdown("""
    #### Built by Stephen Clare | 619.977.3020
    *A tool for extracting project information from the Division of State Architect (DSA) website*
    """)
    
    # Debug mode toggle in sidebar
    debug_mode = st.sidebar.checkbox("Debug Mode", help="Enable detailed debugging output")
    
    if debug_mode:
        st.sidebar.markdown("### Debug Options")
        show_raw_html = st.sidebar.checkbox("Show Raw HTML")
        download_debug = st.sidebar.checkbox("Enable Debug Download")
    
    delay = st.slider(
        "Delay between requests (seconds)", 
        min_value=0.1, 
        max_value=2.0, 
        value=0.5,
        help="Adjust this if you're experiencing connection issues"
    )
    
    if st.button("Start Scraping"):
        try:
            scraper = DSAScraper()
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("Fetching project list..."):
                projects = scraper.get_project_list(
                    progress_bar=progress_bar,
                    status_text=status_text,
                    debug_mode=debug_mode
                )
                
            if not projects:
                st.error("No projects found or error occurred")
                if debug_mode:
                    with st.expander("Debug Information"):
                        st.code("\n".join(scraper.debug_info))
                return
                
            st.info(f"Found {len(projects)} projects. Fetching details...")
            
            for i, project in enumerate(projects):
                status_text.text(f"Processing details for project {i+1} of {len(projects)}: {project['Project Name']}")
                progress_bar.progress((i + 1) / len(projects))
                
                time.sleep(delay)
                details = scraper.get_project_details(project['Link'], debug_mode=debug_mode)
                project.update(details)
            
            df = pd.DataFrame(projects)
            timestamp = datetime.now().strftime("%m%d%y")
            filename = f"DSA_Projects_{scraper.client_id.replace('-', '')}_{timestamp}.csv"
            
            st.download_button(
                label="Download CSV",
                data=df.to_csv(index=False),
                file_name=filename,
                mime="text/csv"
            )
            
            st.subheader("Preview of Results")
            st.dataframe(df)
            
            if debug_mode:
                if show_raw_html:
                    with st.expander("Raw HTML"):
                        st.code(scraper.debug_info[-1])
                        
                if download_debug:
                    debug_filename = f"debug_log_{timestamp}.txt"
                    st.download_button(
                        label="Download Debug Log",
                        data="\n".join(scraper.debug_info),
                        file_name=debug_filename,
                        mime="text/plain"
                    )
            
            st.success("Scraping completed successfully!")
            
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            st.error("An error occurred during scraping")
            if debug_mode:
                with st.expander("Error Details"):
                    st.code(error_msg)

if __name__ == "__main__":
    main()