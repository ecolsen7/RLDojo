from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ValidationError
import os


class RaceRecord(BaseModel):
    number_of_trials: int
    time_to_finish: float
    split_times: List[float] = Field(default_factory=list)
    
    def update_split_time(self, split_index: int, split_time: float):
        if split_index >= len(self.split_times):
            self.split_times.append(split_time)
        else:
            self.split_times[split_index] = split_time

    def get_split_time(self, split_index: int) -> Optional[float]:
        if split_index >= len(self.split_times):
            return None
        return self.split_times[split_index]

class RaceRecords(BaseModel):
    records: Dict[int, RaceRecord]
    
    def set_record(self, race_record: RaceRecord):
        self.records[race_record.number_of_trials] = race_record

    def get_previous_record_data(self, number_of_trials: int) -> Optional[RaceRecord]:
        if number_of_trials not in self.records:
            return None
        return self.records[number_of_trials]

    def get_previous_record(self, number_of_trials: int) -> Optional[float]:
        previous_record_data = self.get_previous_record_data(number_of_trials)
        if previous_record_data is None:
            return None
        return previous_record_data.time_to_finish

def _get_records_base_path():
    appdata_path = os.path.expandvars("%APPDATA%")
    if not os.path.exists(os.path.join(appdata_path, "RLBot", "Dojo")):
        os.makedirs(os.path.join(appdata_path, "RLBot", "Dojo"))
    return os.path.join(appdata_path, "RLBot", "Dojo")

def _get_race_records_path():
    return os.path.join(_get_records_base_path(), "race_records.json")

def get_race_records() -> RaceRecords:
    if not os.path.exists(_get_race_records_path()):
        return RaceRecords(records={})
    with open(_get_race_records_path(), "r") as f:
        try:
            return RaceRecords.model_validate_json(f.read())
        except ValidationError:
            return RaceRecords(records={})

def store_race_records(records: RaceRecords):
    with open(_get_race_records_path(), "w") as f:
        f.write(records.model_dump_json())
