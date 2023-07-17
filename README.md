# Lemmy NBA Gameday Bot

A Lemmy Bot that create and maintains NBA Game threads, Post Game threads and Daily Game Index threads

DISCLAIMER: I HOLD NO RESPONSIBILITY ON THE BOT OR THE CODE, IT MAY OR MAY NOT WORK, USE AT YOUR OWN RISK!

## SETUP
* Create a Lemmy bot account. Creating a Bot is identical to creating a user on your Lemmy Instance but please make sure you mark your Bot as such in it's settings page
* Optionally - Make the Bot a Mod if Daily Index Posts are needed so it can Feature these posts (pin them to the top of the community) 
* A hosting solution to run the Bot from. The GCP free tier should be enough as the Bot is very lightweight. 

## Parameters
The following parameters are needed for the bot to run:
* **domain** can also be set via an Environemnt variable **INSTANCE_URL**: Base endpoint to the Lemmy instance, for example 'https://lemmy.world' (note - https, and no '/' at the end)
* **username** can also be set via an Environemnt variable **BOT_USERNAME**:The Bot's user name
* **password** can also be set via an Environemnt variable **BOT_PASSWORD**:The Bot's password
* **community** can also be set via an Environemnt variable **BOT_COMMUNITY**: Lemmy community name, so this is the full community URL {domain}/c/{community}
* **admin_id** can also be set via an Environemnt variable **BOT_ADMIN_ID**: A Lemmy User ID, that will recieve a Direct Message from the BOT when it's failed in unexpected ways... A hacky way to find this ID is by trying to DM the user, and looking at the URL which would be in the shape of https://lemmy.world/create_private_message/<USER ID>


The following parameters are optional:
* **sleep** can also be set via an Environemnt variable **BOT_SLEEP_SECS**: Sleep duraiton between Bot cycles, defaults to 60 seconds
* **team_name** can also be set via an Environemnt variable **BOT_TEAM_NAME**: A team abbreviation (e.g. BOS) or full name (Boston Celtics). If set, the Bot will only create posts for this specific team, and will *not* create Daily Index posts (as they will only have a single line)


## Running the Bot

``` 
git clone https://github.com/GitBarns/Lemmy_NBA_Gameday_Bot.git
cd Lemmy_NBA_Gameday_Bot
python3 ./nbagamebot.py --domain 'https://lemmy.world' --username '<Bot User name or Email>' --password '<Bot Password>' --community 'nba' --admin_id <LEMMY USER ID>
```
