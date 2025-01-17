import json
import ctypes
import requests
import os
from threading import Thread
from datetime import datetime
from colorama import Fore, Back, Style, init
import discord

init()

done = 0
success = 0
failure = 0
skipped = 0

config_path = 'Config.json'
tokens_path = 'tokens.txt'

config_content = {
    "THREADS": 5,
    "APPS_TO_IGNORE": [1, 2, 3, 4, 5]
}

if not os.path.exists(config_path):
    with open(config_path, 'w', encoding='utf-8') as config_file:
        json.dump(config_content, config_file, indent=4)

if not os.path.exists(tokens_path):
    open(tokens_path, 'w').close()
    print("Required files have been created. Please restart it.")
    input("Press Enter to exit...")
    exit()

def load_token():
    with open(tokens_path, 'r') as file:
        token = file.readline().strip()
        if not token:
            print("Token is missing. Please add a valid token to 'tokens.txt'.")
            input("Press Enter to exit...")
            exit()
        return token

token = load_token()

class Cleaner:
    def __init__(self):
        self.config = json.load(open(config_path, 'r'))

    def update_console_title(self):
        global done, success, failure, skipped
        ctypes.windll.kernel32.SetConsoleTitleW(
            f"Done: {done} | Deauthorized: {success} | Failures: {failure} | Skipped: {skipped}"
        )

    def headers(self, token: str) -> dict:
        return {
            'authority': 'discord.com',
            'accept': '*/*',
            'authorization': token,
            'content-type': 'application/json',
            'origin': 'https://discord.com',
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'x-debug-options': 'bugReporterEnabled',
            'x-discord-locale': 'en-US',
            'x-super-properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6InVrLVVBIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMi4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIyLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmVyX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6Mjc1NTY1LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ==',
        }

    def fetch_apps(self, token: str) -> dict:
        global done, success, failure, skipped
        r = requests.get('https://discord.com/api/v9/oauth2/tokens', headers=self.headers(token))
        if r.ok:
            apps = r.json()
            print(f'Fetched {len(apps)} app(s)')
            return apps
        else:
            failure += 1
            self.update_console_title()
            print(f'Failed while getting authorized applications -> {r.json()}')
            return None

    def deauthorize_apps(self, token: str):
        global done, success, failure, skipped
        apps = self.fetch_apps(token)
        if apps:
            total_apps = len(apps)
            for index, app in enumerate(apps):
                if int(app['application']['id']) not in self.config['APPS_TO_IGNORE']:
                    r = requests.delete(f'https://discord.com/api/v9/oauth2/tokens/{app["id"]}', headers=self.headers(token))
                    if r.ok:
                        success += 1
                        print(f'Deauthorized the application {app["application"]["name"]} ({app["id"]}) [{index + 1}/{total_apps}]')
                    else:
                        failure += 1
                        print(r.text)
                else:
                    skipped += 1
                    print(f'Skipping {app["application"]["name"]} ({app["id"]})')
                self.update_console_title()
            done += 1
            self.update_console_title()

    def remove_friends(self, token: str):
        global done, success, failure, skipped
        headers = self.headers(token)
        r = requests.get('https://discord.com/api/v10/users/@me/relationships', headers=headers)
        if r.ok:
            friends = r.json()
            print(f'Fetched {len(friends)} friend(s)')
            for friend in friends:
                friend_id = friend['id']
                friend_name = friend['user']['username']
                r = requests.delete(f'https://discord.com/api/v10/users/@me/relationships/{friend_id}', headers=headers)
                if r.ok:
                    success += 1
                    print(f'Removed friend {friend_name} ({friend_id})')
                else:
                    failure += 1
                    print(f'Failed to remove friend {friend_name} ({friend_id}) -> {r.text}')
                self.update_console_title()
            done += 1
            self.update_console_title()
        else:
            failure += 1
            print(f'Failed to fetch friends list -> {r.text}')
            self.update_console_title()

def start_deauthorization(token: str):
    instance = Cleaner()
    thread = Thread(target=instance.deauthorize_apps, args=(token,))
    thread.start()
    thread.join()

def start_remove_friends(token: str):
    instance = Cleaner()
    thread = Thread(target=instance.remove_friends, args=(token,))
    thread.start()
    thread.join()

async def leave_servers(client: discord.Client):
    print(f'Fetched {len(client.guilds)} server(s)')
    for guild in client.guilds:
        try:
            if guild.id not in whitelist:
                server = client.get_guild(guild.id)
                await server.leave()
                print(f"Leaving server: {guild.name}")
        except Exception as e:
            print(e)

client = discord.Client()
whitelist = []

@client.event
async def on_ready():
    await leave_servers(client)
    start_deauthorization(token)
    start_remove_friends(token)
    await client.close()

client.run(token, bot=False)
input("Done...!")
