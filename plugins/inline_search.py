import logging
import asyncio
from pyrogram import Client
from pyrogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from utils import get_poster

logger = logging.getLogger(__name__)


@Client.on_inline_query()
async def inline_search(client, query: InlineQuery):
    search_text = query.query.strip()

    # Empty query
    if not search_text:
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title="🔍 Search Movie or Series",
                    description="Type a movie or web series name...",
                    input_message_content=InputTextMessageContent(
                        "🔍 Type a movie or series name to search."
                    ),
                )
            ],
            cache_time=0,
        )
        return

    try:
        # Use existing IMDBKit bulk search
        bulk_results = await get_poster(search_text, bulk=True)

        if not bulk_results:
            await query.answer(
                results=[
                    InlineQueryResultArticle(
                        title="❌ No Results Found",
                        description=f'No results for: "{search_text}"',
                        input_message_content=InputTextMessageContent(
                            f"❌ No results found for <b>{search_text}</b>\n\nTry a different spelling.",
                            parse_mode="html"
                        ),
                    )
                ],
                cache_time=5,
            )
            return

        inline_results = []

        for movie_brief in bulk_results[:8]:
            try:
                # Get full details for each result
                imdb_id = getattr(movie_brief, 'imdb_id', None)
                if not imdb_id:
                    continue

                details = await get_poster(imdb_id, id=True)
                if not details:
                    continue

                title = details.get('title') or 'Unknown'
                year = str(details.get('year') or '')
                rating = details.get('rating') or 'N/A'
                genres = details.get('genres') or ''
                plot = details.get('plot') or 'No description available.'
                if len(plot) > 250:
                    plot = plot[:250] + '...'
                kind = details.get('kind') or ''
                poster_url = details.get('poster') or None
                imdb_url = details.get('url') or ''

                caption = (
                    f"🎬 <b>{title}</b>"
                    + (f" ({year})" if year else "")
                    + (f"\n📺 <b>Type:</b> {kind.capitalize()}" if kind else "")
                    + (f"\n⭐ <b>Rating:</b> {rating}" if rating and rating != 'N/A' else "")
                    + (f"\n🎭 <b>Genre:</b> {genres}" if genres else "")
                    + f"\n\n📝 {plot}"
                )

                buttons = []
                if imdb_url:
                    buttons.append([InlineKeyboardButton("🌐 View on IMDb", url=imdb_url)])
                reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

                if poster_url:
                    inline_results.append(
                        InlineQueryResultPhoto(
                            photo_url=poster_url,
                            thumb_url=poster_url,
                            title=f"🎬 {title}" + (f" ({year})" if year else ""),
                            description=(f"⭐ {rating} | " if rating and rating != 'N/A' else "") + (kind.capitalize() if kind else ""),
                            caption=caption,
                            parse_mode="html",
                            reply_markup=reply_markup,
                        )
                    )
                else:
                    inline_results.append(
                        InlineQueryResultArticle(
                            title=f"🎬 {title}" + (f" ({year})" if year else ""),
                            description=(f"⭐ {rating} | " if rating and rating != 'N/A' else "") + (kind.capitalize() if kind else ""),
                            input_message_content=InputTextMessageContent(
                                caption, parse_mode="html"
                            ),
                            reply_markup=reply_markup,
                        )
                    )
            except Exception as e:
                logger.warning(f"Skipping result due to error: {e}")
                continue

        if not inline_results:
            await query.answer(
                results=[
                    InlineQueryResultArticle(
                        title="❌ No Results Found",
                        description=f'No results for: "{search_text}"',
                        input_message_content=InputTextMessageContent(
                            f"❌ No results found for <b>{search_text}</b>",
                            parse_mode="html"
                        ),
                    )
                ],
                cache_time=5,
            )
            return

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
