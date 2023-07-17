import logging

from nba_api.live.nba.endpoints import scoreboard, boxscore
from pythorhead import Lemmy
from pythorhead.types import ListingType

from . import DailyIndexMaker
from .summerleague import summerscoreboard, summerboxscore
from .utils import PostUtils, MarkupUtils, GameUtils


class GameThreadMaker:
    sent_pm_already: bool = False

    def __init__(self, api_base_url, user_name, password, community_name, team_name, is_summer_league, admin_id):
        self.team = None
        self.lemmy = None
        self.community_id = None
        self.team_name = team_name
        self.api_base_url = api_base_url
        self.admin_id = admin_id
        self.community_name = community_name
        self.password = password
        self.user_name = user_name
        self.is_summer_league = is_summer_league

    def log_in(self):
        self.lemmy = Lemmy(self.api_base_url)

        if self.lemmy.nodeinfo is None:
            raise RuntimeError(f"Failed to connect to Lemmy instance {self.api_base_url}, leaving...")

        if not PostUtils.safe_api_call(self.lemmy.log_in, username_or_email=self.user_name, password=self.password):
            raise RuntimeError("Failed to log into the Lemmy instance, please verify your bot credentials")

        community = PostUtils.safe_api_call(self.lemmy.community.get, name=self.community_name)
        if len(community) == 0:
            raise RuntimeError(f"Failed to find community named {self.community_name}")
        self.community_id = community["community_view"]["community"]["id"]
        logging.info(f"Lemmy Community found - {self.community_name} ({self.community_id})")

        if self.team_name:
            self.team = GameUtils.get_team_by_name(self.team_name)
            if self.team is None:
                raise RuntimeError(f"Failed to find team by name {self.team_name}")
            logging.info(f"NBA Team found - {self.team['full_name']} ({self.team['id']})")
        else:
            logging.info(f"No team specified, will process ALL teams")

    def run(self):
        try:
            self.process_game_threads()
            if not self.team:
                logging.info("Will process Daily Index Thread")
                DailyIndexMaker.run(self.lemmy, community_id=self.community_id, is_summer_league=self.is_summer_league)
        except Exception:
            logging.exception("Failed to run")
            if not GameThreadMaker.sent_pm_already:
                self.lemmy.private_message.create(content="Failed to process game posts, go check logs",
                                                  recipient_id=int(self.admin_id))
                GameThreadMaker.sent_pm_already = True

    def process_game_threads(self):
        # Current active game posts
        active_lemmy_game_threads = self.get_lemmy_game_threads()
        # Today's Score Board
        scorebox_games = self.get_todays_scoreboard()

        upcoming_games = [game for game in scorebox_games if GameUtils.get_game_status(game) == GameUtils.STARTING_SOON]
        [logging.info(f"Found an upcoming game: {PostUtils.game_info(game)}") for game in upcoming_games]
        self.create_upcoming_game_threads(upcoming_games, active_lemmy_game_threads)

        live_games = [game for game in scorebox_games if game["gameStatus"] == 2]
        [logging.info(f"Found a live game: {PostUtils.game_info(game)}") for game in live_games]
        self.update_live_threads(live_games, active_lemmy_game_threads)

        # Get all finished games, compare them to current ongoing game threads (upcoming + playing)
        # if the same game is in both groups - close the game thread  with a final update and open a post game thread with detailed stats
        finished_games = [game for game in scorebox_games if game["gameStatus"] == 3]
        [logging.info(f"Found a finished game: {PostUtils.game_info(game)}") for game in finished_games]
        self.close_finished_games(finished_games, active_lemmy_game_threads)

        # go through all active lemmy game threads and find them in today's scorebox
        # if any aren't found in the scorebox for some reason (day switch?) - close them just in case
        self.close_orphan_posts(scorebox_games, active_lemmy_game_threads)

    def get_todays_scoreboard(self):
        board = summerscoreboard.SummerScoreBoard() if self.is_summer_league else scoreboard.ScoreBoard()
        sb_games = board.games.get_dict()
        if self.team:
            sb_games = [sb for sb in sb_games if
                        self.team['id'] in (sb['awayTeam']['teamId'], sb['homeTeam']['teamId'])]
        [logging.info(f"Found a game in today's scorebox: {PostUtils.game_info(game)}") for game in sb_games]
        return sb_games

    def get_lemmy_game_threads(self):
        # get all posts by the bot that are saved (i.e. active)
        lemmy_posts = PostUtils.get_last50_posts(self.lemmy, community_id=self.community_id, saved_only=True,
                                                 type_=ListingType.Subscribed)
        # filter out ones that aren't GT or PGT
        lemmy_posts = [post for post in lemmy_posts if str(post['name']).startswith(PostUtils.GAME_THREAD_PREFIX)]
        [logging.info(f"Found a game post in {self.community_name} : {post['name']}") for post in lemmy_posts]
        return lemmy_posts

    def create_upcoming_game_threads(self, upcoming_games, lemmy_posts):
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
        response = PostUtils.safe_api_call(self.lemmy.post.create, community_id=self.community_id, name=name, body=body)
        post_id = int(response["post_view"]["post"]["id"])
        logging.info(f"CREATED Post ID {post_id}")

        PostUtils.safe_api_call(self.lemmy.post.save, post_id=post_id, saved=True)
        logging.info(f"SAVED Post ID {post_id}, good to go!")
        return post_id

    def update_live_threads(self, live_games, lemmy_posts):
        for live_game in live_games:
            post_id = None
            for post in lemmy_posts:
                lemmy_game_id = PostUtils.get_post_game_id(post)
                if live_game["gameId"] == lemmy_game_id:
                    post_id = post["id"]
            if not post_id:
                logging.warning(f"Found a LIVE game without a thread, will create: {PostUtils.game_info(live_game)}")
                post_id = self.create_new_game_thread(live_game)
            logging.info(f"UPDATE Post for {PostUtils.game_info(live_game)}")
            self.update_game_thread(live_game, post_id, False)

    def update_game_thread(self, live_game, post_id, final):
        name = MarkupUtils.get_thread_title(live_game, final, self.is_summer_league)
        body = MarkupUtils.get_live_game_body(live_game)
        PostUtils.safe_api_call(self.lemmy.post.edit, post_id=int(post_id), body=body, name=name)

    def close_finished_games(self, finished_games, lemmy_posts):
        for game in finished_games:
            for post in lemmy_posts:
                if game["gameId"] == PostUtils.get_post_game_id(post):
                    logging.info(f"FINAL UPDATE - for Post ID {post['id']} - {PostUtils.game_info(game)}")
                    self.update_game_thread(game, post['id'], True)
                    logging.info(f"CLOSE Post ID {post['id']} - {PostUtils.game_info(game)} ")
                    PostUtils.safe_api_call(self.lemmy.post.save, post_id=post['id'], saved=False)
                    logging.info(f"UN-SAVED Post ID {post['id']} - {PostUtils.game_info(game)} ")
                    self.create_pgt(game)

    def create_pgt(self, game):
        logging.info(f"CREATE New Post Game Thread: {PostUtils.game_info(game)}")
        box_score = summerboxscore.SummerBoxScore(
            game_id=game["gameId"]) if self.is_summer_league else boxscore.BoxScore(game_id=game["gameId"])
        name = MarkupUtils.get_pgt_title(game)
        body = MarkupUtils.get_game_body(box_score.get_dict()['game'], game)
        PostUtils.safe_api_call(self.lemmy.post.create, community_id=self.community_id, name=name, body=body)
        logging.info(f"CREATED new Post Game Thread for {PostUtils.game_info(game)}")

    def close_orphan_posts(self, games, lemmy_posts):
        for post in lemmy_posts:
            post_game_id = PostUtils.get_post_game_id(post)
            found_games = [game for game in games if game["gameId"] == post_game_id]
            if len(found_games) == 0:
                logging.warning(f"Found an ORPHAN post, will close it - {post['id']}:{post['name']}")
                PostUtils.safe_api_call(self.lemmy.post.edit, post_id=post['id'], name=post['name'] + " [CLOSED]")
                PostUtils.safe_api_call(self.lemmy.post.save, post_id=post['id'], saved=False)
