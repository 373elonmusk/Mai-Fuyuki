import logging
import asyncio
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

logger = logging.getLogger(__name__)

TMDB_BEARER_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI2ZGU3YTIyZGU1YjE5YTFjNmUyZGU5ZWEyMzE2ZmQxMCIsIm5iZiI6MTc0NTMyMjQ2Mi41MzMsInN1YiI6IjY4MDc4MWRlYzVjODAzNWZiMDhhNjExNCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.rMMJ2-PBIv8Y7ybxPIEpIlzTEXzuwrm9ruKxAUCAsbw'
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500'


async def tmdb_search(query: str, limit: int = 8):
    """Search TMDB for movies and TV shows, return list of results."""
    url = f"{TMDB_BASE_URL}/search/multi"
    headers = {
        'Authorization': f'Bearer {TMDB_BEARER_TOKEN}',
        'Content-Type': 'application/json;charset=utf-8'
    }
    params = {
        'query': query,
        'language': 'en-US',
        'page': 1,
        'include_adult': 'false'
    }
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url, headers=headers, params=params, ssl=False) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                results = []
                for r in data.get('results', [])[:limit]:
                    mtype = r.get('media_type')
                    if mtype not in ('movie', 'tv'):
                        continue
                    title = r.get('title') or r.get('name') or 'Unknown'
                    year = (r.get('release_date') or r.get('first_air_date') or '')[:4]
                    rating = round(r.get('vote_average', 0), 1)
                    overview = r.get('overview') or 'No description.'
                    if len(overview) > 250:
                        overview = overview[:250] + '...'
                    poster_path = r.get('poster_path')
                    poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else None
                    tmdb_url = f"https://www.themoviedb.org/{mtype}/{r['id']}"
                    results.append({
                        'title': title,
                        'year': year,
                        'rating': rating,
                        'overview': overview,
                        'poster_url': poster_url,
                        'kind': 'Movie' if mtype == 'movie' else 'TV Series',
                        'tmdb_url': tmdb_url,
                        'id': str(r['id']),
                    })
                return results
    except Exception as e:
        logger.error(f"TMDB search error: {e}")
        return []


@Client.on_inline_query()
async def inline_search(client, query: InlineQuery):
    search_text = query.query.strip()

    if not search_text:
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title="🔍 Type a movie or series name",
                    description="Start typing to search...",
                    input_message_content=InputTextMessageContent(
                        "🔍 Type a movie or series name to search."
                    ),
                )
            ],
            cache_time=0,
        )
        return

    try:
        results_data = await tmdb_search(search_text, limit=8)

        if not results_data:
            await query.answer(
                results=[
                    InlineQueryResultArticle(
                        title="❌ No Results Found",
                        description=f'No results for: "{search_text}"',
                        input_message_content=InputTextMessageContent(
                            f"❌ No results found for **{search_text}**\n\nTry a different spelling or name."
                        ),
                    )
                ],
                cache_time=5,
            )
            return

        inline_results = []
        for idx, item in enumerate(results_data):
            title = item['title']
            year = item['year']
            rating = item['rating']
            overview = item['overview']
            poster_url = item['poster_url']
            kind = item['kind']
            tmdb_url = item['tmdb_url']

            caption = (
                f"🎬 <b>{title}</b>"
                + (f" ({year})" if year else "")
                + f"\n📺 <b>Type:</b> {kind}"
                + (f"\n⭐ <b>Rating:</b> {rating}/10" if rating else "")
                + f"\n\n📝 {overview}"
            )

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 View on TMDB", url=tmdb_url)]
            ])

            if poster_url:
                inline_results.append(
                    InlineQueryResultPhoto(
                        photo_url=poster_url,
                        thumb_url=poster_url,
                        title=f"🎬 {title}" + (f" ({year})" if year else ""),
                        description=f"{'⭐ ' + str(rating) + '/10 | ' if rating else ''}{kind}",
                        caption=caption,
                        parse_mode="html",
                        reply_markup=buttons,
                    )
                )
            else:
                inline_results.append(
                    InlineQueryResultArticle(
                        title=f"🎬 {title}" + (f" ({year})" if year else ""),
                        description=f"{'⭐ ' + str(rating) + '/10 | ' if rating else ''}{kind}",
                        input_message_content=InputTextMessageContent(
                            caption, parse_mode="html"
                        ),
                        reply_markup=buttons,
                    )
                )

        await query.answer(results=inline_results, cache_time=30)

    except Exception as e:
        logger.exception(f"Inline search error: {e}")
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title="⚠️ Error Occurred",
                    description="Something went wrong, try again.",
                    input_message_content=InputTextMessageContent(
                        "⚠️ Something went wrong. Please try again."
                    ),
                )
            ],
            cache_time=0,
        )
