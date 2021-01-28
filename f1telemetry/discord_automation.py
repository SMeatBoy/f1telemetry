import discord_webhook


def upload_to_webhook(url, file_path, file_name):
    webhook = discord_webhook.DiscordWebhook(url=url, username="Result Bot")
    with open(file_path) as f:
        webhook.add_file(file=f.read(), filename=file_name)
    response = webhook.execute()
    print(response)
