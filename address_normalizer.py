import re
from typing import Dict, Optional, List, Tuple
import logging

class AddressNormalizer:
    """
    A utility class for normalizing and standardizing address strings.
    This helps with consistent address formatting across the application.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common address abbreviations and their full forms
        self.street_abbr = {
            'ave': 'avenue',
            'blvd': 'boulevard',
            'cir': 'circle',
            'ct': 'court',
            'dr': 'drive',
            'expy': 'expressway',
            'hwy': 'highway',
            'ln': 'lane',
            'pkwy': 'parkway',
            'pl': 'place',
            'rd': 'road',
            'sq': 'square',
            'st': 'street',
            'trl': 'trail'
        }
        
        # Common direction abbreviations
        self.direction_abbr = {
            'n': 'north',
            's': 'south',
            'e': 'east',
            'w': 'west',
            'ne': 'northeast',
            'nw': 'northwest',
            'se': 'southeast',
            'sw': 'southwest'
        }
    
    def normalize(self, address: str) -> str:
        """
        Normalize an address string by standardizing format.
        
        Args:
            address: The address string to normalize
            
        Returns:
            A normalized version of the address
        """
        if not address:
            return ""
            
        try:
            # Convert to lowercase for consistent processing
            address = address.lower().strip()
            
            # Remove extra whitespace
            address = re.sub(r'\s+', ' ', address)
            
            # Replace common abbreviations
            words = address.split()
            normalized_words = []
            
            for word in words:
                # Remove trailing periods from abbreviations
                word = word.rstrip('.')
                
                # Expand street type abbreviations
                if word in self.street_abbr:
                    word = self.street_abbr[word]
                
                # Expand direction abbreviations
                if word in self.direction_abbr:
                    word = self.direction_abbr[word]
                
                normalized_words.append(word)
            
            # Recombine into a single string
            normalized = ' '.join(normalized_words)
            
            # Format the address with proper capitalization
            return self._capitalize_address(normalized)
            
        except Exception as e:
            self.logger.error(f"Error normalizing address: {e}")
            return address
    
    def _capitalize_address(self, address: str) -> str:
        """
        Apply proper capitalization to an address.
        
        Args:
            address: The lowercase address string
            
        Returns:
            The address with proper capitalization
        """
        words = address.split()
        capitalized = []
        
        for word in words:
            # Don't capitalize certain words unless they're at the beginning
            if word in ['and', 'of', 'the', 'in', 'on', 'at'] and capitalized:
                capitalized.append(word)
            else:
                capitalized.append(word.capitalize())
        
        return ' '.join(capitalized)
    
    def parse_address(self, address: str) -> Dict[str, str]:
        """
        Parse an address into its components.
        
        Args:
            address: The address string to parse
            
        Returns:
            Dictionary with address components
        """
        if not address:
            return {}
            
        try:
            # Simple regex-based parsing for US addresses
            # This is a basic implementation and may need enhancement for complex addresses
            
            # Find the ZIP code
            zip_match = re.search(r'(\d{5})(?:-\d{4})?', address)
            zip_code = zip_match.group(0) if zip_match else ''
            
            # Split into parts
            parts = re.split(r',\s*', address)
            
            result = {
                'street': parts[0] if len(parts) > 0 else '',
                'city': parts[1] if len(parts) > 1 else '',
                'state': parts[2].split()[0] if len(parts) > 2 and ' ' in parts[2] else '',
                'zip': zip_code
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing address: {e}")
            return {'full_address': address} 