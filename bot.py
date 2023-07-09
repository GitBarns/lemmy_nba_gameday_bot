import argparse
import logging
import os
from logging.handlers import RotatingFileHandler

import time

from nba.nbathreadmaker import NBAMatchThreadMaker


def run_post_maker(domain, community, username, password):
    try:
        logging.info("Starting thread maker")
        retry = 1
        post_maker = NBAMatchThreadMaker(domain)
        logging.info(f"Logging into {domain}/c/{community}")
        while not post_maker.log_in(username, password, community) and retry < 10:
            retry += 1
            logging.warning(f"Failed to login, will retry in {retry * 5} secs, try #{retry}")
            time.sleep(5 * retry)
        logging.info(f"Logged into {domain}/c/{community}, will begin processing games")
        post_maker.create_or_update_threads()
    except Exception as err:
        logging.error("Failed to process match threads", err)


def main():
    # Get and parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("--domain", default=os.environ.get("INSTANCE_URL"))
    parser.add_argument("--username", default=os.environ.get("BOT_USERNAME"))
    parser.add_argument("--password", default=os.environ.get("BOT_PASSWORD"))
    parser.add_argument("--community", default=os.environ.get("BOT_COMMUNITY"))
    parser.add_argument("--sleep", default=os.environ.get("BOT_SLEEP_SECS"))
    args = parser.parse_args()
    if not args.domain or not args.username or not args.password or not args.community:
        exit(parser.print_usage())

    logging.root.handlers = []
    logging.basicConfig(
        level=(logging.DEBUG if args.verbose > 0 else logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler('logs/bot.log', maxBytes=10 * 1000 * 1000, backupCount=10),
            logging.StreamHandler()
        ]
    )
    logging.info("Starting Up...")

    while True:
        run_post_maker(args.domain, args.community, args.username, args.password)
        logging.info(f"Done processing match threads, will sleep for {args.sleep} seconds...")
        time.sleep(int(args.sleep))


if __name__ == "__main__":
    main()
