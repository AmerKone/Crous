import requests
from bs4 import BeautifulSoup
import time
from discord_webhook import DiscordWebhook
import re 
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crous_checker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# URL du site CROUS à scraper
url = "https://trouverunlogement.lescrous.fr/tools/37/search?bounds=2.9679677_50.6612596_3.125725_50.6008264"
# URL du webhook Discord
discord_webhook_url = "https://discord.com/api/webhooks/1410564661270810787/lkQFgm1wLBSLPg2NVnbQQqSxVJYnm0RrTsuScFk0eZQmvbjm9HeOJH0gzVW3ZbWas8a9"

buffer = set()

def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def check_logements():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    session = create_session()
    response = session.get(url, headers=headers, timeout=10)
    
    if response.status_code != 200:
        logger.error(f"Failed to fetch data: Status code {response.status_code}")
        return None
        
    soup = BeautifulSoup(response.content, "lxml")
    #<h2 class="SearchResults-desktop fr-h4 svelte-11sc5my">321 logements trouvés</h2>
    logements_montpellier = soup.find_all('h2', {'class':'SearchResults-desktop fr-h4 svelte-11sc5my'})
    
    logger.debug(f"Found results: {logements_montpellier[0].text}")
    
    if "Aucun" not in logements_montpellier[0].text:
        logements_disponibles = logements_montpellier[0].text
        logger.info(f"Available housing found: {logements_disponibles}")
        logements = soup.find_all('div', {'class': 'fr-card svelte-12dfls6'})
        for logement in logements:
            title = logement.find('h3', {'class': 'fr-card__title'}).text.strip()
                
            url_element = logement.find('a')
            url_path = url_element['href'] if url_element else ''
            if url_path not in buffer:
                buffer.add(url_path)
                base_url = "https://trouverunlogement.lescrous.fr"
                full_url = base_url + url_path
                send_discord_notification(f"{title} - {full_url}")
    else :
        return None

def send_discord_notification(message):
    logger.info(f"Sending Discord notification: {message}")
    webhook = DiscordWebhook(url=discord_webhook_url, content=message)
    response = webhook.execute()

def main():
    logger.info("Starting CROUS housing checker")
    while True:
        try:
            check_logements()
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            logger.error(error_message, exc_info=True)
            send_discord_notification(error_message)
        
        # Increase sleep time to avoid being rate limited
        time.sleep(30)  # Changed from 5 to 30 seconds

if __name__ == "__main__":
    main()

