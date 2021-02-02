import multiprocessing
import pickle
import socket
import sys

import f1_2020_telemetry.packets

import f1telemetry.session


class DigestOrchestrator:

    def __init__(self, output_path, save_packets, plot_ai, discord_url=""):
        self.output_path = output_path
        self.save_packets = save_packets
        self.plot_ai = plot_ai
        self.discord_url = discord_url
        self.queue_packets = multiprocessing.Queue()
        self.queue_sessions = multiprocessing.Queue()
        self.is_unpacked = False

    def proc_file(self, filename):
        with open(filename, 'rb') as f:
            if filename.endswith('.pkl'):
                packets = pickle.load(f)
                for packet in packets:
                    self.queue_packets.put(packet)
                self.queue_packets.put('DONE')
            else:
                while True:
                    try:
                        r = pickle.load(f)
                        self.queue_packets.put(r[2])
                    except EOFError:
                        self.queue_packets.put('DONE')
                        break

    def proc_socket(self, sock):
        while True:
            self.queue_packets.put(sock.recvfrom(1500)[0])

    def proc_digest(self):
        packet_digester = f1telemetry.session.PacketDigester(self.queue_sessions, self.save_packets, self.plot_ai)
        while True:
            msg = self.queue_packets.get()
            if msg == 'DONE':
                self.queue_sessions.put('DONE')
                if packet_digester.current_session is not None:
                    packet_digester.current_session.process_end(self.output_path, self.save_packets, self.plot_ai, "")
                break
            else:
                if self.is_unpacked:
                    packet_digester.digest(msg)
                else:
                    packet_digester.digest(f1_2020_telemetry.packets.unpack_udp_packet(msg))

    def proc_session_end(self):
        while True:
            s = self.queue_sessions.get()
            if s == 'DONE':
                break
            s.process_end(self.output_path, self.save_packets, self.plot_ai, self.discord_url)

    def digest_network(self, address, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error as msg:
            print('Failed to create socket. Error Code : {} Message  {}'.format(msg[0], msg[1]))
            sys.exit()
        try:
            s.bind((address, port))
        except socket.error as msg:
            print('Bind failed. Error Code : {} Message  {}'.format(msg[0], msg[1]))
            sys.exit()

        p_socket = multiprocessing.Process(target=self.proc_socket, args=(s,))
        p_socket.start()
        p_digest = multiprocessing.Process(target=self.proc_digest, args=())
        p_digest.start()
        p_session_end = multiprocessing.Process(target=self.proc_session_end, args=())
        p_session_end.start()
        try:
            p_socket.join()
            p_digest.join()
            p_session_end.join()
        except KeyboardInterrupt:
            print('waiting until all received packets are digested...')
            s.close()
            p_socket.close()
            self.queue_packets.put('DONE')
            self.queue_sessions.put('DONE')
            print('closed socket')
            p_digest.join()
            p_session_end.join()
            print('digested received packets. bye')

    def digest_file(self, filename):
        if filename.endswith('.pkl'):
            self.is_unpacked = True
        if self.save_packets:
            print("not saving packets, they're already in a separate .pkl file")
            self.save_packets = False
        p_file = multiprocessing.Process(target=self.proc_file, args=(filename,))
        p_file.start()
        p_digest = multiprocessing.Process(target=self.proc_digest,
                                           args=())
        p_digest.start()
        p_session_end = multiprocessing.Process(target=self.proc_session_end,
                                                args=())
        p_session_end.start()
        p_file.join()
        p_digest.join()
        p_session_end.join()
