import logging
import os
import json
from pathlib import Path

# Create logger for this module
logger = logging.getLogger(__name__)

COOKIES_FILE = Path(__file__).parent.parent.parent / "logiqs-cookies.json"

def cookies_exist():
    exists = COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0
    logger.debug(f"🍪 Checking if cookies exist: {exists}")
    logger.debug(f"📁 Cookies file path: {COOKIES_FILE}")
    if COOKIES_FILE.exists():
        logger.debug(f"📊 Cookies file size: {COOKIES_FILE.stat().st_size} bytes")
    return exists

def delete_cookies():
    logger.info("🗑️ Deleting cookies file...")
    if COOKIES_FILE.exists():
        COOKIES_FILE.unlink()
        logger.info("✅ Cookies file deleted")
    else:
        logger.info("ℹ️ Cookies file does not exist, nothing to delete")

def get_cookies():
    logger.debug("📖 Loading cookies from file...")
    if not COOKIES_FILE.exists():
        logger.warning("⚠️ Cookies file does not exist")
        return None
    
    try:
        with open(COOKIES_FILE, "r") as f:
            cookies_data = json.load(f)
        logger.debug(f"✅ Successfully loaded cookies from file")
        logger.debug(f"🍪 Cookie data keys: {list(cookies_data.keys()) if isinstance(cookies_data, dict) else 'Not a dict'}")
        if isinstance(cookies_data, dict) and 'cookies' in cookies_data:
            logger.debug(f"🍪 Number of cookies: {len(cookies_data['cookies'])}")
        return cookies_data
    except Exception as e:
        logger.error(f"❌ Error loading cookies: {str(e)}")
        return None

def save_cookies(cookies):
    logger.info("💾 Saving cookies to file...")
    logger.debug(f"🍪 Cookie data keys: {list(cookies.keys()) if isinstance(cookies, dict) else 'Not a dict'}")
    if isinstance(cookies, dict) and 'cookies' in cookies:
        logger.debug(f"🍪 Number of cookies to save: {len(cookies['cookies'])}")
    
    try:
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f)
        logger.info(f"✅ Cookies saved to: {COOKIES_FILE}")
    except Exception as e:
        logger.error(f"❌ Error saving cookies: {str(e)}")
        raise 