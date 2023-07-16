import logging
import time
from typing import Optional

from pythorhead import Lemmy
from pythorhead.types import SortType, ListingType

from nba.utils import GameUtils


class PostUtils:
    POST_GAME_PREFIX = "[Post Game Thread] "
    GAME_THREAD_PREFIX = "[Game Thread] "
    DAILY_INDEX_PREFIX = "Daily Discussion + Game Thread Index "

    @staticmethod
    def get_post_game_id(gamepost):
        return gamepost["body"][-16:-6]

    @staticmethod
    def game_info(game):
        return f"{game['gameId']}: {game['gameStatusText']} [{GameUtils.get_game_status(game)}] - " \
               f"{game['homeTeam']['teamName']} vs {game['awayTeam']['teamName']}"

    @staticmethod
    def safe_api_call(fun, **kwargs):
        retries = 1
        while not (response := fun(**kwargs)) and retries < 10:
            retries += 1
            logging.warning(f"Failed to call {fun.__name__}({kwargs}), will retry again in {retries * 5} seconds")
            time.sleep(retries * 5)

        if retries >= 10:
            raise RuntimeError("Failed to invoke Lemmy API")
        else:
            return response

    @staticmethod
    def get_last50_posts(lemmy: Lemmy, community_id: Optional[int] = None,
                         community_name: Optional[str] = None,
                         saved_only: Optional[bool] = None,
                         sort: Optional[SortType] = None,
                         type_: Optional[ListingType] = None):
        posts = []
        for i in range(1, 6):
            response = PostUtils.safe_api_call(lemmy.post.list, community_id=community_id,
                                               community_name=community_name,
                                               sort=sort,
                                               type_=type_, page=i)

            # ugly hack since there are very few saved pages....
            if saved_only:
                posts.extend([post['post'] for post in response if not post['post']["deleted"] and post['saved']])
            else:
                posts.extend([post['post'] for post in response if not post['post']["deleted"]])
        return posts
