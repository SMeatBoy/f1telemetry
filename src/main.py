import argparse

import f1telemetry.digest_orchestrator


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
    digest_orchestrator = f1telemetry.digest_orchestrator.DigestOrchestrator(args.output_path, args.save_packets,
                                                                             args.plot_ai, args.discord_url)
    if args.network:
        digest_orchestrator.digest_network(args.address, int(args.port))
    elif args.file:
        digest_orchestrator.digest_file(args.file)


if __name__ == '__main__':
    main()
