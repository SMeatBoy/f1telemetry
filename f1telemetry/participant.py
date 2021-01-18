class Participant:

    def __init__(self, participant_data):
        self.data = participant_data
        self.laps = []
        self.grid_position = 0
        self.finishing_position = 0
        self.num_laps = 0
        self.current_lap_num = 0
        self.points = 0
        self.num_pit_stops = 0
        self.result_status = 0
        self.best_lap_time = 0
        self.best_lap_index = 0
        self.total_race_time = 0
        self.total_penalties_time = 0
        self.num_penalties = 0
        self.num_tyre_stints = 0
        self.tyre_stints = []