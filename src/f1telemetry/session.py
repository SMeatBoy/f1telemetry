import datetime
import os
import pickle
import time as time_module

import matplotlib
import matplotlib.gridspec
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np

import f1_2020_telemetry.packets

import f1telemetry.lap
import f1telemetry.participant
import f1telemetry.sessiontype
import f1telemetry.team
import f1telemetry.tracks
import f1telemetry.discord_automation

teams = [
    f1telemetry.team.Team('Mercedes', 0, '#00D2BE'),
    f1telemetry.team.Team('Ferrari', 1, '#FF2800'),
    f1telemetry.team.Team('Red Bull Racing', 2, '#0600EF'),
    f1telemetry.team.Team('Williams', 3, '#0082FA'),
    f1telemetry.team.Team('Racing Point', 4, '#F596C8'),
    f1telemetry.team.Team('Renault', 5, '#FFF500'),
    f1telemetry.team.Team('Alpha Tauri', 6, '#C8C8C8'),
    f1telemetry.team.Team('Haas', 7, '#787878'),
    f1telemetry.team.Team('McLaren', 8, '#FF8700'),
    f1telemetry.team.Team('ART Grand Prix', 70, '#B4B3B4'),
    f1telemetry.team.Team('Campos Racing', 71, '#EBC110'),
    f1telemetry.team.Team('Carlin', 72, '#243EF6'),
    f1telemetry.team.Team('Charouz Racing System', 73, '#84020A'),
    f1telemetry.team.Team('DAMS', 74, '#0ED4FA'),
    f1telemetry.team.Team('UNI-Virtuosi Racing', 75, '#FBEC20'),
    f1telemetry.team.Team('MP Motorsport', 76, '#F7401A'),
    f1telemetry.team.Team('PREMA Cacing', 77, '#E80309'),
    f1telemetry.team.Team('Trident', 78, '#0E1185'),
    f1telemetry.team.Team('BWT HWA Racelab', 79, '#FCB9E5'),
    f1telemetry.team.Team('Hitech Grand Prix', 80, '#E8E8E8'),
]

tyre_colors = {
    15: "#FFFFFF",
    16: "#FF2D2C",
    17: "#FFD318",
    18: "#FFFFFF",
    7: "#3AC82C",
    8: "#4491D2",
    24: "#FF2D2C",
    25: "#FFD318",
    26: "#FFFFFF",
}

tyre_names = {
    11: "SS",
    12: "S",
    13: "M",
    14: "H",
    15: "W",
    16: "C5",
    17: "C4",
    18: "C3",
    19: "C2",
    20: "C1",
    7: "Inter",
    8: "Wet",
}


def get_line_attributes(used_team_ids, team_id):
    color = 'green'
    line_style = '-'
    marker = 'o'
    for t in teams:
        if t.uid == team_id:
            color = t.color
            if t.uid in used_team_ids:
                line_style = '--'
                marker = '*'
            else:
                used_team_ids.append(t.uid)
            break
    return color, line_style, marker


class Session:

    def __init__(self, session_packet):
        self.session_type = session_packet.sessionType
        self.uid = session_packet.header.sessionUID
        self.participants = []
        self.best_lap_driver = []
        self.best_lap_time = []
        self.track_id = session_packet.trackId
        self.track_length = session_packet.trackLength
        self.total_laps = session_packet.totalLaps
        self.online = True if session_packet.networkGame == 1 else False
        self.packets = []

    def plot_fastest_lap_distance(self, output_path, time=None, plot_fastest_bot=False):
        fig = plt.figure()
        fig.suptitle('{} - {}: Best Lap Telemetry - Distance (m)'.format(f1telemetry.tracks.Tracks(self.track_id).name,
                                                                         f1telemetry.sessiontype.SessionType(
                                                                             self.session_type).pretty_name()))
        gs = matplotlib.gridspec.GridSpec(6, 1, left=0.04, right=0.99, bottom=0.03, top=0.95)
        axs = [fig.add_subplot(gs[0, :])]
        axs.append(fig.add_subplot(gs[1, :], sharex=axs[0]))
        axs.append(fig.add_subplot(gs[2:5, :], sharex=axs[0]))
        axs.append(fig.add_subplot(gs[5, :], sharex=axs[0]))
        for ax in axs:
            ax.grid(True)
            ax.xaxis.set_tick_params(which='both', labelbottom=True)
        axs[0].set_xlim(0, self.track_length)
        axs[0].set_ylabel('Throttle')
        axs[1].set_ylabel('Brake')
        axs[2].set_ylabel('Speed (km/h)')
        axs[2].set_ylim(0, 350)
        axs[2].yaxis.set_minor_locator(matplotlib.ticker.MultipleLocator(10))
        axs[2].yaxis.grid(True, 'minor', linestyle='--', color='#E0E0E0')
        axs[3].set_ylabel('Steer (°)')
        used_team_ids = []
        fastest_bot_race_number = 0
        fastest_bot_time = 0
        for participant in self.participants:
            if participant.data.aiControlled == 1:
                if fastest_bot_time == 0:
                    fastest_bot_time = participant.best_lap_time
                    fastest_bot_race_number = participant.data.raceNumber
                elif participant.best_lap_time < fastest_bot_time:
                    fastest_bot_time = participant.best_lap_time
                    fastest_bot_race_number = participant.data.raceNumber
        for participant in self.participants:
            if participant.best_lap_time != 0:
                if participant.data.aiControlled == 0 or \
                        (participant.data.raceNumber == fastest_bot_race_number and plot_fastest_bot):
                    hotlap_indices = participant.laps[participant.best_lap_index].get_hotlap_indices()
                    fastest_hotlap_index = hotlap_indices[0]
                    for index in hotlap_indices:
                        if participant.laps[participant.best_lap_index].time[index[1]] < \
                                participant.laps[participant.best_lap_index].time[fastest_hotlap_index[1]]:
                            fastest_hotlap_index = index
                    for i in range(fastest_hotlap_index[0], fastest_hotlap_index[1]):
                        if participant.laps[participant.best_lap_index].distance[i] > \
                                participant.laps[participant.best_lap_index].distance[i + 1]:
                            fastest_hotlap_index = (fastest_hotlap_index[0], i)
                            break
                    color, line_style, marker = get_line_attributes(used_team_ids, participant.data.teamId)
                    axs[0].plot(
                        participant.laps[participant.best_lap_index].distance[
                        fastest_hotlap_index[0]:fastest_hotlap_index[1]],
                        participant.laps[participant.best_lap_index].telemetry.throttle[
                        fastest_hotlap_index[0]:fastest_hotlap_index[1]],
                        label=participant.data.raceNumber, color=color, linestyle=line_style)
                    axs[1].plot(
                        participant.laps[participant.best_lap_index].distance[
                        fastest_hotlap_index[0]:fastest_hotlap_index[1]],
                        participant.laps[participant.best_lap_index].telemetry.brake[
                        fastest_hotlap_index[0]:fastest_hotlap_index[1]],
                        label=participant.data.raceNumber, color=color, linestyle=line_style)
                    axs[2].plot(
                        participant.laps[participant.best_lap_index].distance[
                        fastest_hotlap_index[0]:fastest_hotlap_index[1]],
                        participant.laps[participant.best_lap_index].telemetry.speed[
                        fastest_hotlap_index[0]:fastest_hotlap_index[1]],
                        label=participant.data.raceNumber, color=color, linestyle=line_style)
                    axs[3].plot(
                        participant.laps[participant.best_lap_index].distance[
                        fastest_hotlap_index[0]:fastest_hotlap_index[1]],
                        participant.laps[participant.best_lap_index].telemetry.steer[
                        fastest_hotlap_index[0]:fastest_hotlap_index[1]],
                        label=participant.data.raceNumber, color=color, linestyle=line_style)
        axs[2].legend(loc='lower left')
        file_name = self.save_fig(fig, output_path, (21, 9), time)
        plt.close(fig)
        return file_name

    def plot_race_summary(self, output_path, time=None):
        used_team_ids = []
        fig = plt.figure()
        fig.suptitle(
            '{} - {}'.format(f1telemetry.tracks.Tracks(self.track_id).name,
                             f1telemetry.sessiontype.SessionType(self.session_type).pretty_name()),
            fontsize=20)
        gs = fig.add_gridspec(20, 1, left=0.03, right=0.99, bottom=0.03, top=0.93, hspace=1.3)

        num_participants = 0
        for p in self.participants:
            if p.data.raceNumber != 0:
                num_participants += 1
        ax0 = fig.add_subplot(gs[0:9, :])
        ax0.set_title('Car Positions')
        ax0.grid(True)
        ax0.set_ylim(num_participants + 0.5, 0.5)
        ax0.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(1))
        ax0.yaxis.set_minor_locator(matplotlib.ticker.MultipleLocator(1))
        ax0.yaxis.grid(True, 'minor', linestyle='--', color='#E0E0E0')

        ax2 = fig.add_subplot(gs[11:, :], sharex=ax0)
        ax2.set_title('Lap Times')
        ax2.set_xlim(0, self.total_laps)
        ax2.grid(True)
        formatter = matplotlib.ticker.FuncFormatter(
            lambda seconds, x: time_module.strftime('%-M:%S', time_module.gmtime(seconds)))
        ax2.yaxis.set_major_formatter(formatter)
        ax2.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(2))
        ax2.yaxis.set_minor_locator(matplotlib.ticker.MultipleLocator(0.5))
        ax2.yaxis.grid(True, 'minor', linestyle='--', color='#E0E0E0')

        for p in self.participants:
            color, line_style, marker = get_line_attributes(used_team_ids, p.data.teamId)
            if p.data.aiControlled == 0:
                ax2.plot(range(1, len(p.laps)), [l.total_time for l in p.laps[:-1]],
                         color=color,
                         linestyle=line_style, marker=marker)

            if p.result_status == 3:
                positions = [p.grid_position]
                for current_lap in p.laps[:p.num_laps - 1]:
                    if len(current_lap.car_position) != 0:
                        positions.append(current_lap.car_position[-1])
                positions.append(p.finishing_position)
            elif p.result_status == 4:
                positions = [p.grid_position]
                for current_lap in p.laps[:p.num_laps]:
                    if len(current_lap.car_position) != 0:
                        positions.append(current_lap.car_position[-1])
                positions.append(p.finishing_position)
            else:
                positions = []
                for current_lap in p.laps[:p.current_lap_num]:
                    if len(current_lap.car_position) != 0:
                        positions.append(current_lap.car_position[-1])
            ax0.plot(range(0, len(positions)), positions, label=p.data.raceNumber, color=color,
                     linestyle=line_style, marker=marker)

        ax1 = fig.add_subplot(gs[9:11, :], sharex=ax0)
        self.subplot_tyre_stints(ax1)

        fig.legend(bbox_to_anchor=(.1, 0.96, .85, 0), loc='upper left', ncol=num_participants, mode="expand",
                   borderaxespad=0.)
        file_name = self.save_fig(fig, output_path, (16, 18), time)
        plt.close(fig)
        return file_name

    def subplot_tyre_stints(self, ax):
        human_participants = [p for p in self.participants if p.data.aiControlled == 0]
        ax.set_title('Tyre Stints')
        ax.set_yticks(np.arange(len(human_participants)))
        ax.xaxis.grid(True, zorder=0)
        ax.set_yticklabels([p.data.raceNumber for p in human_participants])
        for p, i in zip(human_participants, range(len(human_participants))):
            pit_laps = [lap.lap_num for lap in p.laps if lap.lap_num != 0 and lap.pit_status[-1] == 1]
            if p.tyre_stints_actual:
                tyre_stints_actual = [t for t in p.tyre_stints_actual if t != 0]
                tyre_stints_visual = [t for t in p.tyre_stints_visual if t != 0]
            else:
                tyre_stints_actual = [p.laps[0].tyre_compound_actual]
                tyre_stints_visual = [p.laps[0].tyre_compound_visual]
                for pit_lap in pit_laps:
                    tyre_stints_actual.append(p.laps[pit_lap - 1].tyre_compound_actual)
                    tyre_stints_visual.append(p.laps[pit_lap - 1].tyre_compound_visual)
                tyre_stints_actual.append(p.laps[-1].tyre_compound_actual)
                tyre_stints_visual.append(p.laps[-1].tyre_compound_visual)
            ax.barh(i, min(self.total_laps, len(p.laps)), color=tyre_colors[tyre_stints_visual[-1]], align='center',
                    zorder=3,
                    height=0.6)
            if not pit_laps:
                ax.annotate(tyre_names[tyre_stints_actual[-1]],
                            (min(self.total_laps, len(p.laps)) / 2, i),
                            ha='center', va='center', zorder=4)
            else:
                ax.annotate(tyre_names[tyre_stints_actual[-1]],
                            (((min(self.total_laps, len(p.laps)) - pit_laps[-1]) / 2 + pit_laps[-1]), i),
                            ha='center', va='center', zorder=4)
            for j in range(len(pit_laps) - 1, -1, -1):
                ax.barh(i, pit_laps[j] + (self.total_laps / 1000), color='black', align='center', zorder=3,
                        height=0.6)
                ax.barh(i, pit_laps[j] - (self.total_laps / 1000), color=tyre_colors[tyre_stints_visual[j]],
                        align='center',
                        zorder=3, height=0.6)
                if j == 0:
                    ax.annotate(tyre_names[tyre_stints_actual[j]], (pit_laps[j] / 2, i), ha='center', va='center',
                                zorder=4)
                else:
                    ax.annotate(tyre_names[tyre_stints_actual[j]],
                                (((pit_laps[j] - pit_laps[j - 1]) / 2 + pit_laps[j - 1]), i),
                                ha='center', va='center', zorder=4)

    def save_fig(self, fig, output_path, aspect_ratio, time=None):
        fig.set_size_inches(aspect_ratio)
        if time is not None:
            file_name = '{}_{}_{}-{}.svg'.format(time.strftime('%Y-%m-%d'), self.uid,
                                                 f1telemetry.tracks.Tracks(self.track_id).name,
                                                 f1telemetry.sessiontype.SessionType(
                                                     self.session_type).pretty_name())

        else:
            file_name = '{}_{}-{}.svg'.format(self.uid, f1telemetry.tracks.Tracks(self.track_id).name,
                                              f1telemetry.sessiontype.SessionType(
                                                  self.session_type).pretty_name())
        fig.savefig(os.path.join(output_path, file_name), format='svg', dpi=300)
        return file_name

    def process_end(self, output_path, save_packets, plot_ai, discord_url):
        time = datetime.datetime.now()
        file_name = ""
        if self.session_type == f1telemetry.sessiontype.SessionType.R:
            file_name = self.plot_race_summary(output_path, time)
        elif self.session_type == f1telemetry.sessiontype.SessionType.Q_Short:
            file_name = self.plot_fastest_lap_distance(output_path, time, plot_ai)
        if save_packets:
            with open(os.path.join(output_path,
                                   '{}_{}_{}-{}.pkl'.format(time.strftime('%Y-%m-%d'), self.uid,
                                                            f1telemetry.tracks.Tracks(self.track_id).name,
                                                            f1telemetry.sessiontype.SessionType(
                                                                self.session_type).pretty_name())), 'wb') as f:
                pickle.dump(self.packets, f)
        if discord_url and file_name and self.online:
            f1telemetry.discord_automation.upload_to_webhook(discord_url, os.path.join(output_path, file_name),
                                                             '{}-{}.svg'.format(
                                                                 f1telemetry.tracks.Tracks(self.track_id).name,
                                                                 f1telemetry.sessiontype.SessionType(
                                                                     self.session_type).pretty_name()))
        print('{} digested session end: {} {}-{}'.format(datetime.datetime.now().strftime('%H:%M:%S.%f'),
                                                         self.uid,
                                                         f1telemetry.tracks.Tracks(self.track_id).name,
                                                         f1telemetry.sessiontype.SessionType(
                                                             self.session_type).pretty_name()))
        return file_name


class PacketDigester:

    def __init__(self, queue, save_packets=False, store_ai_data=False):
        self.current_session = None
        self.current_session_uid = 0
        self.current_session_time = 0
        self.current_frame_identifier = -1
        self.current_packets = [None, None, None, None]
        self.queue = queue
        self.save_packets = save_packets
        self.store_ai_data = store_ai_data

    def digest(self, packet):
        if isinstance(packet, f1_2020_telemetry.packets.PacketSessionData_V1) \
                and self.current_session_uid != packet.header.sessionUID:
            self.digest_packet_session_data(packet)
            if self.save_packets:
                self.current_session.packets.append(packet)
        elif packet.header.sessionUID != 0 and packet.header.sessionUID == self.current_session_uid:
            if self.save_packets:
                self.current_session.packets.append(packet)
            if packet.header.packetId in [0, 2, 6, 7]:
                if packet.header.frameIdentifier != self.current_frame_identifier:
                    self.current_frame_identifier = packet.header.frameIdentifier
                    if None not in self.current_packets:
                        self.digest_packet_lap_data(self.current_packets[1])
                        self.digest_packet_car_telemetry(self.current_packets[2])
                        self.digest_packet_car_status(self.current_packets[3])
                    self.current_packets = [None, None, None, None]
                if packet.header.packetId == 0:
                    self.current_packets[0] = packet
                elif packet.header.packetId == 2:
                    self.current_packets[1] = packet
                elif packet.header.packetId == 6:
                    self.current_packets[2] = packet
                elif packet.header.packetId == 7:
                    self.current_packets[3] = packet
            if isinstance(packet, f1_2020_telemetry.packets.PacketParticipantsData_V1) \
                    and len(self.current_session.participants) == 0:
                return self.digest_packet_participants(packet)
            elif isinstance(packet, f1_2020_telemetry.packets.PacketEventData_V1):
                return self.digest_packet_event(packet)
            elif isinstance(packet, f1_2020_telemetry.packets.PacketFinalClassificationData_V1):
                return self.digest_packet_final_classification(packet)
        elif packet.header.sessionUID == 0 \
                and isinstance(packet, f1_2020_telemetry.packets.PacketFinalClassificationData_V1) \
                and packet.header.frameIdentifier >= self.current_frame_identifier:
            if self.save_packets:
                self.current_session.packets.append(packet)
            return self.digest_packet_final_classification(packet)

    def digest_packet_session_data(self, packet):
        self.current_session_uid = packet.header.sessionUID
        self.current_session = Session(packet)
        self.current_session.packets = []
        print('{} received session start: {} {}-{}'.format(datetime.datetime.now().strftime('%H:%M:%S.%f'),
                                                           self.current_session.uid,
                                                           f1telemetry.tracks.Tracks(
                                                               self.current_session.track_id).name,
                                                           f1telemetry.sessiontype.SessionType(
                                                               self.current_session.session_type).pretty_name()))

    def digest_packet_participants(self, packet):
        for p in packet.participants:
            if p.raceNumber != 0:
                self.current_session.participants.append(f1telemetry.participant.Participant(p))

    def digest_packet_lap_data(self, packet):
        for lapData, p in zip(packet.lapData[:len(self.current_session.participants)],
                              self.current_session.participants):
            if lapData.currentLapNum != 0 and lapData.resultStatus > 0:
                p.result_status = lapData.resultStatus
                if lapData.currentLapNum != p.current_lap_num:
                    if p.current_lap_num >= 1:
                        p.laps[-1].total_time = lapData.lastLapTime
                        if p.best_lap_time == 0 or p.best_lap_time > lapData.lastLapTime:
                            p.best_lap_time = lapData.lastLapTime
                            p.best_lap_index = p.current_lap_num - 1
                        p.laps[p.current_lap_num - 1].lap_num = p.current_lap_num
                    p.laps.append(f1telemetry.lap.Lap())
                    p.current_lap_num = lapData.currentLapNum
                    while p.current_lap_num > len(p.laps):
                        p.laps.append(f1telemetry.lap.Lap())
                if p.data.aiControlled == 0 or (self.store_ai_data and self.current_session.session_type != 12):
                    p.laps[p.current_lap_num - 1].distance.append(lapData.lapDistance)
                    p.laps[p.current_lap_num - 1].time.append(lapData.currentLapTime)
                p.laps[p.current_lap_num - 1].driver_status.append(lapData.driverStatus)
                p.laps[p.current_lap_num - 1].pit_status.append(lapData.pitStatus)
                p.laps[p.current_lap_num - 1].car_position.append(lapData.carPosition)
        self.current_session_time = packet.header.sessionTime

    def digest_packet_car_telemetry(self, packet):
        for carTelemetryData, p in zip(
                packet.carTelemetryData[:len(self.current_session.participants)],
                self.current_session.participants):
            if p.result_status > 0 and (p.data.aiControlled == 0 or self.store_ai_data):
                p.laps[p.current_lap_num - 1].telemetry.speed.append(
                    carTelemetryData.speed)
                p.laps[p.current_lap_num - 1].telemetry.throttle.append(
                    carTelemetryData.throttle)
                p.laps[p.current_lap_num - 1].telemetry.steer.append(
                    carTelemetryData.steer)
                p.laps[p.current_lap_num - 1].telemetry.brake.append(
                    carTelemetryData.brake)
                p.laps[p.current_lap_num - 1].telemetry.clutch.append(
                    carTelemetryData.clutch)
                p.laps[p.current_lap_num - 1].telemetry.gear.append(
                    carTelemetryData.gear)
                p.laps[p.current_lap_num - 1].telemetry.engine_rpm.append(
                    carTelemetryData.engineRPM)
                p.laps[p.current_lap_num - 1].telemetry.drs.append(carTelemetryData.drs)
                p.laps[p.current_lap_num - 1].telemetry.rev_lights_percent.append(
                    carTelemetryData.revLightsPercent)

    def digest_packet_car_status(self, packet):
        for carStatusData, p in zip(
                packet.carStatusData[:len(self.current_session.participants)],
                self.current_session.participants):
            if p.result_status > 0 and (p.data.aiControlled == 0 or self.store_ai_data):
                p.laps[p.current_lap_num - 1].tyre_compound_actual = carStatusData.actualTyreCompound
                p.laps[p.current_lap_num - 1].tyre_compound_visual = carStatusData.visualTyreCompound
                p.laps[p.current_lap_num - 1].tyre_age_laps = carStatusData.tyresAgeLaps

    def digest_packet_event(self, packet):
        if packet.eventStringCode.decode() == 'SEND':
            if self.current_session.session_type == 12:
                self.process_session_end()

    def digest_packet_final_classification(self, packet):
        for classificationData, p, in zip(
                packet.classificationData[:len(self.current_session.participants)],
                self.current_session.participants, ):
            p.finishing_position = classificationData.position
            p.num_laps = classificationData.numLaps
            p.grid_position = classificationData.gridPosition
            p.points = classificationData.points
            p.num_pit_stops = classificationData.numPitStops
            p.result_status = classificationData.resultStatus
            p.best_lap_time = classificationData.bestLapTime
            p.total_race_time = classificationData.totalRaceTime
            p.total_penalties_time = classificationData.penaltiesTime
            p.num_penalties = classificationData.numPenalties
            p.num_tyre_stints = classificationData.numTyreStints
            for i in range(p.num_tyre_stints):
                p.tyre_stints_actual.append(classificationData.tyreStintsActual[i])
                p.tyre_stints_visual.append(classificationData.tyreStintsVisual[i])
        self.process_session_end()

    def process_session_end(self):
        print('{} received session end: {} {}-{}'.format(datetime.datetime.now().strftime('%H:%M:%S.%f'),
                                                         self.current_session.uid,
                                                         f1telemetry.tracks.Tracks(self.current_session.track_id).name,
                                                         f1telemetry.sessiontype.SessionType(
                                                             self.current_session.session_type).pretty_name()))
        self.queue.put(self.current_session)
        self.current_session = None
        self.current_session_uid = 0
        self.current_session_time = 0
        self.current_frame_identifier = -1
        self.current_packets = [None, None, None, None]
