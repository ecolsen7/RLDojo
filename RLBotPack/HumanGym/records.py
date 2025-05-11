import os
import json
# Scenario mode records
# Contains:
# - Offensive scenario type
# - Defensive scenario type
# - Total goals scored
# - Human score
# - Bot score
# - Bot name

class ScenarioRecord:
    def __init__(self, offensive_scenario_type, defensive_scenario_type, total_goals_scored, human_score, bot_score, bot_name):
        self.offensive_scenario_type = offensive_scenario_type
        self.defensive_scenario_type = defensive_scenario_type
        self.total_goals_scored = total_goals_scored
        self.human_score = human_score
        self.bot_score = bot_score
        self.bot_name = bot_name

    def to_json(self):
        return json.dump(self.__dict__)

# Race mode records
# Contains:
# - Number of trials
# - Total time to finish

class RaceRecord:
    def __init__(self, number_of_trials, total_time_to_finish):
        self.number_of_trials = number_of_trials
        self.total_time_to_finish = total_time_to_finish

    def to_json(self):
        return json.dump(self.__dict__)

def get_race_records_path():
    appdata_path = os.path.expandvars("%APPDATA%")
    if not os.path.exists(os.path.join(appdata_path, "RLBot", "HumanGym")):
        os.makedirs(os.path.join(appdata_path, "RLBot", "HumanGym"))
    return os.path.join(appdata_path, "RLBot", "HumanGym", "race_records.json")

def get_race_records():
    if not os.path.exists(get_race_records_path()):
        return {}
    with open(get_race_records_path(), "r") as f:
        records = json.load(f)
    return records[mode]

def update_race_record_if_faster(record):
    # Debug log
    print(f"Updating race record if faster at path: {get_race_records_path()}, record: {record}")
    if not os.path.exists(get_race_records_path()):
        records = {}
    else:
        with open(get_race_records_path(), "r") as f:
            records = json.load(f)

    # Load all of the existing records as race record classes
    existing_records = []
    for record in records:
        existing_records.append(RaceRecord(**record))

    # Compare this run to the previous record at the same number of trials
    record_to_delete = None
    for i, existing_record in enumerate(existing_records):
        if existing_record.number_of_trials == record.number_of_trials:
            if existing_record.total_time_to_finish > record.total_time_to_finish:
                existing_records[i] = record
                break

    # Add the new record to the list
    existing_records.append(record)

    # Store the records
    with open(get_race_records_path(), "w") as f:
        json.dump(existing_records, f)


    

