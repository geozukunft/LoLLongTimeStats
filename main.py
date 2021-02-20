import asyncio
import platform
import threading
import time
from datetime import timedelta as td

import asyncpg
from pyot.core import Queue
from pyot.core import Settings
from pyot.core.exceptions import NotFound
from pyot.models import lol

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
            "LOG_LEVEL": 10
        },
        {"BACKEND": "pyot.stores.MerakiCDN"},
        {"BACKEND": "pyot.stores.CDragon"},
        {
            "BACKEND": "pyot.stores.MongoDB",
            "DB": 'pyotdata',
            "HOST": "192.168.20.145",
            "PORT": 27017,
            "LOG_LEVEL": 10,
            "EXPIRATIONS": {
                "champion_mastery_v4_all_mastery": td(days=1),
                "champion_mastery_v4_by_champion_id": td(days=1),
                "league_v4_summoner_entries": td(days=1),
                "league_v4_entries_by_division": td(days=1),
                "league_v4_league_by_league_id": td(days=1),
                "league_v4_challenger_league": td(days=1),
                "league_v4_grandmaster_league": td(days=1),
                "match_v4_match": td(days=3650),
                "match_v4_timeline": td(days=3650),
                "match_v4_matchlist": td(days=10),
                "summoner_v4_by_name": td(days=1),
                "summoner_v4_by_id": td(days=1),
                "summoner_v4_by_account_id": td(days=1),
                "summoner_v4_by_puuid": td(days=1),
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
            "API_KEY": "",  # API KEY
            "LOG_LEVEL": 10
        }
    ]
).activate()  # <- DON'T FORGET TO ACTIVATE THE SETTINGS

credentials = {"user": "loldata", "password": "LoLData2021#", "database": "loldata", "host": "db.geozukunft.at",
               "port": "6969"}
db = " "
dbg = ""


class myThread(threading.Thread):
    def __init__(self, threadID, gamecount, gameIds):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.gamecount = gamecount
        self.gameIds = gameIds

    def run(self):
        print(f'Starting Thread {self.threadID} with {self.gamecount} games')
        between_function(self.threadID, self.gameIds)
        print(f'Exiting Thread {self.threadID}')


# Don't ask me why I use this stackoverflow told me to do so
def between_function(threadId, gameIds):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(pull_games(threadId, gameIds))
    loop.close()


async def main():
    global db
    db = await asyncpg.create_pool(**credentials)
    global dbg

    """
    try:
        summoner = await lol.Summoner(name="geozukunft", platform="EUW1").get()
        print(summoner.name, 'in', summoner.platform.upper(), 'is level', summoner.level)
    except NotFound:
        print('Summoner not found')"""
    summoners = ["geozukunft", "Schmidi49", "MiniSchmidi", "EvoSchmidi"]
    # ["geozukunft", "Schmidi49", "MiniSchmidi"]
    #await pull_gameids(summoners)

    testmatch = await lol.Match(id=5011121798, platform="EUW1", include_timeline=True).get()
    testtimeline = await lol.Timeline(id=5011121798, platform="EUW1").get()
    """
    for team in testmatch.teams:
        for participant in team.participants:
            for event in participant.timeline.events:
                print(event.type)
                print(event.timestamp)
                print("halt")
    """
    print(testmatch)
    #for summoner in summoners:
    #    await pull_matchtimelines()
    """
    gameIdcount = await db.fetchrow('SELECT COUNT(*) FROM matches')
    threadcount = 8
    idsperthread: int = math.ceil(int(gameIdcount[0]) / threadcount)
    thread = 0
    offset = 0
    gameIdblock = []
    while thread < threadcount:
        gameIds = await db.fetch(
            'SELECT "gameId", "platformId" FROM matches ORDER BY timestamp ASC OFFSET $1 ROWS FETCH FIRST $2 ROW ONLY',
            offset, idsperthread)
        gameIdblock.append(gameIds)
        offset += idsperthread
        thread += 1

    threads = []
    for i in range(threadcount):
        thread = myThread(i, len(gameIdblock[i]), gameIdblock[i])
        threads.append(thread)
        thread.start()
"""
    print("Starring with Inserting Games")
    t = time.time()
    games = await db.fetch('SELECT "gameId", "platformId" FROM matches ORDER BY timestamp ASC LIMIT 200')
    print(f'Execute took {time.time() - t}')
    async with Queue() as queue:
        dbg = await asyncpg.create_pool(**credentials)
        for game in games:
            await queue.put(pull_games(queue, game))

    print("Exiting Main Thread")

    # accountId = await db.fetchrow('SELECT "accountId" FROM summoner WHERE name = $1', summoner)


async def pull_matchtimelines():
    global db

    matchids = await db.fetch('SELECT "gameId", "platformId"  FROM matches')

    for matchid in matchids:
        try:
            timeline = await lol.Match(id=matchid['gameId'], platform=matchid['platformId'], include_timeline=True).get()
            print(f"Game {timeline.id} pulled")
        except Exception as error:
            print(f'Match with number {matchid["gameId"]} had following error retrieving it s timeline: {error}')


async def pull_games(queue: Queue, gameId):
    dbg = await asyncpg.create_pool(**credentials)
    i: int = 0
    cmatch: lol.Match
    special = await asyncpg.connect(**credentials)
    t = time.time()
    try:
        # Pull Game
        cmatch = await lol.Match(id=gameId['gameId'], platform=gameId['platformId'], include_timeline=True).get()
        # Add Primary Game data
        await dbg.execute('INSERT INTO match VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) on conflict DO NOTHING ',
                          cmatch.id, cmatch.platform.lower(),
                          cmatch.type, cmatch.mode, cmatch.version, cmatch.map_id, cmatch.season_id,
                          cmatch.queue_id,
                          cmatch.creation, cmatch.duration)
        # Add team and player specific data
        for team in cmatch.teams:
            await dbg.execute(
                'INSERT INTO "matchTeamData" VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16) on conflict DO NOTHING ',
                cmatch.id, cmatch.platform.lower(), team.id, team.first_blood,
                team.first_tower, team.first_inhibitor, team.first_baron,
                team.first_dragon, team.first_rift_herald, team.tower_kills,
                team.inhibitor_kills, team.baron_kills, team.dragon_kills,
                team.vilemaw_kills, team.rift_herald_kills,
                team.dominion_victory_score)

            # Add participant data and participant stats data of blue team
            for participant in team.participants:
                stats = participant.stats
                await dbg.execute(
                    'INSERT INTO "matchParticipantData" VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14) on conflict DO NOTHING',
                    cmatch.id, cmatch.platform.lower(), participant.id, participant.team_id,
                    participant.champion_id,
                    participant.spell_ids, participant.profile_icon_id, participant.account_id,
                    participant.match_history_uri,
                    participant.current_account_id, participant.current_platform.lower(), participant.summoner_name,
                    participant.summoner_id, participant.platform.lower())

                await add_participantStatData(cmatch, participant, dbg)
                f = time.time()
                await add_participantTimelineFrames(cmatch, participant, special)
                #print(f'Frames took: {time.time() - f}')
                e = time.time()
                #await add_participantTimelineEvents(cmatch, participant, dbg)
                #print(f'Events took: {time.time() - e}')
            # Add bans blue team
            for ban in team.bans:
                await dbg.execute('INSERT INTO "matchBanData" VALUES ($1,$2,$3,$4,$5) on conflict DO NOTHING ',
                                  cmatch.id, cmatch.platform.lower(), team.id, ban.pick_turn, ban.champion_id)

        await dbg.execute('UPDATE "match" SET inserted = True WHERE id=$1', cmatch.id)
    except Exception as error:
        #print(f'Match with number had {gameId} following error inserting the game into the DB: {error}')
        pass
    print(f'{time.time() - t}')
    i += 1
    # print(match)
    # print(gameIds)
    await dbg.close()
    # print(f'Thread {threadId} finished proccesing {len(gameIds)} games')


async def add_participantTimelineEvents(match, participant, dbg):
    for event in participant.timeline.events:
        if event.type == "CHAMPION_KILL":
            try:
                await dbg.execute(
                    'INSERT INTO "matchEventData"("gameId","platformId",participant_id,type,timestamp,'
                    'assisting_participant_ids,killer_id,position_x,position_y,victim_id) VALUES ($1,$2,$3,$4,$5,$6,$7,'
                    '$8,$9,$10) on conflict DO NOTHING', match.id, match.platform.lower(), participant.id, event.type,
                    event.timestamp, event.assisting_participant_ids, event.killer_id, event.position.x,
                    event.position.y, event.victim_id)
            except Exception as error:
                print(
                    f'Event of {participant.id} in game {match.id} had an following error in CHAMPION KILL {error}')
        elif event.type == "WARD_PLACED":
            try:
                await dbg.execute(
                    'INSERT INTO "matchEventData"("gameId","platformId",participant_id,type,timestamp,ward_type,'
                    'creator_id) VALUES ($1,$2,$3,$4,$5,$6,$7) on conflict DO NOTHING', match.id,
                    match.platform.lower(),
                    participant.id, event.type, event.timestamp, event.ward_type, event.creator_id)
            except Exception as error:
                print(
                    f'Event of {participant.id} in game {match.id} had an following error in WARD PLACED {error}')
        elif event.type == "WARD_KILL":
            try:
                await dbg.execute(
                    'INSERT INTO "matchEventData"("gameId","platformId",participant_id,type,timestamp,ward_type,'
                    'killer_id) VALUES ($1,$2,$3,$4,$5,$6,$7) on conflict DO NOTHING', match.id, match.platform.lower(),
                    participant.id, event.type, event.timestamp, event.ward_type, event.killer_id)
            except Exception as error:
                print(
                    f'Event of {participant.id} in game {match.id} had an following error in WARD KILLED {error}')
        elif event.type == "BUILDING_KILL":
            try:
                await dbg.execute(
                    'INSERT INTO "matchEventData"("gameId","platformId",participant_id,type,timestamp,'
                    'assisting_participant_ids,building_type,killer_id,lane_type,position_x,position_y,team_id,'
                    'tower_type) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13) on conflict DO NOTHING', match.id,
                    match.platform.lower(),
                    participant.id, event.type, event.timestamp, event.assisting_participant_ids,
                    event.building_type, event.killer_id, event.lane_type, event.position.x, event.position.y,
                    event.team_id, event.tower_type)
            except Exception as error:
                print(
                    f'Event of {participant.id} in game {match.id} had an following error in BUILDING KILLED {error}')
        elif event.type == "ELITE_MONSTER_KILL":
            if event.monster_type == "DRAGON":
                try:
                    await dbg.execute(
                        'INSERT INTO "matchEventData"("gameId","platformId",participant_id,type,timestamp,killer_id,'
                        'monster_sub_type,monster_type,position_x,position_y) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) '
                        'on conflict DO NOTHING', match.id, match.platform.lower(), participant.id, event.type,
                        event.timestamp, event.killer_id, event.monster_sub_type, event.monster_type,
                        event.position.x,
                        event.position.y)
                except Exception as error:
                    print(
                        f'Event of {participant.id} in game {match.id} had an following error in MONSTER KILL {error}')
            elif event.monster_type == "RIFTHERALD" or event.monster_type == "BARON_NASHOR":
                try:
                    await dbg.execute(
                        'INSERT INTO "matchEventData"("gameId","platformId",participant_id,type,timestamp,killer_id,'
                        'monster_type,position_x,position_y) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) '
                        'on conflict DO NOTHING', match.id, match.platform.lower(), participant.id, event.type,
                        event.timestamp, event.killer_id, event.monster_type, event.position.x,
                        event.position.y)
                except Exception as error:
                    print(
                        f'Event of {participant.id} in game {match.id} had an following error in MONSTER KILL {error}')
            else:
                try:
                    await dbg.execute(
                        'INSERT INTO "matchEventData"("gameId","platformId",participant_id,type,timestamp,killer_id,'
                        'monster_sub_type,monster_type,position_x,position_y) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) '
                        'on conflict DO NOTHING', match.id, match.platform.lower(), participant.id, event.type,
                        event.timestamp, event.killer_id, event.monster_sub_type, event.monster_type,
                        event.position.x,
                        event.position.y)
                except Exception as error:
                    print(
                        f'Event of {participant.id} in game {match.id} had an following error in MONSTER KILL {error}')
        elif event.type == "ITEM_PURCHASED":
            try:
                await dbg.execute(
                    'INSERT INTO "matchEventData"("gameId","platformId",participant_id,type,timestamp,item_id) '
                    'VALUES ($1,$2,$3,$4,$5,$6) on conflict DO NOTHING', match.id, match.platform.lower(),
                    event.participant_id,
                    event.type, event.timestamp, event.item_id)
            except Exception as error:
                print(
                    f'Event of {participant.id} in game {match.id} had an following error in ITEM PURCHASE {error}')
        elif event.type == "ITEM_SOLD":
            try:
                await dbg.execute(
                    'INSERT INTO "matchEventData"("gameId","platformId",participant_id,type,timestamp,item_id) '
                    'VALUES ($1,$2,$3,$4,$5,$6) on conflict DO NOTHING', match.id, match.platform.lower(),
                    event.participant_id,
                    event.type, event.timestamp, event.item_id)
            except Exception as error:
                print(
                    f'Event of {participant.id} in game {match.id} had an following error in ITEM SOLD {error}')
        elif event.type == "ITEM_DESTROYED":
            try:
                await dbg.execute(
                    'INSERT INTO "matchEventData"("gameId","platformId",participant_id,type,timestamp,item_id) '
                    'VALUES ($1,$2,$3,$4,$5,$6) on conflict DO NOTHING', match.id, match.platform.lower(),
                    event.participant_id,
                    event.type, event.timestamp, event.item_id)
            except Exception as error:
                print(
                    f'Event of {participant.id} in game {match.id} had an following error in ITEM DESTROYED {error}')
        elif event.type == "ITEM_UNDO":
            try:
                await dbg.execute(
                    'INSERT INTO "matchEventData"("gameId","platformId",participant_id,type,timestamp,after_id,'
                    'before_id) VALUES ($1,$2,$3,$4,$5,$6,$7) on conflict DO NOTHING', match.id, match.platform.lower(),
                    event.participant_id, event.type, event.timestamp, event.after_id, event.before_id)
            except Exception as error:
                print(
                    f'Event of {participant.id} in game {match.id} had an following error in ITEM UNDO {error}')
        elif event.type == "SKILL_LEVEL_UP":
            try:
                await dbg.execute(
                    'INSERT INTO "matchEventData"("gameId","platformId",participant_id,type,timestamp,level_up_type,'
                    'skill_slot) VALUES ($1,$2,$3,$4,$5,$6,$7) on conflict DO NOTHING', match.id,
                    match.platform.lower(),
                    event.participant_id, event.type, event.timestamp, event.level_up_type, event.skill_slot, )
            except Exception as error:
                print(
                    f'Event of {participant.id} in game {match.id} had an following error in SKILL LVL UP {error}')
        else:
            print("EDGE CASE IN EVENT TYPE!")


async def add_participantTimelineFrames(match, participant, dbg):
    i: int = 0
    data: list = []
    for frame in participant.timeline['frames']:
        if not hasattr(frame, 'position'):
            x = 0
            y = 0
        else:
            x = frame['position']['x']
            y = frame['position']['y']
        try:
            t = tuple([match.id, match.platform.lower(), frame['participantId'], i, 0, 0,
                       frame['totalGold'], frame['level'], frame['xp'], frame['currentGold'], x, y,
                       frame['jungleMinionsKilled']])
            data.append(t)
        except Exception as error:
            print(
                f'Participant {participant.id} in game {match.id} had following error while inserting Timeline Frames {error}')
        i += 1
    try:
        await dbg.copy_records_to_table('matchFrameData', records=data)
    except Exception as error:
        print(error)


async def add_participantStatData(match, participant, dbg):
    stats = participant.stats
    timeline = participant.timeline
    if not hasattr(stats, 'first_inhibitor_kill'):
        setattr(stats, 'first_inhibitor_kill', False)
    if not hasattr(stats, 'first_inhibitor_assist'):
        setattr(stats, 'first_inhibitor_assist', False)
    if not hasattr(stats, 'neutral_minions_killed_team_jungle'):
        setattr(stats, 'neutral_minions_killed_team_jungle', 0)
    if not hasattr(stats, 'neutral_minions_killed_enemy_jungle'):
        setattr(stats, 'neutral_minions_killed_enemy_jungle', 0)
    if not hasattr(stats, 'wards_placed'):
        setattr(stats, 'wards_placed', 0)
    if not hasattr(stats, 'wards_killed'):
        setattr(stats, 'wards_killed', 0)
    if not hasattr(stats, 'first_tower_kill'):
        setattr(stats, 'first_tower_kill', False)
    if not hasattr(stats, 'first_tower_assist'):
        setattr(stats, 'first_tower_assist', False)
    if not hasattr(stats, 'first_blood_kill'):
        setattr(stats, 'first_blood_kill', False)
    if not hasattr(stats, 'first_blood_assist'):
        setattr(stats, 'first_blood_assist', False)

    try:
        await dbg.execute(
            'INSERT INTO "matchParticipantStatData" VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,'
            '$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27,$28,$29,$30,$31,$32,$33,$34,$35,$36,$37,$38,$39,'
            '$40,$41,$42,$43,$44,$45,$46,$47,$48,$49,$50,$51,$52,$53,$54,$55,$56,$57,$58,$59,$60,$61,$62,$63,'
            '$64,$65,$66,$67,$68) on conflict DO NOTHING ',
            match.id, match.platform.lower(), participant.id, stats.win, stats.dominion_scores, stats.spell_ids,
            stats.item_ids, stats.rune_ids, stats.stat_rune_ids, stats.rune_vars, stats.rune_main_style,
            stats.rune_sub_style, stats.kills, stats.deaths, stats.assists, stats.largest_killing_spree,
            stats.largest_multi_kill, stats.killing_sprees, stats.longest_time_spent_living, stats.double_kills,
            stats.triple_kills, stats.quadra_kills, stats.penta_kills, stats.unreal_kills,
            stats.total_damage_dealt, stats.magic_damage_dealt, stats.physical_damage_dealt,
            stats.true_damage_dealt, stats.largest_critical_strike, stats.total_damage_dealt_to_champions,
            stats.magic_damage_dealt_to_champions, stats.physical_damage_dealt_to_champions,
            stats.true_damage_dealt_to_champions, stats.total_heal, stats.total_units_healed,
            stats.damage_self_mitigated, stats.damage_dealt_to_objectives, stats.damage_dealt_to_turrets,
            stats.vision_score, stats.time_ccing_others, stats.total_damage_taken, stats.magical_damage_taken,
            stats.physical_damage_taken, stats.true_damage_taken, stats.gold_earned, stats.gold_spent,
            stats.turret_kills, stats.inhibitor_kills, stats.total_minions_killed, stats.neutral_minions_killed,
            stats.neutral_minions_killed_team_jungle, stats.neutral_minions_killed_enemy_jungle,
            stats.total_time_crowd_control_dealt, stats.champ_level, stats.vision_wards_bought_in_game,
            stats.sight_wards_bought_in_game, stats.wards_placed, stats.wards_killed, stats.first_blood_kill,
            stats.first_blood_assist, stats.first_tower_kill, stats.first_tower_assist,
            stats.first_inhibitor_kill, stats.first_inhibitor_assist, stats.combat_player_score,
            stats.objective_player_score, stats.total_player_score, stats.total_score_rank)
    except Exception as error:
        print(error)

    """if match.duration > td(minutes=10):
        await dbg.execute(
            'INSERT INTO "matchParticipantTimelineData" VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) on conflict DO NOTHING ',
            match.id, match.platform.lower(), timeline.participant_id, timeline.creeps_per_min_deltas,
            timeline.xp_per_min_deltas, timeline.gold_per_min_deltas, timeline.damage_taken_per_min_deltas,
            timeline.role, timeline.lane)"""


async def get_puuid(queue: Queue, summoner: lol.Summoner):
    summoner = await summoner.get(sid=queue.sid)
    return summoner.puuid


async def get_accountid(queue: Queue, summoner: lol.Summoner):
    summoner = await summoner.get(sid=queue.sid)
    return summoner.account_id


async def get_matchlists(queue: Queue, summoner: lol.Summoner):
    global db
    summoner = await summoner.get(sid=queue.sid)
    run: bool = True
    index: int = 0
    matchlists = []
    while run:
        matchlist = await lol.MatchHistory(account_id=summoner.account_id).query(begin_index=index).get()
        if matchlist.end_index == matchlist.start_index:
            run = False
        else:
            matchlists.append(matchlist)
        index = index + 100
        print(matchlist.start_index)
    for matchlist in matchlists:
        for match in matchlist.entries:
            try:
                await db.execute("INSERT INTO matches VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) on conflict DO NOTHING ",
                                 matchlist.summoner.account_id,
                                 match.id, match.role, match.season_id, match.platform.lower(), match.champion_id,
                                 match.queue_id,
                                 match.lane, match.creation.timestamp())
            except Exception as error:
                print(f'Match with number {match.id} had following error inserting its ID: {error}')
    return matchlists


async def pull_gameids(summonernames):
    global db
    async with Queue() as queue:  # type: Queue
        summoners = []
        for name in summonernames:
            response = await lol.Summoner(name=name, platform="EUW1").get(sid=queue.sid)
            summoners.append(response)

        for summoner in summoners:
            # await queue.put(get_puuid(queue, summoner))
            try:
                await db.execute("INSERT INTO summoner VALUES ($1,$2,$3,$4,$5,$6,$7) on conflict DO NOTHING ",
                                 summoner.account_id,
                                 summoner.profile_icon_id, summoner.revision_date.timestamp(), summoner.name,
                                 summoner.id,
                                 summoner.puuid, summoner.level)
            except Exception as error:
                print(f'Summoner {summoner.name} had following error inserting into the DB: {error}')
            await queue.put(get_matchlists(queue, summoner))
        user_matchlists = await queue.join()
        # print(user_matchlists)


"""
        userdata = []
        for user_matchlist in user_matchlists:
            matchdata = []
            for matchlist in user_matchlist:
                for match in matchlist:
                    try:
                        matchdata.append(await lol.Match(id=match.id, platform=match.platform.lower()).get())
                    except Exception as error:
                        print(f'Match with number {match.id} had following error: {error}')
"""

"""
            userdata.append(matchdata)
        
        
        
        
        
        
        duration: time = td(seconds=0)
        
        
        
        
        for matchdata in userdata:
            for singlematch in matchdata:
                duration = duration + singlematch.duration
        print("test")
        print(duration)
        """

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
