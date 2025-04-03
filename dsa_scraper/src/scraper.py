import requests
from bs4 import BeautifulSoup
import logging
import re
import json
import traceback
from urllib.parse import urljoin
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime
from .sitemap_crawler import SitemapCrawler, RegionInfo

class DSAScraper:
    def __init__(self, base_url: str, client_id: str = None, use_proxy: bool = False):
        self.base_url = base_url
        self.client_id = client_id
        self.session = self._create_session()
        self.debug_info = []
        self.use_proxy = use_proxy
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': datetime.now(),
            'regions_processed': 0
        }
        self.logger = logging.getLogger(__name__)
        self.sitemap_crawler = SitemapCrawler(base_url)
        
    def _create_session(self) -> requests.Session:
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
        if self.client_id:
            session.headers.update({'X-Client-ID': self.client_id})
        return session
        
    def _make_request(self, url: str, method: str = 'GET', data: Dict = None) -> Optional[requests.Response]:
        """Make HTTP request with error handling and proxy support."""
        self.stats['total_requests'] += 1
        try:
            proxies = self._get_proxy() if self.use_proxy else None
            response = self.session.request(method, url, json=data, proxies=proxies, timeout=30)
            response.raise_for_status()
            self.stats['successful_requests'] += 1
            return response
        except Exception as e:
            self.stats['failed_requests'] += 1
            self.logger.error(f"Error making request to {url}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return None

    def _get_proxy(self) -> Dict[str, str]:
        """Get proxy configuration - implement your proxy logic here."""
        # Example proxy configuration
        return {
            'http': 'http://proxy.example.com:8080',
            'https': 'https://proxy.example.com:8080'
        }

    def get_project_list(self, callback: Optional[Callable] = None) -> List[Dict]:
        """
        Fetch and parse the project list from DSA website.
        Now includes neighboring regions to San Diego.
        """
        projects = []
        try:
            # Get neighboring regions first
            neighboring_regions = self.sitemap_crawler._get_neighboring_regions()
            
            for region in neighboring_regions:
                self.logger.info(f"Processing region: {region.name}")
                region_data = self.sitemap_crawler.get_region_data(region)
                
                if region_data and region_data['listings']:
                    projects.extend(region_data['listings'])
                    
                if callback:
                    callback({
                        'status': 'processing',
                        'region': region.name,
                        'projects_found': len(region_data['listings'])
                    })
                
                self.stats['regions_processed'] += 1

        except Exception as e:
            self.logger.error(f"Error fetching project list: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
        if callback:
            callback({
                'status': 'completed',
                'total_projects': len(projects),
                'total_regions': self.stats['regions_processed']
            })
            
        return projects

    def get_project_details(self, project_url: str) -> Optional[Dict]:
        """
        Extract detailed information about a specific project.
        """
        try:
            response = self._make_request(project_url)
            if not response:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract project details
            details = {
                'url': project_url,
                'title': self._extract_text(soup, 'h1'),
                'price': self._extract_price(soup),
                'description': self._extract_text(soup, 'div', {'class': 'description'}),
                'location': self._extract_text(soup, 'div', {'class': 'location'}),
                'features': self._extract_features(soup),
                'contact_info': self._extract_contact_info(soup),
                'timestamp': datetime.now().isoformat()
            }
            
            return details

        except Exception as e:
            self.logger.error(f"Error fetching project details from {project_url}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return None

    def _extract_text(self, soup: BeautifulSoup, tag: str, attrs: Dict = None) -> str:
        """Extract text from HTML element."""
        element = soup.find(tag, attrs) if attrs else soup.find(tag)
        return element.text.strip() if element else ''

    def _extract_price(self, soup: BeautifulSoup) -> str:
        """Extract price from various possible locations in the HTML."""
        price_element = (
            soup.find('div', class_=re.compile(r'price|cost|value')) or
            soup.find(text=re.compile(r'\$[\d,]+'))
        )
        if price_element:
            price_match = re.search(r'\$[\d,]+', price_element.text)
            return price_match.group(0) if price_match else ''
        return ''

    def _extract_features(self, soup: BeautifulSoup) -> List[str]:
        """Extract project features."""
        features_section = soup.find('div', class_=re.compile(r'features|amenities'))
        if features_section:
            return [item.text.strip() for item in features_section.find_all('li')]
        return []

    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract contact information."""
        contact_section = soup.find('div', class_=re.compile(r'contact|agent'))
        if not contact_section:
            return {}

        return {
            'name': self._extract_text(contact_section, 'div', {'class': 'name'}),
            'phone': self._extract_text(contact_section, 'div', {'class': 'phone'}),
            'email': self._extract_text(contact_section, 'div', {'class': 'email'})
        }

    def get_stats(self) -> Dict:
        """Get current scraping statistics."""
        stats = self.stats.copy()
        stats['elapsed_time'] = str(datetime.now() - stats['start_time'])
        return stats 