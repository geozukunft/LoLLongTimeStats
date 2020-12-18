import asyncio
import sys
from pyot.models import lol
from pyot.core.exceptions import NotFound
import platform
import os
from datetime import timedelta as td
from pyot.core import Settings
from pyot.core import Queue
from typing import List
from pyot.models import lol
from pyot.core import Queue
from pyot.utils import FrozenGenerator, shuffle_list

if platform.system() == 'Windows':
    from pyot.utils.internal import silence_proactor_pipe_deallocation

    silence_proactor_pipe_deallocation()

Settings(
    MODEL="LOL",
    DEFAULT_PLATFORM="EUW1",
    DEFAULT_REGION="EUROPE",
    DEFAULT_LOCALE="EN_US",
    PIPELINE=[
        {
            "BACKEND": "pyot.stores.Omnistone",
            "LOG_LEVEL": 30
        },
        {"BACKEND": "pyot.stores.MerakiCDN"},
        {"BACKEND": "pyot.stores.CDragon"},
        {
            "BACKEND": "pyot.stores.MongoDB",
            "DB": 'pyotdata',
            "HOST": "127.0.0.1",
            "PORT": 27017,
            "LOG_LEVEL": 30,
            "EXPIRATIONS": {
                "champion_mastery_v4_all_mastery": td(days=1),
                "champion_mastery_v4_by_champion_id": td(days=1),
                "league_v4_summoner_entries": td(days=3650),
                "league_v4_entries_by_division": td(days=3650),
                "league_v4_league_by_league_id": td(days=3650),
                "match_v4_match": td(days=3650),
                "match_v4_timeline": td(days=3650),
                "match_v4_matchlist": td(days=1),
                "summoner_v4_by_name": td(days=3650),
                "summoner_v4_by_id": td(days=3650),
                "summoner_v4_by_account_id": td(days=3650),
                "summoner_v4_by_puuid": td(days=3650),
                "third_party_code_v4_code": 0,
                "cdragon_champion_by_id": td(hours=3),
                "cdragon_item_full": td(hours=3),
                "cdragon_rune_full": td(hours=3),
                "cdragon_profile_icon_full": td(hours=3),
                "cdragon_spells_full": td(hours=3),
                "meraki_champion_by_key": td(hours=3),
                "meraki_item_by_id": td(hours=3)
            },
        },
        {
            "BACKEND": "pyot.stores.RiotAPI",
            "API_KEY": "RGAPI-4be2cd22-7fd6-4365-b5e7-efe54aafc217",  # API KEY
            "LOG_LEVEL": 30
        }
    ]
).activate()  # <- DON'T FORGET TO ACTIVATE THE SETTINGS


async def main():
    try:
        summoner = await lol.Summoner(name="geozukunft", platform="EUW1").get()
        print(summoner.name, 'in', summoner.platform.upper(), 'is level', summoner.level)
    except NotFound:
        print('Summoner not found')
    await pull_puuids()


async def get_puuid(queue: Queue, summoner: lol.Summoner):
    summoner = await summoner.get(sid=queue.sid)
    return summoner.puuid


async def pull_puuids():
    async with Queue() as queue:  # type: Queue
        await queue.put(lol.ChallengerLeague(queue="RANKED_SOLO_5x5", platform="na1").get(sid=queue.sid))
        await queue.put(lol.MasterLeague(queue="RANKED_SOLO_5x5", platform="na1").get(sid=queue.sid))
        leagues = await queue.join()  # type: List[lol.ChallengerLeague]

        summoners = []
        for league in leagues:
            for entry in league.entries:
                summoners.append(entry.summoner)
        # Shuffles the list by platform to balance rate limits by region
        # Also freezes the list to prevent mutation that causes memory leak
        summoners = FrozenGenerator(shuffle_list(summoners, "platform"))

        for summoner in summoners:
            await queue.put(get_puuid(queue, summoner))
        print(await queue.join())


if __name__ == "__main__":
    schleife = asyncio.new_event_loop()
    asyncio.set_event_loop(schleife)
    asyncio.run(main())


async def summoner_level(name, platform):
    '''Get summoner level by name and platform'''

    # Pyot Model: lol
    # Pyot Core Object: Summoner
    # Refer: https://paaksing.github.io/Pyot/models/lol_summoner.html

    try:
        summoner = await lol.Summoner(name=name, platform=platform).get()
        print(summoner.name, 'in', summoner.platform.upper(), 'is level', summoner.level)
    except NotFound:
        print('Summoner not found')
