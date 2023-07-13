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
            time_to_game = (datetime.now(pytz.utc) - gameutc).seconds
            if 0 < time_to_game < 15 * 60:
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
    def get_game_score(live_game):
        return f"{live_game['homeTeam']['score']} : {live_game['awayTeam']['score']}"
