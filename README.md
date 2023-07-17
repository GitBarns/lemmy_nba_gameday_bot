# Lemmy NBA Gameday Bot

[![GitHub license](https://img.shields.io/badge/license-Apache-blue.svg)](https://raw.githubusercontent.com/tjkessler/plemmy/master/LICENSE.txt)

A Lemmy Bot that create and maintains NBA Game threads, Post Game threads and Daily Game Index threads.

The Bot uses 
* [`nba_api`](https://github.com/swar/nba_api) - An API Client package to access the APIs for NBA.com
* [`pythorhead`](https://github.com/db0/pythorhead) - A python library for interacting with Lemmy


DISCLAIMER: THIS CODE IS STILL IN DEVELOPMENT, USE AT YOUR OWN RISK!

## How does it work


## Running the Bot
### Parameters
The following parameters are needed for the bot to run:
* **_domain_** (or environment var **_INSTANCE_URL_**): Base endpoint to the Lemmy instance, for example 'https://lemmy.world' (note - https, and no '/' at the end)
* **_username_** (or environment var **_BOT_USERNAME_**):The Bot's username
* **_password_** (or environment var **_BOT_PASSWORD_**):The Bot's password
* **_community_** (or environment var **_BOT_COMMUNITY_**): Lemmy community name, so this is the full community URL {domain}/c/{community}
* **_admin_id_** (or environment var **_BOT_ADMIN_ID_**): A Lemmy User ID, that will receive a Direct Message from the BOT when it's failed in unexpected ways... A hacky way to find this ID is by trying to DM the user, and looking at the URL which would be in the shape of https://lemmy.world/create_private_message/<USER ID>


The following parameters are optional:
* **_sleep_** (or environment var **_BOT_SLEEP_SECS_**): Sleep duration between Bot cycles, defaults to 60 seconds
* **_team_name_** (or environment var **_BOT_TEAM_NAME_**): A team abbreviation (e.g. BOS) or full name (Boston Celtics). If set, the Bot will only create posts for this specific team, and will *not* create Daily Index posts (as they will only have a single line)

### Download and run

``` 
git clone https://github.com/GitBarns/lemmy_nba_gameday_bot.git
cd lemmy_nba_gameday_bot
python3 ./nbagamebot.py --domain 'https://lemmy.world' --username '<Bot User name or Email>' --password '<Bot Password>' --community 'nba' --admin_id <LEMMY USER ID>
```

**Logs**  would be created in the Logs folder 

**Note**: This above is for testing purposes. You will need to run the Bot as a background process, using nohup or tmux or byobu or something similar 

## Bugs

Encounter a bug, [report a bug](https://github.com/GitBarns/lemmy_nba_gameday_bot/issues).

## FAQ
### How do I get a Lemmy Bot account?
Creating a Bot is identical to creating a user on your Lemmy Instance but please make sure you mark your Bot as such in its settings page

 _Optionally_: Make the Bot a Mod if Daily Index Posts are needed so it can Feature these posts (pin them to the top of the community)
 
### I got the code, now what?
Well, you will need to self-host the bot. There are quite a few free options for hosting a small python project such as this.
One potential solution is to open a Google Cloud Account and use their free tier compute instance, which should be enough,

### How can I contribute?
Want to contribute? Make a pull request. Contact [@GitBarns](https://github.com/GitBarns) with any questions.  

### What about MLB, NFL, MLS, or any other league?
Any league where a stable python API client exist should be possible but most likely not as part of this library. Please feel free to fork and create your own versions!