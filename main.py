import argparse
import multiprocessing
import pickle
import socket
import sys

from f1_2020_telemetry.packets import *

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
    i = 0
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
                packet_digester.digest(unpack_udp_packet(msg))


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
                                            args=(queue_sessions, output_path, save_packets, discord_url))
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
                                            args=(queue_sessions, output_path, save_packets,plot_ai, discord_url))
    p_session_end.start()
    p_file.join()
    p_digest.join()
    p_session_end.join()


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('-n', '--network', help='Read packets from network connection', action='store_true')
    mode.add_argument('-f', '--file', help='Read packets from file', type=str, dest='file')
    parser.add_argument('-p', '--port', help='Port to listen to in. Network mode only', type=int)
    parser.add_argument('-a', '--address', help='IP Address to listen to in. Network mode only', type=str)
    parser.add_argument('--save-packets', help='Save packets of session to file', default=False, action='store_true')
    parser.add_argument('--plot-ai', help='Plot qualification lap of fastest AI driver', default=False,
                        action='store_true')
    parser.add_argument('-o', '--output-path', help='Directory to place files in', default='.', required=False)
    parser.add_argument('--discord-url', help='URL of Discord Webhook to post results to', default='', required=False)
    args = parser.parse_args()
    if args.network:
        digest_packets_from_socket(int(args.port), args.address, args.output_path, args.save_packets, args.plot_ai,
                                   args.discord_url)
    elif args.file:
        digest_packets_from_file(args.file, args.output_path, args.save_packets, args.plot_ai, args.discord_url)


if __name__ == '__main__':
    main()
