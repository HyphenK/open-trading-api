"""
HTTP API client for Korea Investment REST API.
Uses kis_auth logic for proper parameter handling and TR_ID conversion.
"""
import sys
sys.path.insert(0, '/workspaces/open-trading-api/examples_user')

import requests
import json
from typing import Any, Dict, Optional
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
    
    def get(self, path: str, params: Optional[Dict] = None, tr_id: str = "") -> Dict[str, Any]:
        """
        Make GET request using kis_auth._url_fetch.
        
        Args:
            path: API endpoint path
            params: query parameters
            tr_id: transaction ID (will be auto-converted if needed)
            
        Returns:
            Response data as dictionary
            
        Raises:
            Exception if API call fails
        """
        try:
            logger.debug(f"GET {path} (TR_ID={tr_id}) with params {params}")
            
            # Use kis_auth._url_fetch for proper handling
            resp = ka._url_fetch(path, tr_id, "", params, postFlag=False)
            
            # Check if response is OK
            if resp.status_code == 200 or hasattr(resp, 'isOK') and resp.isOK():
                # kis_auth returns APIResp object with isOK() method
                return resp
            else:
                error_msg = f"API error: {resp.status_code}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error on GET {path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error on GET {path}: {e}")
            raise
    
    def post(self, path: str, data: Dict[str, Any], tr_id: str = "") -> Dict[str, Any]:
        """
        Make POST request using kis_auth._url_fetch.
        
        Args:
            path: API endpoint path
            data: request body
            tr_id: transaction ID
            
        Returns:
            Response data as dictionary
            
        Raises:
            Exception if API call fails
        """
        try:
            logger.debug(f"POST {path} (TR_ID={tr_id}) with data {data}")
            
            # Use kis_auth._url_fetch for POST
            resp = ka._url_fetch(path, tr_id, "", data, postFlag=True)
            
            if resp.status_code == 200 or hasattr(resp, 'isOK') and resp.isOK():
                return resp
            else:
                error_msg = f"API error: {resp.status_code}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error on POST {path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error on POST {path}: {e}")
            raise
    
    def check_response_error(self, response) -> bool:
        """
        Check if response contains error.
        Works with both kis_auth APIResp and dict responses.
        
        Returns:
            True if error, False otherwise
        """
        # kis_auth APIResp object
        if hasattr(response, 'isOK'):
            return not response.isOK()
        
        # Dict response
        if isinstance(response, dict):
            return response.get('rt_cd') != '0'
        
        return True
            path: API endpoint path
            data: request body dictionary
            tr_id: transaction ID (required by Korea Investment API)
            
        Returns:
            JSON response as dictionary
            
        Raises:
            requests.RequestException if request fails
        """
        url = f"{self.base_url}{path}"
        body = json.dumps(data)
        headers = self._get_headers("POST", body, tr_id=tr_id)
        
        try:
            logger.debug(f"POST {path} (TR_ID={tr_id}) with data {data}")
            response = requests.post(
                url,
                data=body,
                headers=headers,
                timeout=self.timeout,
                verify=False
            )
            response.raise_for_status()
            
            data_response = response.json()
            logger.debug(f"Response status: {data_response.get('rt_cd', 'N/A')}")
            return data_response
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout on POST {path}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error on POST {path}: {e}")
            raise
    
    def check_response_error(self, response: Dict[str, Any]) -> bool:
        """
        Check if API response indicates an error.
        
        Args:
            response: API response dictionary
            
        Returns:
            True if error, False if success
        """
        rt_cd = response.get('rt_cd', '')
        msg = response.get('msg1', response.get('msg', ''))
        
        if rt_cd == '0':
            return False  # Success
        else:
            logger.warning(f"API Error: rt_cd={rt_cd}, msg={msg}")
            return True


# Global API client instance
_api_client = None


def get_api_client() -> KIApiClient:
    """Get or create global API client."""
    global _api_client
    if _api_client is None:
        _api_client = KIApiClient()
    return _api_client
