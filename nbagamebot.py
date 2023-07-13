import argparse
import logging
import os
import time
from logging.handlers import RotatingFileHandler

from nba.gamethreadmaker import GameThreadMaker


def run_post_maker(domain, community, username, password, is_summer_league, admin_id):
    try:
        logging.info("Starting post maker")
        post_maker = GameThreadMaker(domain, username, password, community, is_summer_league, admin_id)
        logging.info(f"Logging into {domain}/c/{community}")
        post_maker.log_in()
        logging.info(f"Logged into {domain}/c/{community}, will begin processing games")
        post_maker.process_posts()
    except Exception:
        logging.exception("Failed to process match threads")


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
    parser.add_argument("--summer_league", default=os.environ.get("FORCE_SUMMER_LEAGUE"))
    args = parser.parse_args()
    if not args.domain or not args.username or not args.password or not args.community or not args.admin_id or not args.sleep:
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
    logging.info("Starting Up...")

    while True:
        run_post_maker(args.domain, args.community, args.username, args.password, args.summer_league, args.admin_id)
        logging.info(f"Done processing match threads, will sleep for {args.sleep} seconds...")
        time.sleep(int(args.sleep))


if __name__ == "__main__":
    main()
