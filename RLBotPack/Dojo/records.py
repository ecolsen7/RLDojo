import os
import json
from typing import List, Optional
from dataclasses import dataclass, asdict

# Scenario mode records
# Contains:
# - Offensive scenario type
# - Defensive scenario type
# - Total goals scored
# - Human score
# - Bot score
# - Bot name

@dataclass
class ScenarioRecord:
    offensive_scenario_type: str
    defensive_scenario_type: str
    total_goals_scored: int
    human_score: int
    bot_score: int
    bot_name: str

# Race mode records
# Contains:
# - Number of trials
# - Total time to finish

@dataclass
class RaceRecord:
    number_of_trials: int
    total_time_to_finish: float

def get_race_records_path():
    appdata_path = os.path.expandvars("%APPDATA%")
    if not os.path.exists(os.path.join(appdata_path, "RLBot", "Dojo")):
        os.makedirs(os.path.join(appdata_path, "RLBot", "Dojo"))
    return os.path.join(appdata_path, "RLBot", "Dojo", "race_records.json")

def get_race_records() -> List[RaceRecord]:
    if not os.path.exists(get_race_records_path()):
        return []

    with open(get_race_records_path(), "r") as f:
        try:
            records = json.load(f)
            print(f"Loaded records {str(records)}")
        except json.JSONDecodeError:
            # If the file is empty or corrupted, create a new one
            records = []

    parsed_records = [RaceRecord(**record) for record in records]

    return parsed_records

def get_race_record(number_of_trials: int) -> Optional[float]:
    for record in get_race_records():
        if record.number_of_trials == number_of_trials:
            print(f"Found record for {number_of_trials} trials: {record}")
            return record.total_time_to_finish
    print(f"No record found for the given number of trials. {str(get_race_records())}")

def store_race_records(records: List[RaceRecord]):
    race_records = [
        asdict(record) for record in records
    ]
    with open(get_race_records_path(), "w") as f:
        print(f"Storing race records to {get_race_records_path()}")
        print(f"Records: {json.dumps(race_records)}")
        json.dump(race_records, f, indent=4)


def update_race_record_if_faster(record: RaceRecord):
    if record.total_time_to_finish == 0:
        print("Record time is 0, not updating")
        return

    # Debug log
    print(f"Updating race record if faster at path: {get_race_records_path()}, record: {record}")
    race_records = get_race_records()

    # Compare this run to the previous record at the same number of trials

    for race_record in race_records:
        if race_record.number_of_trials == record.number_of_trials:
            race_record.total_time_to_finish = min(
                race_record.total_time_to_finish, record.total_time_to_finish
            )
            break
    else:
        race_records.append(record)

    # Store the records
    store_race_records(race_records)
