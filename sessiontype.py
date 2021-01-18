import enum


class SessionType(enum.IntEnum):
    Unknown = 0
    FP1 = 1
    FP2 = 2
    FP3 = 3
    FP_Short = 4
    Q1 = 5
    Q2 = 6
    Q3 = 7
    Q_Short = 8
    Q_OneShot = 9
    R = 10
    R2 = 11
    TimeTrial = 12

    def pretty_name(self):
        if self.value in [SessionType.R, SessionType.R2]:
            name_session = "Race"
        elif self.value in [SessionType.Q_OneShot, SessionType.Q_Short]:
            name_session = "Qualifying"
        elif self.value == SessionType.Q1:
            name_session = "Qualifying 1"
        elif self.value == SessionType.Q2:
            name_session = "Qualifying 2"
        elif self.value == SessionType.Q3:
            name_session = "Qualifying 3"
        else:
            name_session = SessionType(self.value).name
        return name_session

