import logging

from nba_api.live.nba.endpoints import scoreboard
from pythorhead import Lemmy
from pythorhead.types import FeatureType

from nba.summerleague import summerscoreboard
from nba.utils import PostUtils, GameUtils


def close_yesterdays_post(lemmy, post, cur_scoreboard):
    post_date = (post['name']).split('[')[1].split("]")[0]
    cur_date = cur_scoreboard.score_board_date
    if post_date != cur_date:
        logging.info(f"Daily Thread dates are different {post_date}:{cur_date}, will close the old one")
        PostUtils.safe_api_call(lemmy.post.feature, post_id=post['id'], feature=False,
                                feature_type=FeatureType.Community)
        logging.info(f"UN-FEATURED new Post {post['id']}")


def new_daily_post(lemmy, cur_scoreboard, community_id):
    name = f"{PostUtils.DAILY_INDEX_PREFIX}[{cur_scoreboard.score_board_date}]"
    response = PostUtils.safe_api_call(lemmy.post.create, community_id=community_id, name=name)
    post_id = int(response["post_view"]["post"]["id"])
    logging.info(f"CREATED new Post {post_id}")
    PostUtils.safe_api_call(lemmy.post.feature, post_id=post_id, feature=True, feature_type=FeatureType.Community)
    logging.info(f"FEATURED new Post {post_id}")
    return post_id


def find_game_post(game_type, game_id, posts):
    for post in posts:
        if str(post['name']).startswith(game_type) and 'body' in post and PostUtils.get_post_game_id(post) == game_id:
            return post
    return None


def update_daily_games_post(lemmy, cur_scoreboard, post_id, posts):
    cur_games = cur_scoreboard.games.get_dict()
    body = f"|TIP OFF | HOME | AWAY| GAME THREAD | STATUS | POST GAME THREAD|\n" \
           f"| :--: | :--: | :--: | :--: | :--: | :--: |"
    for game in cur_games:
        game_time = GameUtils.get_game_time_est(game)
        home = f"{game['homeTeam']['teamCity']} {game['homeTeam']['teamName']}"
        away = f"{game['awayTeam']['teamCity']} {game['awayTeam']['teamName']}"
        game_post = find_game_post(PostUtils.GAME_THREAD_PREFIX, game['gameId'], posts)
        post_game_post = find_game_post(PostUtils.POST_GAME_PREFIX, game['gameId'], posts)
        status = GameUtils.get_game_status(game)
        if game_post:
            logging.debug(f"Will add GAME POST: {game_post}")
        if post_game_post:
            logging.debug(f"Will add POST GAME POST: {post_game_post}")
        body = f"{body}\n" \
               f" | {game_time}" \
               f" | {home}" \
               f" | {away}" \
               f" | {'[Game thread](' + game_post['ap_id'] + ')' if game_post else ''}" \
               f" | {status}" \
               f" | {'[Post Game thread](' + post_game_post['ap_id'] + ')' if post_game_post else ''} |"

    PostUtils.safe_api_call(lemmy.post.edit, post_id=int(post_id), body=body)


def get_todays_post_id(daily_posts, cur_scoreboard):
    for post in daily_posts:
        post_date = (post['name']).split('[')[1].split("]")[0]
        if post_date == cur_scoreboard.score_board_date:
            return post['id']


class DailyIndexMaker:
    @staticmethod
    def run(lemmy: Lemmy = None, community_id=None, is_summer_league=False):
        cur_scoreboard = summerscoreboard.SummerScoreBoard() if is_summer_league else scoreboard.ScoreBoard()
        all_posts = PostUtils.get_last50_posts(lemmy=lemmy, community_id=community_id)
        daily_posts = [post for post in all_posts if
                       str(post['name']).startswith(PostUtils.DAILY_INDEX_PREFIX) and post[
                           'featured_community'] is True]

        if len(daily_posts) >= 1:
            # Delete the sticky posts that aren't today's - there really should be only one
            # try to find today, if it doesn't exist - create one
            [close_yesterdays_post(lemmy, post, cur_scoreboard) for post in daily_posts]
            if (post_id := get_todays_post_id(daily_posts, cur_scoreboard)) is None:
                # really should happen only when there's one post (yesterday) and no new one
                post_id = new_daily_post(lemmy, cur_scoreboard, community_id)
        else:
            post_id = new_daily_post(lemmy, cur_scoreboard, community_id)

        logging.info(f"Will now update the daily games post: {post_id}")
        update_daily_games_post(lemmy, cur_scoreboard, post_id, all_posts)