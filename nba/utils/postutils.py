class PostUtils:

    @staticmethod
    def get_post_id(gamepost):
        return gamepost["body"][-15:-5]

    @staticmethod
    def game_info(game):
        return f"{game['gameId']}: {game['gameStatusText']} - {game['homeTeam']['teamName']} vs {game['awayTeam']['teamName']}"

