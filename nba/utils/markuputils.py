import logging
import random
import re
from datetime import datetime

import pytz
from dateutil import parser


class MarkupUtils:
    @staticmethod
    def get_game_body(box_score, live_game):
        body = MarkupUtils.get_match_summary(live_game)
        body = f"{body}\n{MarkupUtils.get_game_quarter_summary(box_score, live_game)}"
        body = f"{body}\n---"
        body = f"{body}\n{MarkupUtils.get_single_team_body('homeTeam', box_score, live_game)}"
        body = f"{body}\n---"
        body = f"{body}\n{MarkupUtils.get_single_team_body('awayTeam', box_score, live_game)}"
        body = f"{body}\n---"
        body = f"{body}\n{MarkupUtils.get_footer(box_score['gameId'])}"
        return body

    @staticmethod
    def get_match_summary(live_game):
        game_time = parser.parse(timestr=live_game["gameTimeUTC"]).astimezone(pytz.timezone('US/Eastern'))
        body = f"|Match Summary|\n|:-:|"
        body = f"{body}\n|{game_time.strftime('%a, %b %-d, %H:%M EST')}|"
        body = f"{body}\n|{live_game['homeTeam']['teamName']} {live_game['homeTeam']['score']} : {live_game['awayTeam']['teamName']} {live_game['awayTeam']['score']}|"
        body = f"{body}\n|{live_game['gameStatusText']}|\n"
        return body

    @staticmethod
    def get_footer(game_id):
        footer = f"^{datetime.now().strftime('%d-%m-%Y %H:%M:%S')} game id:{game_id}^"
        footer = f"::: spoiler bot info \n{footer.replace(':', chr(92) + ':').replace(' ', chr(92) + ' ')}\n:::"
        return footer

    @staticmethod
    def get_game_quarter_summary(box_score, live_game):
        title = "| TEAM | Q1 | Q2 | Q3 | Q4 | "
        low_title = "| :--- | :---: | :---: | :---: | :---: | "
        home_team = f"| **{box_score['homeTeam']['teamCity']} {box_score['homeTeam']['teamName']}** | {box_score['homeTeam']['periods'][0]['score']} | {box_score['homeTeam']['periods'][1]['score']} | {box_score['homeTeam']['periods'][2]['score']} | {box_score['homeTeam']['periods'][3]['score']} |"
        away_team = f"| **{box_score['awayTeam']['teamCity']} {box_score['awayTeam']['teamName']}** | {box_score['awayTeam']['periods'][0]['score']} | {box_score['awayTeam']['periods'][1]['score']} | {box_score['awayTeam']['periods'][2]['score']} | {box_score['awayTeam']['periods'][3]['score']} | "
        if len(live_game['homeTeam']['periods']) > 4:
            for ot in range(4, len(live_game['homeTeam']['periods'])):
                title = f"{title}OT{ot - 4} | "
                low_title = f"{low_title}:---: | "
                home_team = f"{home_team}{box_score['homeTeam']['periods'][ot]['score']} | "
                away_team = f"{away_team}{box_score['awayTeam']['periods'][ot]['score']} | "
        if live_game["gameStatus"] == 3:
            title = f"{title}FINAL | "
            low_title = f"{low_title}:---: | "
            home_team = f"{home_team}**{live_game['homeTeam']['score']}** | "
            away_team = f"{away_team}**{live_game['awayTeam']['score']}** | "
        body = f"\n---\n{title}\n{low_title}\n{home_team}\n{away_team}\n"
        return body

    @staticmethod
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

    @staticmethod
    def get_thread_title(game):
        name = f"GAME THREAD: {game['awayTeam']['teamCity']} {game['awayTeam']['teamName']} ({game['awayTeam']['wins']}:{game['awayTeam']['losses']})"
        name = f"{name} @ {game['homeTeam']['teamCity']} {game['homeTeam']['teamName']} ({game['homeTeam']['wins']}:{game['homeTeam']['losses']})"
        logging.info("SET Post Title: " + name)
        return name

    @staticmethod
    def get_pgt_title(game):
        verb = random.choice(['defeat', 'win over', 'overcome', 'beat'])
        winner = (game['homeTeam'] if game['homeTeam']['score'] > game['awayTeam']['score'] else game['awayTeam'])
        loser = (game['homeTeam'] if game['homeTeam']['score'] < game['awayTeam']['score'] else game['awayTeam'])
        name = f"POST GAME THREAD: The {winner['teamCity']} {winner['teamName']} {verb} the {loser['teamCity']} {loser['teamName']}, {winner['score']}-{loser['score']}"
        logging.info(f"SET Post Game Thread Title: {name}")
        return name