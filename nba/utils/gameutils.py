import logging
import re
from datetime import datetime

import pytz
from dateutil import parser


class GameUtils:
    NOT_STARTED = "Not Started"
    STARTING_SOON = "Starting Soon"

    @staticmethod
    def get_game_time_est(game):
        game_time = parser.parse(timestr=game["gameTimeUTC"]).astimezone(pytz.timezone('US/Eastern'))
        return game_time.strftime('%H:%M EST')

    @staticmethod
    def get_game_datetime_est(game):
        game_time = parser.parse(timestr=game["gameTimeUTC"]).astimezone(pytz.timezone('US/Eastern'))
        return game_time.strftime('%a, %b %-d, %H:%M EST')

    @staticmethod
    def get_game_status(game):
        if game['gameStatus'] == 1:
            gameutc = parser.parse(game['gameTimeUTC']).astimezone(pytz.UTC)
            time_to_game = (gameutc - datetime.now(pytz.utc)).total_seconds()
            logging.info(
                f"Upcoming game starts at {gameutc}, its now {datetime.now(pytz.utc)}, seconds diff :{time_to_game}")
            if time_to_game < 15 * 60:
                return GameUtils.STARTING_SOON
            else:
                return GameUtils.NOT_STARTED
        if game['gameStatus'] == 2:
            quarter = f"Q{game['period']}" if game['period'] <= 4 else f"OT{game['period'] - 4}"
            mins = re.split('PT(\d+)M(\d*)(.?\d*)', game['gameClock'])
            return f"{quarter} {mins[1]}:{mins[2]}"
        if game['gameStatus'] == 3:
            return game['gameStatusText']

    @staticmethod
    def get_home_team(game):
        return f"{game['homeTeam']['teamCity']} {game['homeTeam']['teamName']}"

    @staticmethod
    def get_away_team(game):
        return f"{game['awayTeam']['teamCity']} {game['awayTeam']['teamName']}"

    @staticmethod
    def get_game_score(game):
        return f"{game['homeTeam']['score']} : {game['awayTeam']['score']}"
