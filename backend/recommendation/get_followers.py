import aiohttp
import asyncio
import csv
import time
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch(session, url, semaphore):
    """Fetch content asynchronously for a given URL"""
    async with semaphore:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    status = "success"
                else:
                    content = None
                    status = "failed"
        except Exception as e:
            content = None
            status = str(e)
        return {"url": url, "content": content, "status": status}


async def scrape(urls, max_concurrent=10):
    """Fetch all pages asynchronously"""
    semaphore = asyncio.Semaphore(max_concurrent)
    connector = aiohttp.TCPConnector(limit=max_concurrent)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    return results


def parse_members(pages):
    """Parsing using BeautifulSoup to extract member names, followers, and following."""
    all_members = []
    
    for page in pages:
        if page["content"]:
            html = page["content"]
            soup = BeautifulSoup(html, "html.parser")
            
            for td in soup.find_all("td", class_="table-person"):
                member = {}
                
                # Extract member ID (href of the first <a> tag)
                member_link = td.find("a", href=True)
                if member_link:
                    member["id"] = member_link["href"].strip('/')
                    
                # Extract followers and following counts
                metadata = td.find("small", class_="metadata")
                if metadata:
                    links = metadata.find_all("a", class_="_nobr")
                    if len(links) >= 2:
                        member["followers"] = int(links[0].text.split('\xa0')[0].replace(',', ''))
                        member["following"] = int(links[1].text.split()[-1].replace(',', ''))
                
                all_members.append(member)
        else:
            print(f"Failed to fetch or parse URL: {page['url']}")
    
    return all_members


def write_members_to_csv(members, filename="data/members_with_followers.csv"):
    """Appends member data to a CSV file."""
    if not members:
        print("No data to write.")
        return
    
    keys = members[0].keys()
    file_exists = False
    
    try:
        with open(filename, mode="r", encoding="utf-8") as file:
            file_exists = True
    except FileNotFoundError:
        pass
    
    with open(filename, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        if not file_exists:
            writer.writeheader()
        writer.writerows(members)

    print(f"Data successfully appended to {filename}")


def get_members(likes_urls):

    for likes_url in likes_urls:
        num_pages = 256  # 256 is the max number of accessible pages 
        start = time.time()

        # Create URLs for each page
        urls = [
            likes_url + f"page/{page+1}/"
            for page in range(num_pages)
        ]

        # Fetch content asynchronously
        results = asyncio.run(scrape(urls))

        # Parse each page sequentially
        member_data = parse_members(results)

        write_members_to_csv(member_data)

        # save ids to .csv
        # write_results(member_ids)

        end = time.time()
        print(f"Scraping and parsing of {len(urls)} urls finished in {end-start} seconds")


if __name__ == "__main__":

    # some reviews with a lot of activity
    likes_urls = [
        # 'https://letterboxd.com/varghese_no1/film/night-on-earth/likes/'
        # 'https://letterboxd.com/fumilayo/film/bottoms/likes/',
        # 'https://letterboxd.com/girlsnoopy/film/nosferatu-2024/likes/',
        # 'https://letterboxd.com/thediegoandaluz/film/the-brutalist/likes/',
        # 'https://letterboxd.com/screeningnotes/film/mulholland-drive/likes/',
        # 'https://letterboxd.com/usercillian/film/full-metal-jacket/likes/',
        # 'https://letterboxd.com/jay/film/oldboy/1/likes/',
        # 'https://letterboxd.com/andredenervaux/film/paris-texas/1/likes/',
        # 'https://letterboxd.com/elementarii/film/lost-highway/likes/',
        # 'https://letterboxd.com/sublimeken/film/lost-highway/likes/',
        # 'https://letterboxd.com/usercillian/film/apocalypse-now/likes/',
        # 'https://letterboxd.com/incomingmail/film/anora/likes/',
        # 'https://letterboxd.com/aniawatchesmvs/film/mickey-17/likes/',
        # 'https://letterboxd.com/wizardchurch/film/the-godfather/likes/',
        # 'https://letterboxd.com/kfavs/film/requiem-for-a-dream/1/likes/',
        # 'https://letterboxd.com/hewasthrfriendd/film/spirited-away/likes/',
        # 'https://letterboxd.com/demiadejuyigbe/film/alien/likes/',
        # 'https://letterboxd.com/riverjphoenix/film/alien/likes/'
        # 'https://letterboxd.com/tototoro/film/american-psycho/1/likes/',
        # 'https://letterboxd.com/cobrarocky/film/fallen-angels/likes/',
        # 'https://letterboxd.com/aegxpredator/film/gladiator-2000/3/likes/',
        # 'https://letterboxd.com/sophiedarcy/film/gladiator-2000/likes/',
        # 'https://letterboxd.com/deathproof/film/the-lord-of-the-rings-the-two-towers/likes/',
        # 'https://letterboxd.com/truman/film/memento/likes/',
        # 'https://letterboxd.com/doinkdedoink/film/memento/likes/',
        # 'https://letterboxd.com/missgurl/film/perfect-days-2023/likes/'
        # 'https://letterboxd.com/riverjphoenix/film/good-will-hunting/likes/',
        # 'https://letterboxd.com/deathproof/film/synecdoche-new-york/3/likes/',
        # 'https://letterboxd.com/than/film/being-john-malkovich/likes/',
        # 'https://letterboxd.com/coffeevirus/film/adaptation/3/likes/',

        'https://letterboxd.com/franhoepfner/film/the-lord-of-the-rings-the-fellowship-of-the-ring/2/likes/',
        'https://letterboxd.com/alyssaraetho/film/the-silence-of-the-lambs/likes/'


    ]
    get_members(likes_urls)