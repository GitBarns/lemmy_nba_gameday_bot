import logging
from datetime import datetime

import pytz
from dateutil import parser
from nba_api.live.nba.endpoints import scoreboard, boxscore
from pythorhead import Lemmy
from pythorhead.types import ListingType

from .summerleague import summerscoreboard, summerboxscore
from .utils import PostUtils, MarkupUtils


class NBAGamePostMaker:

    def __init__(self, api_base_url, user_name, password, community_name, is_summer_league, admin_id):
        self.admin_id = admin_id
        self.community_name = community_name
        self.password = password
        self.user_name = user_name
        self.community_id = None
        self.is_summer_league = is_summer_league
        self.lemmy = Lemmy(api_base_url)

    def log_in(self):
        PostUtils.safe_api_call(self.lemmy.log_in, username_or_email=self.user_name, password=self.password)

        community = PostUtils.safe_api_call(self.lemmy.community.get, name=self.community_name)
        self.community_id = community["community_view"]["community"]["id"]
        logging.debug(f"community is {self.community_id}:{community}")

        return True

    def process_posts(self):
        try:
            self.process_posts_inner()
        except Exception:
            logging.exception("Failed to process match threads")
            try:
                self.lemmy.private_message.create(content="Failed to process game posts, go check logs",
                                                  recipient_id=self.admin_id)
            except Exception:
                logging.exception("Failed to send a DM, oh well...")

    def process_posts_inner(self):
        lemmy_posts = PostUtils.safe_api_call(self.lemmy.post.list, community_id=self.community_id, saved_only="true",
                                              type_=ListingType.Subscribed)
        lemmy_posts = [post['post'] for post in lemmy_posts if not post["post"]["deleted"]]
        [logging.info(f"Found a game post in {self.community_name} : {post['name']}") for post in lemmy_posts]

        # Today's Score Board
        scorebox_games = summerscoreboard.SummerScoreBoard().games.get_dict() if self.is_summer_league else scoreboard.ScoreBoard().games.get_dict()
        [logging.info(f"Found a game in today's scorebox: {PostUtils.game_info(game)}") for game in scorebox_games]

        upcoming_games = self.get_upcoming_games(scorebox_games)
        [logging.info(f"Found an  upcoming game: {PostUtils.game_info(game)}") for game in upcoming_games]
        self.create_new_game_posts(upcoming_games, lemmy_posts)

        live_games = [game for game in scorebox_games if game["gameStatus"] == 2]
        [logging.info(f"Found a live game: {PostUtils.game_info(game)}") for game in live_games]
        self.update_live_threads(live_games, lemmy_posts)

        finished_games = [game for game in scorebox_games if game["gameStatus"] == 3]
        [logging.info(f"Found a finished game: {PostUtils.game_info(game)}") for game in finished_games]
        self.close_finished_games(finished_games, lemmy_posts)

        self.close_orphan_posts(scorebox_games, lemmy_posts)

    def get_upcoming_games(self, games):
        upcoming_games = []
        for game in games:
            gameutc = parser.parse(game['gameTimeUTC']).astimezone(pytz.UTC)
            time_to_game = (datetime.now(pytz.utc) - gameutc).seconds
            if 0 < time_to_game < 30 * 60 and game["gameStatus"] == 1:
                logging.debug(f"game is upcoming {game}")
                upcoming_games.append(game)
        return upcoming_games

    def create_new_game_posts(self, upcoming_games, lemmy_posts):
        for upcoming_game in upcoming_games:
            post_id = None
            for gamepost in lemmy_posts:
                lemmy_game_id = PostUtils.get_post_game_id(gamepost)
                if upcoming_game["gameId"] == lemmy_game_id:
                    post_id = gamepost["id"]
            if not post_id:
                self.create_new_game_thread(upcoming_game)

    def create_new_game_thread(self, game):
        logging.info(f"CREATE a new game post: {PostUtils.game_info(game)}")
        name = MarkupUtils.get_thread_title(game, False, self.is_summer_league)
        body = MarkupUtils.get_live_game_body(game)
        response = PostUtils.safe_api_call(self.lemmy.post.create, community_id=self.community_id, name=name, body=body,
                                           language_id=37)
        post_id = response["post_view"]["post"]["id"]
        logging.info(f"CREATED Post ID {post_id}")

        PostUtils.safe_api_call(self.lemmy.post.save, post_id=post_id, saved=True)
        logging.info(f"SAVED Post ID {post_id}, good to go!")
        return post_id

    def update_live_threads(self, live_games, lemmy_games):
        for live_game in live_games:
            post_id = None
            for lemmy_game in lemmy_games:
                lemmy_game_id = PostUtils.get_post_game_id(lemmy_game)
                if live_game["gameId"] == lemmy_game_id:
                    post_id = lemmy_game["post"]["id"]
            if not post_id:
                logging.warning(f"Found a LIVE game without a thread, will create: {PostUtils.game_info(live_game)}")
                post_id = self.create_new_game_thread(live_game)
            logging.info(f"UPDATE Post for {PostUtils.game_info(live_game)}")
            self.update_game_thread(live_game, post_id, False)

    def update_game_thread(self, live_game, post_id, final):
        name = MarkupUtils.get_thread_title(live_game, final, self.is_summer_league)
        body = MarkupUtils.get_live_game_body(live_game)
        PostUtils.safe_api_call(self.lemmy.post.edit, post_id=post_id, body=body, name=name)

    def close_finished_games(self, finished_games, lemmy_games):
        for game in finished_games:
            for lemmy_game in lemmy_games:
                if game["gameId"] == PostUtils.get_post_game_id(lemmy_game):
                    self.close_game(game['gameId'], game)

    def close_game(self, post_id, game):
        logging.info(f"FINAL UPDATE - for Post ID {post_id} ")
        self.update_game_thread(game, post_id, True)
        logging.info(f"CLOSE Post ID {post_id} ")
        PostUtils.safe_api_call(self.lemmy.post.save, post_id=post_id, saved=False)
        self.create_pgt(game)

    def create_pgt(self, game):
        logging.info(f"CREATE New Post Game Thread: {PostUtils.game_info(game)}")
        box_score = summerboxscore.SummerBoxScore(
            game_id=game["gameId"]) if self.is_summer_league else boxscore.BoxScore(game_id=game["gameId"])
        name = MarkupUtils.get_pgt_title(game)
        body = MarkupUtils.get_game_body(box_score.get_dict()['game'], game)
        PostUtils.safe_api_call(self.lemmy.post.create, community_id=self.community_id, name=name, body=body, language_id=37)
        logging.info(f"CREATED new Post Game Thread for {PostUtils.game_info(game)}")

    def close_orphan_posts(self, games, lemmy_posts):
        for post in lemmy_posts:
            post_game_id = PostUtils.get_post_game_id(post)
            found_games = [game for game in games if game["gameId"] == post_game_id]
            if len(found_games) == 0:
                logging.warning(f"Found an ORPHAN post, will close it - {post['id']}:{post['name']}")
                PostUtils.safe_api_call(self.lemmy.post.edit, post_id=post['id'], name=post['name'] + " [CLOSED]")
                PostUtils.safe_api_call(self.lemmy.post.save, post_id=post['id'], saved=False)
