import logging
import random
import re
from datetime import datetime

import pytz
import time
from dateutil import parser
from pythorhead import Lemmy

from nba.summerleague import SummerScoreBoard, SummerBoxScore


class NBAMatchThreadMaker:
    lemmy: Lemmy = None
    lfs = None

    def __init__(self, api_base_url):
        self.community_id = None
        self.lemmy = Lemmy(api_base_url)

    def log_in(self, user_name, password, community_name):
        if not self.lemmy.log_in(user_name, password):
            return False

        if not (community := self.lemmy.community.get(name=community_name)):
            logging.error(f"Failed to fine Community {community_name}")
            return False
        else:
            self.community_id = community["community_view"]["community"]["id"]
            logging.debug(f"community is {self.community_id}:{community}")
        return True

    def create_or_update_threads(self):
        lemmy_gameposts = self.lemmy.post.list(community_id=self.community_id, saved_only="true")
        lemmy_gameposts = [gamepost for gamepost in lemmy_gameposts if not gamepost["post"]["deleted"]]

        # Today's Score Board
        scorebox_games = SummerScoreBoard.SummerScoreBoard().games.get_dict()
        [logging.debug(f"found game: {game}") for game in scorebox_games]

        upcoming_games = get_upcoming_games(scorebox_games)
        [logging.debug(f"found upcoming game: {game}") for game in upcoming_games]
        self.create_new_game_posts(upcoming_games, lemmy_gameposts)

        live_games = get_live_games(scorebox_games)
        [logging.debug(f"found live game: {live_game}") for live_game in live_games]
        self.update_live_threads(live_games, lemmy_gameposts)

        finished_games = get_finished_games(scorebox_games)
        [logging.debug(f"found finished game: {live_game}") for live_game in live_games]
        self.close_finished_games(finished_games, lemmy_gameposts)

        orphan_posts = get_orphan_posts(scorebox_games, lemmy_gameposts)
        [self.close_game(game=post, post_id=post["post"]["id"]) for post in orphan_posts]

    def create_new_game_posts(self, upcoming_games, lemmygameposts):
        for upcoming_game in upcoming_games:
            post_id = None
            for gamepost in lemmygameposts:
                lemmy_game_id = get_post_id(gamepost)
                if upcoming_game["gameId"] == lemmy_game_id:
                    post_id = gamepost["post"]["id"]
            if not post_id:
                self.create_new_game_thread(upcoming_game)

    def create_new_game_thread(self, game):
        logging.info(f"CREATE a new game post: {game}")
        name = get_thread_title(game)
        body = f"{get_match_summary(game)}\n {get_footer(game['gameId'])}"
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
                lemmy_game_id = get_post_id(lemmy_game)
                if live_game["gameId"] == lemmy_game_id:
                    post_id = lemmy_game["post"]["id"]
            if not post_id:
                logging.warning(f"Found a LIVE game without a thread, will create it for {live_game}")
                post_id = self.create_new_game_thread(live_game)
            logging.info(f"UPDATE Post for {live_game}")
            bs = SummerBoxScore.BoxScore(game_id=live_game["gameId"]).get_dict()['game']
            self.update_game_thread(bs, live_game, post_id, False)

    def update_game_thread(self, bs, live_game, post_id, final):
        name = get_thread_title(live_game) + " [FINAL]" if final else None
        body = get_game_body(bs, live_game)
        while not self.lemmy.post.edit(post_id=post_id, body=body, name=name):
            logging.warning("Failed to update post, will retry again in 2 seconds")
            time.sleep(2)

    def close_finished_games(self, finished_games, lemmy_games):
        for game in finished_games:
            post_id = None
            for lemmy_game in lemmy_games:
                lemmy_game_id = get_post_id(lemmy_game)
                if game["gameId"] == lemmy_game_id:
                    post_id = lemmy_game["post"]["id"]
            if post_id:
                bs = SummerBoxScore.BoxScore(game_id=game['gameId']).get_dict()['game']
                self.close_game(bs, game, post_id)

    def close_game(self, game, post_id, bs=None):
        if bs:
            logging.info(f"FINAL UPDATE - for Post ID {post_id} ")
            self.update_game_thread(bs, game, post_id, True)
        logging.info(f"CLOSE Post ID {post_id} ")
        while not self.lemmy.post.save(post_id, False):
            logging.warning("Failed to un-save post, will retry again in 2 seconds")
            time.sleep(2)
        self.create_PGT(bs, game)

    def create_PGT(self, boxscore, livegame):
        logging.info(f"CREATE New Post Game Thread: {livegame}")
        name = get_PGT_title(livegame)
        body = get_game_body(boxscore, livegame)
        while not self.lemmy.post.create(community_id=self.community_id, name=name, body=body, language_id=37):
            logging.warning("Failed to create PGT, will retry again in 2 seconds")
            time.sleep(2)
        logging.info(f"CREATED new Post Game Thread for {livegame}")


def get_live_games(games):
    return [game for game in games if game["gameStatus"] == 2]


def get_finished_games(games):
    return [game for game in games if game["gameStatus"] == 3]


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
        post_game_id = get_post_id(post)
        found_games = [game for game in games if game["gameId"] == post_game_id]
        if len(found_games) == 0:
            orphan_posts.append(post)
    return orphan_posts


def get_game_body(boxscore, live_game):
    body = get_match_summary(live_game)
    body = f"{body}\n{get_game_querter_summary(boxscore, live_game)}"
    body = f"{body}\n---"
    body = f"{body}\n{get_single_team_body('homeTeam', boxscore, live_game)}"
    body = f"{body}\n---"
    body = f"{body}\n{get_single_team_body('awayTeam', boxscore, live_game)}"
    body = f"{body}\n---"
    body = f"{body}\n{get_footer(boxscore['gameId'])}"
    return body


def get_match_summary(live_game):
    game_time = parser.parse(live_game["gameTimeUTC"]).astimezone(pytz.timezone('US/Eastern'))
    body = f"|Match Summary|\n|:-:|"
    body = f"{body}\n|{game_time.strftime('%a, %b %-d, %H:%M EST')}|"
    body = f"{body}\n|{live_game['homeTeam']['teamName']} {live_game['homeTeam']['score']} : {live_game['awayTeam']['teamName']} {live_game['awayTeam']['score']}|"
    body = f"{body}\n|{live_game['gameStatusText']}|\n"
    return body


def get_footer(game_id):
    footer = f"^{datetime.now().strftime('%d-%m-%Y %H:%M:%S')} game id:{game_id}^"
    footer = f"::: spoiler bot info \n{footer.replace(':', chr(92) + ':').replace(' ', chr(92) + ' ')}\n:::"
    return footer


def get_game_querter_summary(boxscore, live_game):
    title = "| TEAM | Q1 | Q2 | Q3 | Q4 | "
    low_title = "| :--- | :---: | :---: | :---: | :---: | "
    home_team = f"| **{boxscore['homeTeam']['teamCity']} {boxscore['homeTeam']['teamName']}** | {boxscore['homeTeam']['periods'][0]['score']} | {boxscore['homeTeam']['periods'][1]['score']} | {boxscore['homeTeam']['periods'][2]['score']} | {boxscore['homeTeam']['periods'][3]['score']} |"
    away_team = f"| **{boxscore['awayTeam']['teamCity']} {boxscore['awayTeam']['teamName']}** | {boxscore['awayTeam']['periods'][0]['score']} | {boxscore['awayTeam']['periods'][1]['score']} | {boxscore['awayTeam']['periods'][2]['score']} | {boxscore['awayTeam']['periods'][3]['score']} | "
    if len(live_game['homeTeam']['periods']) > 4:
        for ot in range(4, len(live_game['homeTeam']['periods'])):
            title = f"{title}OT{ot - 4} | "
            low_title = f"{low_title}:---: | "
            home_team = f"{home_team}{boxscore['homeTeam']['periods'][ot]['score']} | "
            away_team = f"{away_team}{boxscore['away_team']['periods'][ot]['score']} | "
    if live_game["gameStatus"] == 3:
        title = f"{title}FINAL | "
        low_title = f"{low_title}:---: | "
        home_team = f"{home_team}**{live_game['homeTeam']['score']}** | "
        away_team = f"{away_team}**{live_game['awayTeam']['score']}** | "
    body = f"\n---\n{title}\n{low_title}\n{home_team}\n{away_team}\n"
    return body


def get_single_team_body(home_away, game, live_game):
    body = f"\n**{game[home_away]['teamCity']} {game[home_away]['teamName']} ({live_game[home_away]['wins']}:{live_game[home_away]['losses']})**"
    body = f"{body}\n| PLAYER | MIN | FG | FT | 3PT | REB | AST | STL | BLK | TO | PTS | +/- |"
    body = f"{body}\n| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    for player in game[home_away]['players']:
        body = f"{body}\n| {player['name']}"
        if player['starter'] == "1":
            body = f"{body}^{player['position']}^"
        pstats = player['statistics']
        mins = re.split('PT(\d+)M(\d*)(.?\d*)', str(pstats['minutes']))
        playtime = f"{mins[1]}:{mins[2]}"
        body = f"{body} | {playtime} |  {pstats['fieldGoalsMade']}:{pstats['fieldGoalsAttempted']} | " \
               f"{pstats['freeThrowsMade']}:{pstats['freeThrowsAttempted']} | {pstats['threePointersMade']}:{pstats['threePointersAttempted']} | {pstats['reboundsTotal']} | " \
               f"{pstats['assists']} | {pstats['steals']} | {pstats['blocks']} | {pstats['steals']} | {pstats['points']} | {int(pstats['plusMinusPoints'])} |"
    pstats = game[home_away]['statistics']
    body = f"{body}\n|**TOTAL**| - | **{pstats['fieldGoalsMade']}:{pstats['fieldGoalsAttempted']}** | **" \
           f"{pstats['freeThrowsMade']}:{pstats['freeThrowsAttempted']}** | **{pstats['threePointersMade']}:{pstats['threePointersAttempted']}** | **{pstats['reboundsTotal']}** | **" \
           f"{pstats['assists']}** | **{pstats['steals']}** | **{pstats['blocks']}** | **{pstats['steals']}** | **{pstats['points']}** | - |"
    return body


def get_thread_title(game):
    name = f"GAME THREAD: {game['awayTeam']['teamCity']} {game['awayTeam']['teamName']} ({game['awayTeam']['wins']}:{game['awayTeam']['losses']})"
    name = f"{name} @ {game['homeTeam']['teamCity']} {game['homeTeam']['teamName']} ({game['homeTeam']['wins']}:{game['homeTeam']['losses']})"
    logging.info("SET Post Title: " + name)
    return name


def get_PGT_title(game):
    verb = random.choice(['defeat', 'win over', 'overcome', 'beat'])
    winner = (game['homeTeam'] if game['homeTeam']['score'] > game['awayTeam']['score'] else game['awayTeam'])
    loser = (game['homeTeam'] if game['homeTeam']['score'] < game['awayTeam']['score'] else game['awayTeam'])
    name = f"POST GAME THREAD: The {winner['teamCity']} {winner['teamName']} {verb} the {loser['teamCity']} {loser['teamName']}, {winner['score']}-{loser['score']}"
    logging.info(f"SET Post Game Thread Title: {name}")
    return name


def get_post_id(gamepost):
    return gamepost["post"]["body"][-15:-5]
