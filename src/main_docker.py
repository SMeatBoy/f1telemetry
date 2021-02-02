import os

import f1telemetry.digest_orchestrator


def main():
    plot_ai = True if os.getenv('PLOT_AI') is not None else False
    save_packets = True if os.getenv('SAVE_PACKETS') is not None else False
    discord_url = os.getenv('DISCORD_URL', "")
    digest_orchestrator = f1telemetry.digest_orchestrator.DigestOrchestrator('/results', save_packets,
                                                                             plot_ai, discord_url)
    digest_orchestrator.digest_network('0.0.0.0', 20777)


if __name__ == '__main__':
    main()
