import asyncio
import logging
import sys
from os import getenv
import random

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from aiohttp import ClientSession, ClientError

from urllib.parse import quote
from bs4 import BeautifulSoup

from cinemabot_db import create_db, get_history, get_statistics, add_search_history, add_to_statistics

TOKEN = getenv("BOT_TOKEN")
GOOGLE_API_KEY = getenv("GOOGLE_API_KEY")
GOOGLE_CX = getenv("GOOGLE_CX")
BASE_URL = "https://www.kino-teatr.ru/search/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\
    (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Referer": "https://www.kino-teatr.ru/search/",
    "Content-Type": "application/x-www-form-urlencoded; charset=windows-1251"
}
CODE = 'windows-1251'
MAX_MESSAGE_LENGTH = 1024

logger = logging.getLogger(__name__)
dp = Dispatcher()


async def check_url_validity(url):
    try:
        async with ClientSession() as session:
            try:
                async with session.get(url, timeout=2.5) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error(f"Invalid link (status code: {response.status}): {url}")
                        return False
            except TimeoutError as e:
                logger.error(str(e))
                return False
    except ClientError as e:
        logger.error(f"Error checking URL {url}: {str(e)}")
        return False


async def get_google_answers(query_text, api_key, cx, num_results=10):
    """
    Find the link where a movie can be watched
    """
    query = query_text + '+смотреть+онлайн+бесплатно'
    encoded_query = quote(query)
    # url = f'https://www.google.com/search?q={encoded_query}&num={num_results}'
    url = f'https://www.googleapis.com/customsearch/v1?q={encoded_query}&key={api_key}&cx={cx}&num={num_results}'

    async with ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error: status code {response.status}")
                    return []
                try:
                    search_results = await response.json()
                except Exception as e:
                    logger.error(f"Failed to parse JSON response. {str(e)}")
                    return []

                answers = []
                for item in search_results.get('items', []):
                    link = item['link']
                    is_valid = await check_url_validity(link)
                    if is_valid:
                        answer = {
                            'link': link,
                        }
                        answers.append(answer)
                        break
                    else:
                        logger.warning(f"Skipping invalid link: {link}")
                return answers

        except ClientError as e:
            logger.error(f"Error getting URL {url}: {str(e)}")
            return []


async def fetch_movie_details(url):
    """
    Extract detailed description
    """
    async with ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                logger.error(f"Status: {response.status}")
                return None
            html = await response.text()

    soup = BeautifulSoup(html, 'html.parser')

    rating_tag = soup.select_one('.rating_digits b[itemprop="ratingValue"]')
    rating = rating_tag.text.strip() if rating_tag else None

    description_tag = soup.select_one('.big_content_block [itemprop="description"]')
    description = description_tag.text.strip() if description_tag else None

    movie_name_tag = soup.find('h1', itemprop="name").text.strip()

    info_params = soup.select('.info_table_param')
    info_data = soup.select('.info_table_data')
    title, year, country = None, None, None

    for param, data in zip(info_params, info_data):
        param_text = param.text.strip().lower()
        data_text = data.text.strip()
        if "год" in param_text:
            year = data_text
        elif "страна" in param_text:
            country = data_text
        elif 'оригинальное название' in param_text:
            title = data_text
    return {
        "title": title if title else movie_name_tag,
        "rating": rating if rating else "be the first to rate!",
        "description": description if description else "it's just great.",
        "year": year if year else "let's assume it’s timeless :)",
        "country": country if country else "it’s a global masterpiece :)",
    }


async def fetch_movie_annotations(movie_name):
    """
    Extract movies annotations based on names
    """
    search = "найти"
    text_encoded = movie_name.encode(CODE)
    search_encoded = search.encode(CODE)

    text_urlencoded = quote(text_encoded)
    search_urlencoded = quote(search_encoded)

    query_string = f"text={text_urlencoded}&search={search_urlencoded}&acter=on&movie=on"

    async with ClientSession() as session:
        async with session.post(BASE_URL, data=query_string, headers=HEADERS, allow_redirects=False) as response:
            if response.status != 302:
                logger.error(f"Status: {response.status}")
                html = await response.text(encoding=CODE)
                logger.info("HTML response:", html[:500])
                return None

            redirect_url = response.headers.get("Location")
            if not redirect_url:
                logger.warning("No redirections")
                return None

            redirect_url = f"https://www.kino-teatr.ru{redirect_url}"
            logger.info(f"Redirecting to: {redirect_url}")

            async with session.get(redirect_url, headers=HEADERS) as get_response:
                html = await get_response.text(encoding=CODE)
                soup = BeautifulSoup(html, 'html.parser')

                results = soup.find_all('div', class_='list_item')
                for result in results:
                    link = result.find('a', href=True)
                    if link and 'annot' in link['href']:
                        return f"https://www.kino-teatr.ru{link['href']}"
    return None


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    await message.answer(
        f"Hey, {html.bold(message.from_user.full_name)}! 🍿\nI'm CinemaBot, your go-to assistant for discovering\
        movies and series. Just tell me the name, and I'll find the details you need")


@dp.message(Command(commands=["help"]))
async def command_help_handler(message: Message) -> None:
    """
    This handler receives messages with `/help` command
    """
    await message.answer(
        f"🎬 Simply enter the {html.bold('name')} of the movie, series, or whatever\n\n"
        f"Here are some useful {html.bold('commands')} to interact with me:\n\n"
        f"/start - {html.bold("Start")} the bot\n"
        f"/history - View your {html.bold("search history")}\n"
        f"/stats - Get {html.bold("statistics")} of search queries\n"
        f"/random - Get a {html.bold("random movie")} recommendation\n\n"
    )


@dp.message(Command(commands=["random"]))
async def command_random_handler(message: Message) -> None:
    """
    This handler receives messages with `/random` command and generates a random movie
    """
    start_id = 100000
    end_id = 189990

    async with ClientSession() as session:
        while True:
            random_id = random.randint(start_id, end_id)
            random_movie_url = f"https://www.kino-teatr.ru/kino/movie/hollywood/{random_id}/annot/"
            async with session.get(random_movie_url) as response:
                if response.status == 200:
                    await message.answer(random_movie_url)
                    break
                else:
                    logger.warning(f"ID {random_id} not found...")


@dp.message(Command(commands=["history"]))
async def command_history_handler(message: Message):
    """
    This handler receives messages with `/history` command and displays the search history
    """
    user_id = message.from_user.id
    history_message = get_history(user_id)
    await message.answer(history_message[:4 * MAX_MESSAGE_LENGTH])


@dp.message(Command(commands=["stats"]))
async def command_stats_handler(message: Message):
    """
    This handler receives messages with `/stats` command and displays the statistics
    """
    user_id = message.from_user.id
    stats_message = get_statistics(user_id)
    await message.answer(stats_message[:4 * MAX_MESSAGE_LENGTH])


@dp.message()
async def films_handler(message: Message) -> None:
    """
    This handler receives a message with a movie name and sends the data about it
    """
    annotation_url = await fetch_movie_annotations(message.text)

    if annotation_url:
        details = await fetch_movie_details(annotation_url)
        if not details:
            await message.answer("No data found :(")
            return

        response_text = (
            f"🎬 Title: {details.get('title')}\n\n"
            f"▫️ Year: {details.get('year')}\n"
            f"▫️ Country: {details.get('country')}\n"
            f"▫️ Rating: {details.get('rating')}\n\n"
            f"▫️ Description:\n{details.get('description')}\n\n"
        )

        answers = await get_google_answers(message.text, GOOGLE_API_KEY, GOOGLE_CX)
        google_link = answers[0]['link'] if answers else "No links found :("

        movie_link = f"🔗 Watch: {google_link}"
        full_message = response_text + movie_link

        if len(full_message) > MAX_MESSAGE_LENGTH:
            max_description_length = MAX_MESSAGE_LENGTH - len(movie_link) - 1
            truncated_description = response_text[:max_description_length].rsplit(' ', 1)[0] + "..."
            full_message = truncated_description + movie_link

        await message.answer_photo(
            annotation_url.replace("/annot/", "/foto/"),
            caption=full_message
        )
        add_to_statistics(message.from_user.id, message.text)
    else:
        logger.error("No annotation found")
        await message.answer("No annotation found :(")

    add_search_history(message.from_user.id, message.text)


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    create_db()
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
