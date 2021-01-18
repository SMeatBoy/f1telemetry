from cartelemetry import CarTelemetry


class Lap:
    def __init__(self):
        self.telemetry = CarTelemetry()
        self.total_time = 0
        self.is_valid = 0
        self.lap_num = 0
        self.distance = []
        self.time = []
        self.car_position = []
        self.pit_status = []
        self.driver_status = []
        self.result_status = []
        self.tyre_compound_actual = 0
        self.tyre_compound_visual = 0
        self.tyre_age_laps = 0

    def get_hotlap_indices(self):
        hotlap_indices = []
        for lap_part_index in self.get_lap_part_indices():
            if all(driver_status == 1 for driver_status in self.driver_status[lap_part_index[0]:lap_part_index[1]]):
                hotlap_indices.append(lap_part_index)
        return hotlap_indices

    def get_lap_part_indices(self):
        indexes = [0]
        p = self.time[0]
        for i in range(len(self.time)):
            if self.time[i] < p - 1:
                indexes.append(i)
            p = self.time[i]
        indexes.append(len(self.time) - 1)
        indices = []
        for i in range(len(indexes) - 1):
            indices.append((indexes[i], indexes[i + 1]))
        return indices