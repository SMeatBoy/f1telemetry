import argparse
import multiprocessing
import os
import pickle
import socket
import sys

import f1_2020_telemetry.packets

import f1telemetry.session


def remove_duplicate_session_types(sessions):
    has_duplicates = True
    while has_duplicates:
        has_duplicates = False
        for i in range(len(sessions) - 1, -1, -1):
            for j in range(i, -1, -1):
                if i != j and sessions[i].session_type == sessions[j].session_type:
                    del (sessions[j])
                    has_duplicates = True
    return sessions


def proc_file(filename, queue):
    with open(filename, 'rb') as f:
        if filename.endswith('.pkl'):
            packets = pickle.load(f)
            for packet in packets:
                queue.put(packet)
            queue.put('DONE')
        else:
            while True:
                try:
                    r = pickle.load(f)
                    queue.put(r[2])
                except EOFError:
                    queue.put('DONE')
                    break


def proc_socket(sock, queue):
    while True:
        queue.put(sock.recvfrom(1500)[0])


def proc_digest(queue_packets, queue_sessions, output_path, save_packets=False, is_unpacked=False, plot_ai=False):
    packet_digester = f1telemetry.session.PacketDigester(queue_sessions, save_packets, plot_ai)
    while True:
        msg = queue_packets.get()
        if msg == 'DONE':
            queue_sessions.put('DONE')
            if packet_digester.current_session is not None:
                packet_digester.current_session.process_end(output_path, save_packets)
            break
        else:
            if is_unpacked:
                packet_digester.digest(msg)
            else:
                packet_digester.digest(f1_2020_telemetry.packets.unpack_udp_packet(msg))


def proc_session_end(queue, output_path, save_packets=False, plot_ai=False, discord_url=""):
    while True:
        s = queue.get()
        if s == 'DONE':
            break
        s.process_end(output_path, save_packets, plot_ai, discord_url)


def digest_packets_from_socket(port, address, output_path, save_packets, plot_ai, discord_url):
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

    queue_packets = multiprocessing.Queue()
    queue_sessions = multiprocessing.Queue()
    p_socket = multiprocessing.Process(target=proc_socket, args=(s, queue_packets))
    p_socket.start()
    p_digest = multiprocessing.Process(target=proc_digest,
                                       args=(queue_packets, queue_sessions, output_path, save_packets, False, plot_ai))
    p_digest.start()
    p_session_end = multiprocessing.Process(target=proc_session_end,
                                            args=(queue_sessions, output_path, save_packets, plot_ai, discord_url))
    p_session_end.start()
    try:
        p_socket.join()
        p_digest.join()
        p_session_end.join()
    except KeyboardInterrupt:
        print('waiting until all received packets are digested...')
        s.close()
        p_socket.close()
        queue_packets.put('DONE')
        queue_sessions.put('DONE')
        print('closed socket')
        p_digest.join()
        p_session_end.join()
        print('digested received packets. bye')


def digest_packets_from_file(filename, output_path, save_packets, plot_ai, discord_url):
    queue_packets = multiprocessing.Queue()
    queue_sessions = multiprocessing.Queue()

    if filename.endswith('.pkl'):
        is_unpacked = True
        if save_packets:
            print("not saving packets, they're already in a separate .pkl file")
            save_packets = False
    else:
        is_unpacked = False
    p_file = multiprocessing.Process(target=proc_file, args=(filename, queue_packets))
    p_file.start()
    p_digest = multiprocessing.Process(target=proc_digest,
                                       args=(
                                           queue_packets, queue_sessions, output_path, save_packets, is_unpacked,
                                           plot_ai))
    p_digest.start()
    p_session_end = multiprocessing.Process(target=proc_session_end,
                                            args=(queue_sessions, output_path, save_packets, plot_ai, discord_url))
    p_session_end.start()
    p_file.join()
    p_digest.join()
    p_session_end.join()


def main():
    plot_ai = True if os.getenv('PLOT_AI') is not None else False
    save_packets = True if os.getenv('SAVE_PACKETS') is not None else False
    discord_url = os.getenv('DISCORD_URL', "")
    digest_packets_from_socket(20777, '0.0.0.0', '/results', save_packets, plot_ai, discord_url)


if __name__ == '__main__':
    main()
