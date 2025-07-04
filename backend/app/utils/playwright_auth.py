import logging
import asyncio
from playwright.async_api import async_playwright
from app.utils.cookies import save_cookies
from pathlib import Path
import time

# Create logger for this module
logger = logging.getLogger(__name__)

LOGIQS_URL = 'https://tps.logiqs.com/Login.aspx'
COOKIES_FILE = Path(__file__).parent.parent.parent / 'logiqs-cookies.json'

async def logiqs_login_async(username: str, password: str) -> dict:
    logger.info("🔐 Starting Logiqs authentication...")
    logger.info(f"🌐 Target URL: {LOGIQS_URL}")
    logger.info(f"👤 Username: {username}")
    logger.info(f"🔑 Password: {'*' * len(password)} (length: {len(password)})")
    
    async with async_playwright() as p:
        logger.info("🚀 Launching Chromium browser...")
        browser = await p.chromium.launch(headless=True, slow_mo=1000)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            logger.info("🌐 Navigating to Logiqs login page...")
            await page.goto(LOGIQS_URL)
            logger.info(f"📍 Current URL: {page.url}")
            
            logger.info("⏳ Waiting for login form to load...")
            await page.wait_for_selector('#txtUsername2', timeout=15000)
            logger.info("✅ Login form loaded successfully")
            
            logger.info("📝 Filling in username...")
            await page.fill('#txtUsername2', username)
            logger.info("✅ Username filled")
            
            logger.info("📝 Filling in password...")
            await page.fill('#txtPassword2', password)
            logger.info("✅ Password filled")
            
            logger.info("🔑 Clicking login button...")
            await page.click('#btnLogin2')
            logger.info("✅ Login button clicked")
            
            logger.info("⏳ Waiting for authentication to complete...")
            await asyncio.sleep(5)
            
            logger.info(f"📍 Current URL after login attempt: {page.url}")
            
            if 'Login.aspx' in page.url:
                logger.error("❌ Still on login page - authentication failed")
                error_text = await page.inner_text('body')
                logger.error(f"📋 Page content: {error_text[:500]}...")
                raise Exception(f'Login failed: {error_text}')
            
            logger.info("✅ Successfully navigated away from login page")
            
            logger.info("🍪 Extracting cookies...")
            cookies = await context.cookies()
            logger.info(f"🍪 Found {len(cookies)} cookies")
            
            # Log cookie names for debugging
            cookie_names = [cookie['name'] for cookie in cookies]
            logger.info(f"🍪 Cookie names: {cookie_names}")

            # Capture the user-agent from the browser context
            user_agent = await page.evaluate("() => navigator.userAgent")
            logger.info(f"🕵️ User-Agent used for login: {user_agent}")

            logger.info("💾 Saving cookies to file...")
            save_cookies({
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'url': LOGIQS_URL,
                'cookies': cookies,
                'user_agent': user_agent
            })
            logger.info(f"💾 Cookies saved to: {COOKIES_FILE}")
            
            logger.info("✅ Authentication completed successfully!")
            return {
                'success': True,
                'message': 'Successfully authenticated with Logiqs',
                'cookieCount': len(cookies)
            }
            
        except Exception as e:
            logger.error(f"❌ Logiqs login failed: {str(e)}")
            logger.error(f"🔍 Error type: {type(e).__name__}")
            import traceback
            logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
            raise Exception(f'Logiqs login failed: {str(e)}')
        finally:
            logger.info("🔒 Closing browser...")
            await browser.close()
            logger.info("✅ Browser closed") 