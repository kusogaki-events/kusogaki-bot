from asyncio import Semaphore, gather, sleep
from datetime import datetime
from random import uniform
from typing import Dict, List, Optional, Tuple

from discord import Embed
from httpx import AsyncClient, ReadTimeout, RequestError, post

from kusogaki_bot.features.recommendation.data import MediaRec


class RecommendationService:
    """Service for handling requests/scoring for animanga recommendations"""

    def __init__(self):
        self.known_manga_recs = {}
        self.known_anime_recs = {}

    async def query_user_statistics(
        self, anilist_username: str, media_type: str
    ) -> Optional[Dict]:
        """
        Queries anilist for user statistics used for weighting/scoring of animanga recommendations

        Args:
            anilist_username (str): Anilist username to query
            media_type (str): Specifies anime or manga statistics

        Returns:
            dict: Anilist media type user statistics data
        """
        query = f"""
        query User($name: String) {{
          User(name: $name) {{
            statistics {{
              {media_type} {{
                count
                meanScore
                standardDeviation
                genres {{
                  count
                  genre
                  meanScore
                }}
              }}
            }}
            favourites {{
              {media_type} {{
                nodes {{
                  id
                }}
              }}
            }}
          }}
        }}
        """
        variables = {'name': anilist_username}

        try:
            response = post(
                url='https://graphql.anilist.co',
                json={'query': query, 'variables': variables},
            )
        except ReadTimeout:
            return None
        if response.status_code != 200:
            return None
        if not response.json()['data']['User']['statistics'][media_type]['count']:
            return None
        user_data = response.json()['data']['User']
        favorites = [fav['id'] for fav in user_data['favourites'][media_type]['nodes']]
        user_data['favourites'][media_type] = favorites

        return user_data

    async def query_media_recs(
        self, anilist_username: str, media_type: str, watched_count: int
    ) -> Optional[List[Dict]]:
        """
        Queries anilist for user list data used for weighting/scoring of animanga recommendations

        Args:
            anilist_username (str): Anilist username to query
            media_type (str): Specifies anime or manga statistics
            watched_count (int): Completed entries on user's list

        Returns:
            Optional[list[dict]]: Anilist media list collection data
        """
        query = """
        query MediaListCollection($userName: String, $type: MediaType, $statusNotIn: [MediaListStatus], $sort: [RecommendationSort], $perPage: Int, $perChunk: Int, $chunk: Int) {
          MediaListCollection(userName: $userName, type: $type, status_not_in: $statusNotIn, perChunk: $perChunk, chunk: $chunk) {
            lists {
              entries {
                score
                status
                media {
                  id
                  popularity
                  recommendations(sort: $sort, perPage: $perPage) {
                    nodes {
                      rating
                      mediaRecommendation {
                        id
                        coverImage {
                          large
                        }
                        genres
                        meanScore
                        popularity
                        title {
                          romaji
                        }
                        relations {
                          edges {
                            relationType
                          }
                          nodes {
                            id
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

        chunk_size = 100
        max_concurrent = Semaphore(6)

        async def query_list_recommendations(session: AsyncClient, chunk):
            max_attempts = 3
            for attempt in range(max_attempts):
                req_vars = {
                    'userName': anilist_username,
                    'type': media_type.upper(),
                    'statusNotIn': 'PLANNING',
                    'perPage': 8,
                    'sort': 'RATING_DESC',
                    'perChunk': chunk_size,
                    'chunk': chunk,
                }
                async with max_concurrent:
                    try:
                        data = await session.post(
                            url='https://graphql.anilist.co',
                            json={'query': query, 'variables': req_vars},
                            timeout=10,
                        )
                        if data.status_code == 200:
                            return data
                    except ReadTimeout:
                        pass

                await sleep((1.75**attempt) + uniform(0, 1))
            return None

        tasks: list = []

        async with AsyncClient() as client:
            for i in range(1, watched_count // chunk_size + 2):
                tasks.append(query_list_recommendations(client, i))

            raw_list_data = await gather(*tasks)

        full_rec_list: list = []
        for data_chunk in raw_list_data:
            if data_chunk is None:
                continue
            if data_chunk.status_code != 200:
                continue
            data_chunk = data_chunk.json()['data']['MediaListCollection']['lists']
            for anime_list in data_chunk:
                anime_list = anime_list['entries']
                full_rec_list += anime_list

        return full_rec_list

    async def fetch_recommendations(
        self, anilist_username: str, media_type: str
    ) -> Tuple[List, Dict, List]:
        """
        Wrapper function for fetching anilist data for animanga recs

        Args:
            anilist_username (str): Anilist username to query
            media_type (str): Specifies anime or manga statistics

        Returns:
            tuple: Tuple containing user list data, user statistics, and favorites

        Raises:
            RequestError if either user statistics or list data is empty
        """
        user_data = await self.query_user_statistics(
            anilist_username=anilist_username, media_type=media_type
        )
        if not user_data:
            raise RequestError('Error obtaining data from anilist.')
        user_stats = user_data['statistics'][media_type]
        user_favorites = user_data['favourites'][media_type]

        list_data = await self.query_media_recs(
            anilist_username=anilist_username,
            media_type=media_type,
            watched_count=user_stats['count'],
        )
        if not list_data:
            raise RequestError('Error obtaining data from anilist.')

        return list_data, user_stats, user_favorites

    def calculate_rec_scores(
        self, list_data: List[Dict], user_stats: Dict, user_favorites: List[int]
    ) -> List[MediaRec]:
        """
        Scoring algorithm for animanga recs

        Args:
            list_data (list[dict]): Anilist media list collection data
            user_stats (dict): Anilist user statistics
            user_favorites (list[int]): List of user favorited media IDs

        Returns:
            list[MediaRec]: List of user's recommendations
        """
        max_popularity = 0
        global_mean = 65
        genre_count_weight = 0.16
        popularity_exp = 1.5
        global_scale_exp = 0.35

        # Obtain max user score, collect watched show info
        max_score = 1
        seen_show_ids = []
        for entry in list_data:
            seen_show_ids.append(entry['media']['id'])
            if entry['score'] > max_score:
                max_score = entry['score']
            if entry['media']['popularity'] > max_popularity:
                max_popularity = entry['media']['popularity']

        seen_show_ids = set(seen_show_ids)

        # Get user genre scores
        user_genre_scores = {}
        for genre in user_stats['genres']:
            genre_name = genre['genre']
            if not genre['meanScore']:
                user_genre_scores[genre_name] = 0
            else:
                user_genre_scores[genre_name] = (
                    genre['meanScore'] - user_stats['meanScore']
                ) / 100 + (genre['count'] - 0.5 * len(seen_show_ids)) / len(
                    seen_show_ids
                ) * genre_count_weight

        recommendation_scores: dict[int:MediaRec] = {}
        for entry in list_data:
            if not entry['media']['recommendations']['nodes']:
                continue
            if entry['status'] == 'DROPPED':
                continue

            # Weight each show's recommendation by strength of recommendation on the site
            max_recs = max(8, len(entry['media']['recommendations']['nodes']))
            max_rec_rating = entry['media']['recommendations']['nodes'][0]['rating']
            if max_rec_rating == 0:
                continue

            favorite_weight = 3 if entry['media']['id'] in user_favorites else 1

            for show_rec in entry['media']['recommendations']['nodes'][0:max_recs]:
                # Filter out bad data from anilist
                if show_rec['mediaRecommendation'] is None:
                    continue
                if show_rec['mediaRecommendation']['id'] in seen_show_ids:
                    continue
                if not show_rec['mediaRecommendation']['meanScore']:
                    show_rec['mediaRecommendation']['meanScore'] = global_mean

                # Filter out shows with prequels that have not been seen yet
                try:
                    if any(
                        related_show[0]['relationType'] == 'PREQUEL'
                        and related_show[1]['id'] not in seen_show_ids
                        for related_show in zip(
                            show_rec['mediaRecommendation']['relations']['edges'],
                            show_rec['mediaRecommendation']['relations']['nodes'],
                        )
                    ):
                        continue
                except KeyError:
                    pass

                # Scoring weights
                node_score_weight = 0 if entry['score'] == 0 else 0.8
                rec_show_score_weight = 1
                rec_pop_factor = (
                    1 - show_rec['mediaRecommendation']['popularity'] / max_popularity
                )
                rec_genre_score_weight = 1.5
                rec_pop_factor = (
                    rec_pop_factor**popularity_exp if rec_pop_factor > 0 else 0.1
                )
                rec_total_weight = show_rec['rating'] / max_rec_rating

                # Scoring
                node_score = node_score_weight * (
                    entry['score'] / max_score - user_stats['meanScore'] / 100
                )
                rec_show_score = (
                    rec_show_score_weight
                    * (show_rec['mediaRecommendation']['meanScore'] - global_mean)
                    / 100
                )
                rec_genre_score = 0
                for genre in show_rec['mediaRecommendation']['genres']:
                    try:
                        rec_genre_score += user_genre_scores[genre] / len(
                            show_rec['mediaRecommendation']['genres']
                        ) ** (1 / 2)
                    except (KeyError, ZeroDivisionError):
                        continue
                    rec_genre_score *= rec_genre_score_weight

                total_rec_score = (
                    (node_score + rec_show_score + rec_genre_score)
                    * rec_total_weight
                    * rec_pop_factor
                    * favorite_weight
                )
                if show_rec['mediaRecommendation']['id'] not in recommendation_scores:
                    recommendation_scores[show_rec['mediaRecommendation']['id']] = (
                        MediaRec(
                            media_id=show_rec['mediaRecommendation']['id'],
                            title=show_rec['mediaRecommendation']['title']['romaji'],
                            genres=[
                                genre.lower()
                                for genre in show_rec['mediaRecommendation']['genres']
                            ],
                            cover_url=show_rec['mediaRecommendation']['coverImage'][
                                'large'
                            ],
                            mean_score=show_rec['mediaRecommendation']['meanScore'],
                        )
                    )
                recommendation_scores[
                    show_rec['mediaRecommendation']['id']
                ].score += total_rec_score

        recommendation_scores = list(recommendation_scores.values())

        # Add random variation of +/- 20%, then sort recommendations by score
        for rec in recommendation_scores:
            rec.score *= uniform(0.8, 1.2)

        recommendation_scores = [rec for rec in recommendation_scores if rec.score >= 0]
        recommendation_scores.sort(reverse=True)

        # Normalize scores and apply filter for logical percentages
        max_score = recommendation_scores[0].score
        for rec in recommendation_scores:
            rec.score = (rec.score / max_score) ** global_scale_exp * 100

        return recommendation_scores

    async def check_recommendation(
        self,
        anilist_username: str,
        media_type: str,
        force_update: bool = False,
    ) -> None:
        """
        Check if recommendations exist in cache and are up to date, and fetch new data if not cached.

        Args:
            anilist_username (str): Anilist username to recommend for
            media_type (str): Anilist user statistics
            force_update (bool): If true, will always fetch new data from anilist instead of using cache
        """
        known_recs = (
            self.known_manga_recs if media_type == 'manga' else self.known_anime_recs
        )

        # Use cached data unless cached data does not exist or is outdated
        try:
            time_delta = (
                datetime.now()
                - datetime.strptime(
                    known_recs[anilist_username]['date'], '%Y/%m/%d %H:%M:%S'
                )
            ).total_seconds()
        except KeyError:
            time_delta = 0
        if anilist_username not in known_recs or force_update or time_delta > 345600:
            list_data, user_stats, user_favorites = await self.fetch_recommendations(
                anilist_username=anilist_username,
                media_type=media_type,
            )
            recommendation_scores = self.calculate_rec_scores(
                list_data=list_data,
                user_stats=user_stats,
                user_favorites=user_favorites,
            )

            if media_type.lower() == 'manga':
                self.known_manga_recs[anilist_username] = {
                    'date': datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                    'recs': recommendation_scores,
                }
            else:
                self.known_anime_recs[anilist_username] = {
                    'date': datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                    'recs': recommendation_scores,
                }

        return None

    def get_rec_embed(
        self, anilist_username: str, media_type: str, genre: str, page: int
    ) -> Embed:
        """
        Generate an embed with the recommended media.

        Args:
            anilist_username (str): Anilist username to recommend for
            media_type (str): Specify to recommend manga/anime
            genre (str): Limit recommendations to specified genre
            page (int): Which recommendation in user's rec list to display

        Returns:
            Embed: Embed displaying recommended media and corresponding information
        """
        if media_type == 'manga':
            color = 0x7CD553
            recs = self.known_manga_recs[anilist_username]['recs']
        else:
            color = 0x3BAFEB
            recs = self.known_anime_recs[anilist_username]['recs']

        if genre:
            recs = [rec for rec in recs if genre in rec.genres]

        embed = Embed(colour=color, title=f'Recommendation for {anilist_username}')
        if not recs:
            embed.description = "I couldn't find any recommendations!"
            return embed

        max_page = min(20, len(recs))
        rec = recs[page % max_page]

        embed.description = f"""
**{rec.title}** - https://anilist.co/{media_type}/{rec.media_id}/
{rec.mean_score}% | *{', '.join(rec.genres)}*
*Recommendation strength - {rec.score:.2f}%*
"""
        embed.set_thumbnail(url=rec.cover_url)
        return embed
