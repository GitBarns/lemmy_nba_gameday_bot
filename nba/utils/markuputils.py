import logging
import random
import re
from datetime import datetime

from nba.utils import GameUtils, TemplateUtils


class MarkupUtils:
    FOOTER = "templates/footer.txt"
    MATCH_SUMMARY_FILE = "templates/match_summary.txt"

    @staticmethod
    def get_live_game_body(live_game):
        body = MarkupUtils.get_match_summary(live_game)
        body = f"{body}\n{MarkupUtils.get_game_quarter_summary(live_game)}"
        body = f"{body}\n---"
        body = f"{body}\n{MarkupUtils.get_footer(live_game['gameId'])}"
        return body

    @staticmethod
    def get_game_body(box_score, live_game):
        body = MarkupUtils.get_match_summary(live_game)
        body = f"{body}\n{MarkupUtils.get_game_quarter_summary(live_game)}"
        body = f"{body}\n---"
        body = f"{body}\n{MarkupUtils.get_single_team_body('homeTeam', box_score, live_game)}"
        body = f"{body}\n---"
        body = f"{body}\n{MarkupUtils.get_single_team_body('awayTeam', box_score, live_game)}"
        body = f"{body}\n---"
        body = f"{body}\n{MarkupUtils.get_footer(box_score['gameId'])}"
        return body

    @staticmethod
    def get_match_summary(live_game):
        return TemplateUtils.format(
            MarkupUtils.MATCH_SUMMARY_FILE,
            {
                'updated': ("`   (updated once a minute) `" if live_game['gameStatus'] == 2 else ""),
                'game_time': GameUtils.get_game_datetime_est(live_game),
                'score': GameUtils.get_game_score(live_game),
                'status': GameUtils.get_game_status(live_game)
            }
        )
        # body = f"|Match Summary "
        # if live_game['gameStatus'] == 2:
        #     body = f"{body}`   (updated once a minute)`"
        # body = f"{body}|\n|:-:|"
        # body = f"{body}\n|{GameUtils.get_game_datetime_est(live_game)}|"
        # body = f"{body}\n|{GameUtils.get_game_score(live_game)}|\n"
        # body = f"{body}|{GameUtils.get_game_status(live_game)}|\n"
        # return body

    @staticmethod
    def get_footer(game_id):
        return TemplateUtils.format(
            MarkupUtils.FOOTER,
            {
                'footer_time': datetime.now().strftime('%d-%m-%Y %H-%M-%S'),
                'game_id': game_id
            })
        # footer = f"^{datetime.now().strftime('%d-%m-%Y %H:%M:%S')} game id:{game_id}^"
        # footer = f"::: spoiler bot info \n{footer.replace(':', chr(92) + ':').replace(' ', chr(92) + ' ')}\n:::"
        # footer = "This post was created by your friendly [NBA Bot](https://lemmy.world/u/MatchThreadBot). " \
        #          "Did I make a mistake? Have a suggestion? [PM me here](https://lemmy.world/create_private_message/98250)\n" \
        #          f"{footer}"
        # return footer

    @staticmethod
    def get_game_quarter_summary(game):
        title = "| | Q1 | Q2 | Q3 | Q4 | "
        low_title = "| :--- | :---: | :---: | :---: | :---: | "
        home_team = f"| **{GameUtils.get_home_team(game)}** | {game['homeTeam']['periods'][0]['score']} | {game['homeTeam']['periods'][1]['score']} | {game['homeTeam']['periods'][2]['score']} | {game['homeTeam']['periods'][3]['score']} |"
        away_team = f"| **{GameUtils.get_away_team(game)}** | {game['awayTeam']['periods'][0]['score']} | {game['awayTeam']['periods'][1]['score']} | {game['awayTeam']['periods'][2]['score']} | {game['awayTeam']['periods'][3]['score']} | "
        if len(game['homeTeam']['periods']) > 4:
            for ot in range(4, len(game['homeTeam']['periods'])):
                title = f"{title}OT{ot - 3} | "
                low_title = f"{low_title}:---: | "
                home_team = f"{home_team}{game['homeTeam']['periods'][ot]['score']} | "
                away_team = f"{away_team}{game['awayTeam']['periods'][ot]['score']} | "
        if game["gameStatus"] == 3:
            title = f"{title}FINAL | "
            low_title = f"{low_title}:---: | "
            home_team = f"{home_team}**{game['homeTeam']['score']}** | "
            away_team = f"{away_team}**{game['awayTeam']['score']}** | "
        body = f"\n---\n{title}\n{low_title}\n{home_team}\n{away_team}\n"
        return body

    @staticmethod
    def get_single_team_body(home_away, game, live_game):
        body = f"\n**{game[home_away]['teamCity']} {game[home_away]['teamName']} ({live_game[home_away]['wins']}-{live_game[home_away]['losses']})**"
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
    def get_thread_title(game, final, is_summer_league):
        title = f"GAME THREAD: {game['homeTeam']['teamCity']} {game['homeTeam']['teamName']} ({game['homeTeam']['wins']}-{game['homeTeam']['losses']})" \
                f" Vs. {game['awayTeam']['teamCity']} {game['awayTeam']['teamName']} ({game['awayTeam']['wins']}-{game['awayTeam']['losses']}) "
        title = f"{title} - {GameUtils.get_game_datetime_est(game)}"
        if is_summer_league:
            title = f"{title} | Summer League"
        if final:
            title = f"{title} [Final Score  {game['homeTeam']['score']}:{game['awayTeam']['score']}]"

        logging.info("SET Post Title: " + title)
        return title

    @staticmethod
    def get_pgt_title(game):
        winner = (game['homeTeam'] if game['homeTeam']['score'] > game['awayTeam']['score'] else game['awayTeam'])
        loser = (game['homeTeam'] if game['homeTeam']['score'] < game['awayTeam']['score'] else game['awayTeam'])
        verb = random.choice(['defeat', 'win over', 'overcome', 'beat'])
        margin = winner['score'] - loser['score']
        if margin < 5:
            verb = random.choice(['barely make it against', 'win over'])
        elif margin > 15:
            verb = random.choice(['crush', 'destroy', 'demolish', 'defeat', 'win over', 'overcome', 'beat'])
        name = f"POST GAME THREAD: The {winner['teamCity']} {winner['teamName']} ({winner['wins']}:{winner['losses']})" \
               f" {verb} the {loser['teamCity']} {loser['teamName']} ({loser['wins']}:{loser['losses']}), {winner['score']}-{loser['score']}"
        logging.info(f"SET Post Game Thread Title: {name}")
        return name
