import logging
import time


class PostUtils:

    @staticmethod
    def get_post_game_id(gamepost):
        return gamepost["body"][-15:-5]

    @staticmethod
    def game_info(game):
        return f"{game['gameId']}: {game['gameStatusText']} - {game['homeTeam']['teamName']} vs {game['awayTeam']['teamName']}"

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
