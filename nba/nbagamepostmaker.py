import logging
import time
from datetime import datetime

import pytz
from dateutil import parser
from nba_api.live.nba.endpoints import scoreboard, boxscore
from pythorhead import Lemmy

from .summerleague import summerscoreboard, summerboxscore
from .utils import PostUtils, MarkupUtils


class NBAGamePostMaker:

    def __init__(self, api_base_url, user_name, password, community_name, is_summer_league):
        self.community_name = community_name
        self.password = password
        self.user_name = user_name
        self.community_id = None
        self.is_summer_league = is_summer_league
        self.lemmy = Lemmy(api_base_url)

    def log_in(self):
        if not self.lemmy.log_in(self.user_name, self.password):
            return False

        if not (community := self.lemmy.community.get(name=self.community_name)):
            logging.error(f"Failed to fine Community {self.community_name}")
            return False
        else:
            self.community_id = community["community_view"]["community"]["id"]
            logging.debug(f"community is {self.community_id}:{community}")

        return True

    def process_posts(self):
        lemmy_posts = self.lemmy.post.list(community_id=self.community_id, saved_only="true")
        lemmy_posts = [post for post in lemmy_posts if not post["post"]["deleted"]]

        # Today's Score Board
        scorebox_games = summerscoreboard.SummerScoreBoard().games.get_dict() if self.is_summer_league else scoreboard.ScoreBoard().games.get_dict()
        [logging.info(f"Found game in today's scorebox: {PostUtils.game_info(game)}") for game in scorebox_games]

        upcoming_games = get_upcoming_games(scorebox_games)
        [logging.info(f"Found upcoming game: {PostUtils.game_info(game)}") for game in upcoming_games]
        self.create_new_game_posts(upcoming_games, lemmy_posts)

        live_games = [game for game in scorebox_games if game["gameStatus"] == 2]
        [logging.info(f"Found live game: {PostUtils.game_info(game)}") for game in live_games]
        self.update_live_threads(live_games, lemmy_posts)

        finished_games = [game for game in scorebox_games if game["gameStatus"] == 3]
        [logging.info(f"Found finished game: {PostUtils.game_info(game)}") for game in finished_games]
        self.close_finished_games(finished_games, lemmy_posts)

        orphan_posts = get_orphan_posts(scorebox_games, lemmy_posts)
        [self.close_game(game=post, post_id=post["post"]["id"]) for post in orphan_posts]

    def create_new_game_posts(self, upcoming_games, lemmy_posts):
        for upcoming_game in upcoming_games:
            post_id = None
            for gamepost in lemmy_posts:
                lemmy_game_id = PostUtils.get_post_id(gamepost)
                if upcoming_game["gameId"] == lemmy_game_id:
                    post_id = gamepost["post"]["id"]
            if not post_id:
                self.create_new_game_thread(upcoming_game)

    def create_new_game_thread(self, game):
        logging.info(f"CREATE a new game post: {PostUtils.game_info(game)}")
        name = MarkupUtils.get_thread_title(game)
        body = f"{MarkupUtils.get_match_summary(game)}\n" \
               f"{MarkupUtils.get_footer(game['gameId'])}"
        while not (response := self.lemmy.post.create(community_id=self.community_id, name=name, body=body,
                                                      language_id=37)):
            logging.warning("Failed to create post, will retry again in 2 seconds")
            time.sleep(2)
        post_id = response["post_view"]["post"]["id"]
        logging.info(f"CREATED Post ID {post_id}")

        while not self.lemmy.post.save(post_id, True):
            logging.warning("Failed to save post, will retry again in 2 seconds")
            time.sleep(2)
        logging.info(f"SAVED Post ID {post_id}, good to go!")
        return post_id

    def update_live_threads(self, live_games, lemmy_games):
        for live_game in live_games:
            post_id = None
            for lemmy_game in lemmy_games:
                lemmy_game_id = PostUtils.get_post_id(lemmy_game)
                if live_game["gameId"] == lemmy_game_id:
                    post_id = lemmy_game["post"]["id"]
            if not post_id:
                logging.warning(f"Found a LIVE game without a thread, will create it for {PostUtils.game_info(live_game)}")
                post_id = self.create_new_game_thread(live_game)
            logging.info(f"UPDATE Post for {PostUtils.game_info(live_game)}")
            bs = summerboxscore.SummerBoxScore(
                game_id=live_game["gameId"]) if self.is_summer_league else boxscore.BoxScore(
                game_id=live_game["gameId"])
            self.update_game_thread(bs.get_dict()['game'], live_game, post_id, False)

    def update_game_thread(self, bs, live_game, post_id, final):
        name = MarkupUtils.get_thread_title(live_game) + " [FINAL]" if final else None
        body = MarkupUtils.get_game_body(bs, live_game)
        while not self.lemmy.post.edit(post_id=post_id, body=body, name=name):
            logging.warning("Failed to update post, will retry again in 2 seconds")
            time.sleep(2)

    def close_finished_games(self, finished_games, lemmy_games):
        for game in finished_games:
            post_id = None
            for lemmy_game in lemmy_games:
                lemmy_game_id = PostUtils.get_post_id(lemmy_game)
                if game["gameId"] == lemmy_game_id:
                    post_id = lemmy_game["post"]["id"]
            if post_id:
                bs = summerboxscore.SummerBoxScore(
                    game_id=game["gameId"]) if self.is_summer_league else boxscore.BoxScore(game_id=game["gameId"])
                self.close_game(bs.get_dict()['game'], game, post_id)

    def close_game(self, game, post_id, bs=None):
        if bs:
            logging.info(f"FINAL UPDATE - for Post ID {post_id} ")
            self.update_game_thread(bs, game, post_id, True)
        logging.info(f"CLOSE Post ID {post_id} ")
        while not self.lemmy.post.save(post_id, False):
            logging.warning("Failed to un-save post, will retry again in 2 seconds")
            time.sleep(2)
        self.create_pgt(bs, game)

    def create_pgt(self, box_score, live_game):
        logging.info(f"CREATE New Post Game Thread: {live_game}")
        name = MarkupUtils.get_pgt_title(live_game)
        body = MarkupUtils.get_game_body(box_score, live_game)
        while not self.lemmy.post.create(community_id=self.community_id, name=name, body=body, language_id=37):
            logging.warning("Failed to create PGT, will retry again in 2 seconds")
            time.sleep(2)
        logging.info(f"CREATED new Post Game Thread for {PostUtils.game_info(live_game)}")


def get_upcoming_games(games):
    upcoming_games = []
    for game in games:
        gameutc = parser.parse(game['gameTimeUTC']).astimezone(pytz.UTC)
        time_to_game = (datetime.now(pytz.utc) - gameutc).seconds
        if 0 < time_to_game < 30 * 60 and game["gameStatus"] == 1:
            logging.debug(f"game is upcoming {game}")
            upcoming_games.append(game)
    return upcoming_games


def get_orphan_posts(games, lemmy_posts):
    orphan_posts = []
    for post in lemmy_posts:
        post_game_id = PostUtils.get_post_id(post)
        found_games = [game for game in games if game["gameId"] == post_game_id]
        if len(found_games) == 0:
            orphan_posts.append(post)
    return orphan_posts