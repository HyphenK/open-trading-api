"""
HTTP API client for Korea Investment REST API.
Uses kis_auth library for proper parameter handling and TR_ID conversion.
"""
import sys
sys.path.insert(0, '/workspaces/open-trading-api/examples_user')

import urllib3
import kis_auth as ka
from logger import setup_logger

# Suppress InsecureRequestWarning for mock trading API
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = setup_logger(__name__)

_api_client_instance = None


def get_api_client():
    """Singleton accessor for API client."""
    global _api_client_instance
    if _api_client_instance is None:
        _api_client_instance = KIApiClient()
    return _api_client_instance


class KIApiClient:
    """REST API client using kis_auth infrastructure."""
    
    def get(self, path: str, params: dict = None, tr_id: str = ""):
        """
        Make GET request using kis_auth._url_fetch.
        
        Args:
            path: API endpoint path
            params: query parameters dict
            tr_id: transaction ID
            
        Returns:
            kis_auth APIResp object
        """
        if params is None:
            params = {}
        
        try:
            logger.debug(f"GET {path} (TR_ID={tr_id})")
            
            # Use kis_auth._url_fetch for proper header handling and TR_ID conversion
            response = ka._url_fetch(path, tr_id, "", params, postFlag=False)
            
            return response
            
        except Exception as e:
            logger.error(f"Request error on GET {path}: {e}")
            raise
    
    def post(self, path: str, data: dict, tr_id: str = ""):
        """
        Make POST request using kis_auth._url_fetch.
        
        Args:
            path: API endpoint path
            data: request body dict
            tr_id: transaction ID
            
        Returns:
            kis_auth APIResp object
        """
        try:
            logger.debug(f"POST {path} (TR_ID={tr_id})")
            
            # Use kis_auth._url_fetch for proper header handling and TR_ID conversion
            response = ka._url_fetch(path, tr_id, "", data, postFlag=True, hashFlag=True)
            
            return response
            
        except Exception as e:
            logger.error(f"Request error on POST {path}: {e}")
            raise
    
    def check_response_error(self, response) -> bool:
        """
        Check if response contains error.
        
        Returns:
            True if error, False otherwise
        """
        if hasattr(response, 'isOK'):
            return not response.isOK()
        return True
