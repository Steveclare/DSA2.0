import logging
import os
from datetime import datetime

def setup_logger(log_dir: str = "../logs") -> None:
    """Configure logging with detailed format and both file and console handlers"""
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"dsa_scraper_{timestamp}.log")
    
    # Configure logging format
    log_format = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    
    # Set up root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            logging.StreamHandler(),  # Console handler
            logging.FileHandler(log_file)  # File handler
        ]
    )
    
    # Log initial message
    logging.info(f"Logging initialized. Log file: {log_file}")

def log_request_details(response, context: str = "") -> str:
    """Log detailed information about HTTP requests/responses"""
    debug_info = f"\n=== {context} ===\n"
    debug_info += f"URL: {response.url}\n"
    debug_info += f"Status Code: {response.status_code}\n"
    debug_info += f"Headers: {response.headers}\n"
    debug_info += f"Cookies: {response.cookies}\n"
    debug_info += f"Content Length: {len(response.content)}\n"
    debug_info += "First 500 chars of content:\n"
    debug_info += response.text[:500]
    logging.debug(debug_info)
    return debug_info

def log_parsing_results(soup, context: str = "") -> str:
    """Log detailed information about HTML parsing results"""
    debug_info = f"\n=== {context} ===\n"
    
    # Check for tables
    tables = soup.find_all('table')
    debug_info += f"Found {len(tables)} tables\n"
    for table in tables:
        debug_info += f"Table ID: {table.get('id', 'None')}, Class: {table.get('class', 'None')}\n"
    
    # Check page structure
    debug_info += "\nPage Structure:\n"
    for tag in ['form', 'div', 'table', 'script']:
        elements = soup.find_all(tag)
        debug_info += f"Number of {tag} elements: {len(elements)}\n"
    
    logging.debug(debug_info)
    return debug_info 