"""
Authentication manager for Korea Investment API.
Uses kis_auth directly for proper token and environment management.
"""
import sys
sys.path.insert(0, '/workspaces/open-trading-api/examples_user')

import kis_auth as ka
from logger import setup_logger

logger = setup_logger(__name__)


def initialize_auth():
    """
    Initialize authentication with kis_auth (VPS = mock trading).
    Call this once at startup.
    """
    try:
        logger.info("Initializing kis_auth for VPS (mock trading)...")
        
        # Initialize kis_auth with VPS (모의투자)
        ka.auth(svr="vps")  # ← 모의투자 환경 설정!
        
        trenv = ka.getTREnv()
        logger.info(f"✓ Authenticated successfully")
        logger.info(f"  Account: {trenv.my_acct}")
        logger.info(f"  Product: {trenv.my_prod}")
        logger.info(f"  URL: {trenv.my_url}")
        logger.info(f"  Paper Trading Mode: {ka.isPaperTrading()}")
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise


def get_access_token() -> str:
    """
    Get current access token from kis_auth.
    
    Returns:
        access token string
    """
    try:
        trenv = ka.getTREnv()
        return trenv.my_token
    except Exception as e:
        logger.error(f"Failed to get access token: {e}")
        raise


def get_token_manager():
    """
    Get dummy token manager for compatibility.
    kis_auth handles token management internally.
    
    Returns:
        TokenManager instance
    """
    return TokenManager()


class TokenManager:
    """
    Dummy token manager for compatibility.
    kis_auth handles actual token management.
    """
    
    def get_hashkey(self, body: str) -> str:
        """
        Get hash key for order API calls.
        kis_auth handles this internally.
        """
        return ""
