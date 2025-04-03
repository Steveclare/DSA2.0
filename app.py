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
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import io
import glob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log'),
    ]
)

logger = logging.getLogger(__name__)

class DSAScraper:
    def __init__(self, use_proxy: bool = False, proxy: Optional[str] = None, request_delay: float = 0.0):
        """Initialize the DSA scraper with optional proxy support."""
        self.base_url = "https://www.apps2.dgs.ca.gov/dsa/tracker/"
        self.session = self._create_session()
        self.debug_info = []
        self.use_proxy = use_proxy
        self.proxy = proxy
        self.request_delay = request_delay
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': datetime.now()
        }
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retries and rotating user agents."""
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
        
    def _make_request(self, url: str, method: str = 'get', data: Optional[Dict] = None, retries: int = 3) -> Optional[requests.Response]:
        """Make HTTP request with proxy support and error handling."""
        for attempt in range(retries):
            try:
                # Add delay between requests
                if self.request_delay > 0:
                    time.sleep(self.request_delay)

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
                self.stats['successful_requests'] += 1
                return response
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    wait_time = int(e.response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                raise
            except Exception as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{retries}): {str(e)}")
                if attempt == retries - 1:
                    self.stats['failed_requests'] += 1
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
                
        return None

    def get_project_list(self, client_id: str, progress_bar: Optional[Any] = None, status_text: Optional[Any] = None) -> List[Dict]:
        """Get list of all projects with enhanced error handling and debugging."""
        url = f"{self.base_url}ProjectList.aspx?ClientId={client_id}"
        
        try:
            response = self._make_request(url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find the specific project table by ID
            table = soup.find('table', {'id': 'ctl00_MainContent_gdvsch'})
                    
            if not table:
                error_msg = "Project table not found in response"
                logger.error(error_msg)
                self.debug_info.append(error_msg)
                return []
                
            projects = []
            detailed_projects = []
            
            # Process each row in the table
            rows = table.find_all('tr')
            total_rows = len(rows)
            
            # Skip header row
            for i, row in enumerate(rows[1:], 1):
                try:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        # Get the link from the first cell
                        link = cells[0].find('a')
                        if link and 'ApplicationSummary.aspx' in link.get('href', ''):
                            href = link.get('href', '')
                            
                            # Extract DSA AppId from the URL parameters
                            parsed_url = urlparse(href)
                            query_params = parse_qs(parsed_url.query)
                            origin_id = query_params.get('OriginId', [''])[0]
                            app_id = query_params.get('AppId', [''])[0]
                            dsa_appid = f"{origin_id} {app_id}" if origin_id and app_id else ""
                            
                            project = {
                                'Link': urljoin(self.base_url, href),
                                'DSA AppId': dsa_appid,
                                'PTN': '',  # Will be filled from detail page
                                'Project Name': cells[2].get_text(strip=True),
                                'Project Scope': '',
                                'Project Cert Type': ''
                            }
                            
                            # Get project details
                            try:
                                basic_info, detailed_info = self.get_project_details(project['Link'])
                                if basic_info:
                                    project.update(basic_info)
                                if detailed_info:
                                    detailed_project = project.copy()
                                    detailed_project.update(detailed_info)
                                    detailed_projects.append(detailed_project)
                            except Exception as e:
                                logger.error(f"Error getting details for project {project['Link']}: {str(e)}")
                            
                            projects.append(project)
                            
                            if progress_bar:
                                progress_bar.progress(i / (total_rows - 1))
                            if status_text:
                                status_text.text(f"Processing project {i} of {total_rows - 1}")
                            
                except Exception as e:
                    error_info = f"Error processing row {i}: {str(e)}\n{traceback.format_exc()}"
                    logger.error(error_info)
                    self.debug_info.append(error_info)
                    continue
                    
            return projects, detailed_projects
            
        except Exception as e:
            error_info = f"Error fetching project list: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_info)
            self.debug_info.append(error_info)
            raise

    def get_project_details(self, url: str) -> Optional[Dict]:
        """Get project details with enhanced error handling and debugging."""
        try:
            # First get the application summary page
            response = self._make_request(url)
            if not response:
                return None, None
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Initialize both basic and detailed info dictionaries
            basic_info = {}
            detailed_info = {}
            
            # Look for PTN in the detail page
            ptn = ""
            ptn_cell = soup.find('td', string=re.compile(r'PTN\s+#:', re.I))
            if ptn_cell and ptn_cell.find_next('td'):
                ptn = ptn_cell.find_next('td').get_text(strip=True)
                basic_info['PTN'] = ptn
                detailed_info['PTN'] = ptn
            
            # Look for project name in a table cell
            project_name = ""
            name_cell = soup.find('td', string=re.compile(r'Project\s+Name:', re.I))
            if name_cell and name_cell.find_next('td'):
                project_name = name_cell.find_next('td').get_text(strip=True)
                basic_info['Project Name'] = project_name
                detailed_info['Project Name'] = project_name
            
            # Look for project scope in a table cell
            scope = ""
            scope_cell = soup.find('td', string=re.compile(r'Project\s+Scope:', re.I))
            if scope_cell and scope_cell.find_next('td'):
                scope = scope_cell.find_next('td').get_text(strip=True)
            
            basic_info['Project Scope'] = scope
            detailed_info['Project Scope'] = scope
            
            # Get certification info from the Project Certification page
            cert_type = ""
            try:
                # Extract AppId and OriginId from the current URL
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                origin_id = query_params.get('OriginId', [''])[0]
                app_id = query_params.get('AppId', [''])[0]
                
                if origin_id and app_id:
                    # Construct the Project Certification URL
                    cert_url = f"{self.base_url}ProjectCloseout.aspx?OriginId={origin_id}&AppId={app_id}"
                    cert_response = self._make_request(cert_url)
                    
                    if cert_response:
                        cert_soup = BeautifulSoup(cert_response.text, 'lxml')
                        
                        # Look for Last Certification Letter Type in any table cell
                        cert_type_cell = cert_soup.find('td', string=re.compile(r'Last Certification Letter Type:', re.I))
                        if cert_type_cell:
                            next_cell = cert_type_cell.find_next('td')
                            if next_cell:
                                cert_type = next_cell.get_text(strip=True)
                        
                        # If not found, look for specific certification patterns
                        if not cert_type:
                            cert_patterns = [
                                r'#\d+-Certification & Close of File(?:\s+Per EDU Code \d+\(\w+\)\s+OR\s+\d+\(\w+\))?',
                                r'DSA 301P Notification of Requirement for Certification',
                                r'#\d+-Close of File w/o Certification - Exceptions',
                                r'1 YR VOID'
                            ]
                            
                            for pattern in cert_patterns:
                                matches = cert_soup.find_all(string=re.compile(pattern, re.I))
                                if matches:
                                    cert_type = matches[0].strip()
                                    break
            except Exception as e:
                logger.error(f"Error getting certification details: {str(e)}")

            basic_info['Project Cert Type'] = cert_type
            detailed_info['Project Cert Type'] = cert_type
            
            # Collect detailed information
            field_mappings = {
                'Office ID:': 'Office ID',
                'Application #:': 'Application #',
                'File #:': 'File #',
                'PTN #:': 'PTN #',
                'OPSC #:': 'OPSC #',
                'Project Type:': 'Project Type',
                'Project Class:': 'Project Class',
                'Special Type:': 'Special Type',
                '# Of Incr:': 'Number of Increments',
                'Address:': 'Address',
                'City:': 'City',
                'Zip:': 'Zip',
                'Estimated Amt:': 'Estimated Amount',
                'Contracted Amt:': 'Contracted Amount',
                'Construction Change Document Amt:': 'Change Document Amount',
                'Final Project Cost:': 'Final Project Cost',
                'Adj Est.Date#1:': 'Adjustment Date 1',
                'Adj Est.Amt#1:': 'Adjustment Amount 1',
                'Adj Est.Date#2:': 'Adjustment Date 2',
                'Adj Est.Amt#2:': 'Adjustment Amount 2',
                'Received Date:': 'Received Date',
                'Approved Date:': 'Approved Date',
                'Approval Ext. Date:': 'Approval Extension Date',
                'Closed Date:': 'Closed Date',
                'Complete Submittal Received Date:': 'Complete Submittal Date'
            }
            
            # Extract all field values
            for field, key in field_mappings.items():
                field_cell = soup.find('td', string=re.compile(rf'^{field}$', re.I))
                if field_cell and field_cell.find_next('td'):
                    value = field_cell.find_next('td').get_text(strip=True)
                    if value:
                        detailed_info[key] = value
            
            # Get checkbox/indicator fields
            indicators = {
                'SB 575': 'SB 575',
                'New Campus': 'New Campus',
                'Modernization': 'Modernization',
                'Auto Fire Detection': 'Auto Fire Detection',
                'Sprinkler System': 'Sprinkler System',
                'Access Compliance': 'Access Compliance',
                'Fire & Life Safety': 'Fire & Life Safety',
                'Structural Safety': 'Structural Safety',
                'Field Review': 'Field Review',
                'CGS Review': 'CGS Review',
                'HPS': 'HPS'
            }
            
            for indicator, key in indicators.items():
                indicator_cell = soup.find('td', string=re.compile(rf'^{indicator}$', re.I))
                if indicator_cell:
                    # Check if there's an input checkbox and if it's checked
                    checkbox = indicator_cell.find_previous('input', {'type': 'checkbox'})
                    if checkbox and checkbox.get('checked'):
                        detailed_info[key] = 'Yes'
                    else:
                        detailed_info[key] = 'No'
            
            return basic_info, detailed_info
            
        except Exception as e:
            logger.error(f"Error getting project details from {url}: {str(e)}")
            return None, None

    def get_stats(self) -> Dict:
        """Get current scraping statistics."""
        stats = self.stats.copy()
        stats['elapsed_time'] = str(datetime.now() - stats['start_time'])
        return stats

def load_district_data() -> pd.DataFrame:
    """Load the most recent district data CSV file."""
    try:
        # Find the most recent district data file
        district_files = glob.glob('california_districts_*.csv')
        if not district_files:
            return None
        
        latest_file = max(district_files, key=lambda x: Path(x).stat().st_mtime)
        return pd.read_csv(latest_file)
    except Exception as e:
        logger.error(f"Error loading district data: {str(e)}")
        return None

def main():
    # Page config
    st.set_page_config(
        page_title="DSA Project Scraper - MMPV Design",
        page_icon="🏗️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .stApp > header {
            background-color: transparent;
        }
        .main > div {
            padding-top: 1rem;
        }
        .title {
            color: rgb(184, 199, 229);
            font-size: 2.5em;
            font-weight: 300;
            margin-top: 0;
            margin-bottom: 1rem;
        }
        .sidebar-logo {
            font-size: 2.25em;
            font-weight: 500;
            margin-bottom: 2rem;
            text-align: left;
            font-family: Arial;
        }
        .logo-white {
            color: #FFFFFF;
        }
        .logo-purple {
            color: #E6E0FF;
        }
        </style>
    """, unsafe_allow_html=True)

    # Title
    st.markdown('<h1 class="title">DSA Project Scraper</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    This application scrapes project data from the DSA website and exports it to a CSV file.
    The output includes project details such as:
    - Link
    - DSA AppId
    - Project Name
    - Project Scope
    - Project Cert Type
    - Project Type
    - Final Project Cost
    - Approved Date
    - Address
    - City
    """)
    
    # Load district data
    district_df = load_district_data()
    
    # Initialize session state for selected districts
    if 'selected_districts' not in st.session_state:
        st.session_state.selected_districts = set()
    
    # Sidebar configuration
    with st.sidebar:
        # Add MMPVDESIGN text at the top of sidebar with colored spans
        st.markdown('<div class="sidebar-logo"><span class="logo-white">MM</span><span class="logo-purple">PV</span><span class="logo-white">DESIGN</span></div>', unsafe_allow_html=True)
        st.header("Configuration")
        
        # District filtering
        if district_df is not None:
            st.subheader("District Selection")
            
            # Create county options with numbers
            county_options = ["All"]
            for county_code in sorted(district_df['CountyCode'].unique()):
                county_name = district_df[district_df['CountyCode'] == county_code]['CountyName'].iloc[0]
                county_options.append(f"{county_name} - {county_code}")
            
            # County selection
            selected_county_full = st.selectbox(
                "Select County",
                options=county_options
            )
            
            # Extract county name and code
            if selected_county_full != "All":
                selected_county = selected_county_full.split(" - ")[0]
                selected_code = selected_county_full.split(" - ")[1]
                
                # Get districts for selected county
                county_districts = district_df[district_df['CountyName'] == selected_county]
                district_options = sorted(county_districts['DistrictName'].unique().tolist())
                
                # Select All checkbox
                select_all = st.checkbox("Select All Districts in County")
                
                # Individual district checkboxes
                for district in district_options:
                    district_code = county_districts[
                        county_districts['DistrictName'] == district
                    ]['DistrictCode'].iloc[0]
                    
                    # Format district display with code
                    district_display = f"{district} ({district_code})"
                    
                    # Update checkbox state based on Select All
                    if select_all:
                        st.session_state.selected_districts.add((district, district_code))
                        st.checkbox(
                            district_display,
                            value=True,
                            key=f"district_{district_code}",
                            help=f"County: {selected_county} ({selected_code})"
                        )
                    else:
                        is_selected = st.checkbox(
                            district_display,
                            value=(district, district_code) in st.session_state.selected_districts,
                            key=f"district_{district_code}",
                            help=f"County: {selected_county} ({selected_code})"
                        )
                        if is_selected:
                            st.session_state.selected_districts.add((district, district_code))
                        else:
                            st.session_state.selected_districts.discard((district, district_code))
            
            # Display selected districts
            if st.session_state.selected_districts:
                st.subheader("Selected Districts")
                for district, code in sorted(st.session_state.selected_districts):
                    # Get county info for the district
                    district_info = district_df[district_df['DistrictCode'] == code].iloc[0]
                    county_name = district_info['CountyName']
                    county_code = district_info['CountyCode']
                    st.info(f"{district} ({code})\nCounty: {county_name} - {county_code}")
                
                if st.button("Clear All Selections"):
                    st.session_state.selected_districts.clear()
                    st.rerun()
        
        # Request delay
        st.subheader("Advanced Settings")
        request_delay = st.number_input(
            "Request Delay (seconds)",
            min_value=0.0,
            max_value=5.0,
            value=0.0,
            step=0.1,
            help="Delay between requests to avoid rate limiting"
        )
        
        # Proxy settings
        use_proxy = st.checkbox("Use Proxy")
        proxy = None
        if use_proxy:
            proxy = st.text_input("Proxy URL", help="Format: http://username:password@host:port")
    
    # Main content area
    if not st.session_state.selected_districts:
        st.warning("Please select at least one district to begin scraping")
        return
    
    # Start button in main area
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        start_scraping = st.button("Start Scraping", type="primary", use_container_width=True)
    
    if start_scraping:
        # Get client IDs from selected districts
        client_ids = [code for _, code in st.session_state.selected_districts]
        
        # Initialize scraper
        scraper = DSAScraper(
            use_proxy=use_proxy,
            proxy=proxy,
            request_delay=request_delay
        )
        
        # Create progress containers
        progress_container = st.container()
        with progress_container:
            st.subheader("Scraping Progress")
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        try:
            # Scrape projects
            all_projects = []
            all_detailed_projects = []
            
            for i, client_id in enumerate(client_ids, 1):
                status_text.text(f"Processing district {i} of {len(client_ids)}: {client_id}")
                
                try:
                    projects, detailed_projects = scraper.get_project_list(
                        client_id,
                        progress_bar,
                        status_text
                    )
                    all_projects.extend(projects)
                    all_detailed_projects.extend(detailed_projects)
                    
                    # Update progress
                    progress_bar.progress(i / len(client_ids))
                    
                except Exception as e:
                    st.error(f"Error processing district {client_id}: {str(e)}")
                    continue
            
            if not all_projects:
                st.error("No projects found")
                return
            
            # Create DataFrames
            basic_df = pd.DataFrame(all_projects)
            detailed_df = pd.DataFrame(all_detailed_projects)
            
            # Merge basic and detailed information
            final_df = pd.merge(
                basic_df,
                detailed_df,
                on=['Link', 'DSA AppId', 'Project Name', 'Project Scope', 'Project Cert Type'],
                how='outer'
            )
            
            # Select only the required columns
            final_df = final_df[[
                'Link', 'DSA AppId', 'Project Name', 'Project Scope',
                'Project Cert Type', 'Project Type', 'Final Project Cost',
                'Approved Date', 'Address', 'City'
            ]]
            
            # Generate filename with timestamp and district codes
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            district_codes = '_'.join(client_ids).replace('-', '')
            filename = f"dsa_projects_{district_codes}_{timestamp}.csv"
            
            # Save to CSV
            final_df.to_csv(filename, index=False)
            
            # Results container
            results_container = st.container()
            with results_container:
                st.subheader("Results")
                
                # Success message and download button
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.success(f"Successfully scraped {len(all_projects)} projects")
                with col2:
                    with open(filename, 'rb') as f:
                        st.download_button(
                            label="Download CSV File",
                            data=f,
                            file_name=filename,
                            mime="text/csv",
                            use_container_width=True
                        )
                
                # Display data preview
                st.subheader("Data Preview")
                st.dataframe(final_df, use_container_width=True)
                
                # Display statistics
                st.subheader("Statistics")
                stats = scraper.get_stats()
                stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                with stat_col1:
                    st.metric("Total Requests", stats['total_requests'])
                with stat_col2:
                    st.metric("Successful Requests", stats['successful_requests'])
                with stat_col3:
                    st.metric("Failed Requests", stats['failed_requests'])
                with stat_col4:
                    st.metric("Time Elapsed", stats['elapsed_time'])
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logger.error(f"Error in main: {str(e)}\n{traceback.format_exc()}")
            
        finally:
            progress_bar.empty()
            status_text.empty()

if __name__ == "__main__":
    main() 