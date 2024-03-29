import argparse
import logging
import os
import time
from logging.handlers import RotatingFileHandler

from nba.gamethreadmaker import GameThreadMaker


def run_bot(domain, community, username, password, team_name,admin_id, sleep):
    try:
        logging.info("Starting bot run")
        bot = GameThreadMaker(domain, username, password, community, team_name, admin_id)
        bot.log_in()
        logging.info(f"Logged into {domain}/c/{community}, will begin processing games")
        bot.run()
    except:
        logging.exception("Failed to run the bot")
    finally:
        logging.info(f"Done, will sleep for {sleep} seconds...")
        time.sleep(sleep)


def main():
    # Get and parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("--domain", default=os.environ.get("INSTANCE_URL"))
    parser.add_argument("--username", default=os.environ.get("BOT_USERNAME"))
    parser.add_argument("--password", default=os.environ.get("BOT_PASSWORD"))
    parser.add_argument("--community", default=os.environ.get("BOT_COMMUNITY"))
    parser.add_argument("--admin_id", default=os.environ.get("BOT_ADMIN_ID"))
    parser.add_argument("--sleep", default=os.environ.get("BOT_SLEEP_SECS"))
    parser.add_argument("--team_name", default=os.environ.get("BOT_TEAM_NAME"))
    args = parser.parse_args()
    if not args.domain or not args.username or not args.password or not args.community or not args.admin_id:
        exit(parser.print_usage())

    logging.root.handlers = []
    logging.basicConfig(
        level=(logging.DEBUG if args.verbose > 0 else logging.INFO),
        format="%(asctime)s  %(name)s :: %(levelname)s :: %(message)s",
        handlers=[
            RotatingFileHandler('logs/nba_game_bot.log', maxBytes=10 * 1000 * 1000, backupCount=10),
            logging.StreamHandler()
        ]
    )
    logging.info("Starting up the Bot...")
    if not args.sleep:
        args.sleep = 60

    while True:
        run_bot(args.domain, args.community, args.username, args.password, args.team_name, args.admin_id, args.sleep)


if __name__ == "__main__":
    main()
