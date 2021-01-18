import argparse
import multiprocessing
import pickle
import socket
import sys

from f1_2020_telemetry.packets import *

import session


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


# def read_packets_from_file(filename):
#     record = []
#     with open(filename, 'rb') as f:
#         while True:
#             try:
#                 r = pickle.load(f)
#                 record.append(r[2])
#             except EOFError:
#                 break
#     # packets = []
#     # for r in record:
#     # packets.append(r)
#     # packets = record[0]
#     return record


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


def proc_digest(queue_packets, queue_sessions, save_packets=False,is_unpacked=False):
    packet_digester = session.PacketDigester(queue_sessions, save_packets)
    i = 0
    while True:
        msg = queue_packets.get()
        if msg == 'DONE':
            queue_sessions.put('DONE')
            if packet_digester.current_session is not None:
                packet_digester.current_session.process_end(save_packets)
            break
        else:
            if is_unpacked:
                packet_digester.digest(msg)
            else:
                packet_digester.digest(unpack_udp_packet(msg))


def proc_session_end(queue, save_packets=False):
    while True:
        s = queue.get()
        if s == 'DONE':
            break
        s.process_end(save_packets)


def digest_packets_from_socket(port, address, save_packets):
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
    p_digest = multiprocessing.Process(target=proc_digest, args=(queue_packets, queue_sessions, save_packets))
    p_digest.start()
    p_session_end = multiprocessing.Process(target=proc_session_end, args=(queue_sessions, save_packets))
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


def digest_packets_from_file(filename):
    queue_packets = multiprocessing.Queue()
    queue_sessions = multiprocessing.Queue()

    if filename.endswith('.pkl'):
        save_packets = False
        is_unpacked = True
    else:
        # save_packets = True
        save_packets = False
        is_unpacked = False
    p_file = multiprocessing.Process(target=proc_file, args=(filename, queue_packets))
    p_file.start()
    p_digest = multiprocessing.Process(target=proc_digest, args=(queue_packets, queue_sessions, save_packets,is_unpacked))
    p_digest.start()
    p_session_end = multiprocessing.Process(target=proc_session_end, args=(queue_sessions, save_packets))
    p_session_end.start()
    # proc_digest(queue_packets,queue_sessions,save_packets,is_unpacked)
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
    parser.add_argument('--save_packets', help='Save packets of session to file', default=False, action='store_true')
    parser.add_argument('-o', '--output_path', help='Directory to place files in', default='.', required=False)
    args = parser.parse_args()
    if args.network:
        digest_packets_from_socket(int(args.port), args.address, args.save_packets)
    elif args.file:
        digest_packets_from_file(args.file)


if __name__ == '__main__':
    main()
