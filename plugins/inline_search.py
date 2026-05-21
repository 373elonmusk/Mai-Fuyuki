import logging
from pyrogram import Client, filters
from pyrogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from plugins.Dreamxfutures.Imdbposter import get_movie_detailsx, get_movie_details

logger = logging.getLogger(__name__)


@Client.on_inline_query()
async def inline_search(client, query: InlineQuery):
    search_text = query.query.strip()

    # Empty query — show prompt
    if not search_text:
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title="🔍 Search Movie or Series",
                    description="Type a movie or web series name to search...",
                    input_message_content=InputTextMessageContent(
                        "Please type a movie or series name to search."
                    ),
                )
            ],
            cache_time=0,
        )
        return

    try:
        # Try TMDB first, fallback to IMDB
        details = await get_movie_detailsx(search_text)
        if not details:
            details = await get_movie_details(search_text, bulk=True)
            if details and isinstance(details, list):
                details = details[0] if details else None

        if not details:
            await query.answer(
                results=[
                    InlineQueryResultArticle(
                        title="❌ No Results Found",
                        description=f"No movie/series found for: {search_text}",
                        input_message_content=InputTextMessageContent(
                            f"❌ No results found for **{search_text}**"
                        ),
                    )
                ],
                cache_time=10,
            )
            return

        title = details.get("title") or "Unknown Title"
        year = details.get("year") or ""
        rating = details.get("rating") or "N/A"
        genres = details.get("genres", [])
        if isinstance(genres, list):
            genres_str = ", ".join(genres[:3])
        else:
            genres_str = str(genres)
        plot = details.get("plot") or "No description available."
        if len(plot) > 300:
            plot = plot[:300] + "..."
        kind = details.get("kind") or ""
        poster_url = details.get("poster_url") or details.get("poster") or None
        imdb_id = details.get("imdb_id") or ""
        imdb_url = details.get("url") or (f"https://www.imdb.com/title/{imdb_id}" if imdb_id else "")

        # Build caption
        caption = (
            f"🎬 <b>{title}</b>"
            + (f" ({year})" if year else "")
            + (f"\n📺 <b>Type:</b> {kind.capitalize()}" if kind else "")
            + (f"\n⭐ <b>Rating:</b> {rating}" if rating and rating != "N/A" else "")
            + (f"\n🎭 <b>Genre:</b> {genres_str}" if genres_str else "")
            + f"\n\n📝 {plot}"
        )

        # Buttons
        buttons = []
        if imdb_url:
            buttons.append([InlineKeyboardButton("🌐 View on IMDb", url=imdb_url)])

        reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

        if poster_url:
            try:
                results = [
                    InlineQueryResultPhoto(
                        photo_url=poster_url,
                        thumb_url=poster_url,
                        title=f"🎬 {title} ({year})" if year else f"🎬 {title}",
                        description=f"⭐ {rating} | {genres_str}" if genres_str else f"⭐ {rating}",
                        caption=caption,
                        parse_mode="html",
                        reply_markup=reply_markup,
                    )
                ]
                await query.answer(results=results, cache_time=30)
                return
            except Exception as e:
                logger.warning(f"Photo result failed: {e}, falling back to article")

        # Fallback: article result
        results = [
            InlineQueryResultArticle(
                title=f"🎬 {title} ({year})" if year else f"🎬 {title}",
                description=f"⭐ {rating} | {genres_str}" if genres_str else f"⭐ {rating}",
                input_message_content=InputTextMessageContent(
                    caption, parse_mode="html"
                ),
                reply_markup=reply_markup,
            )
        ]
        await query.answer(results=results, cache_time=30)

    except Exception as e:
        logger.exception(f"Inline search error: {e}")
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title="⚠️ Error",
                    description="Something went wrong, try again.",
                    input_message_content=InputTextMessageContent(
                        "⚠️ Something went wrong. Please try again."
                    ),
                )
            ],
            cache_time=0,
        )
