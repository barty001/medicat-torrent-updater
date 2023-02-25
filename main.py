#!/usr/bin/env python3
import json
import re
import sys
from typing import List, Optional

import tabulate
from bs4 import BeautifulSoup
import cfscrape
import qbittorrentapi

import mail

scraper = cfscrape.create_scraper()  # returns a CloudflareScraper instance

MEDICAT_THREAD = "https://gbatemp.net/threads/medicat-usb-a-multiboot-linux-usb-for-pc-repair.361577/"


def request_thread(url: str):
    response = scraper.get(url)
    response.raise_for_status()

    # DEBUG
    with open('thread.html', 'w', encoding="utf8") as fp:
        fp.write(response.text)

    soup = BeautifulSoup(response.text, 'html.parser')
    return soup


def fake_request_thread(url: str):
    with open('thread.html', 'r', encoding="utf8") as fp:
        return BeautifulSoup(fp.read(), 'html.parser')


def get_thread_medicat_version(soup: BeautifulSoup) -> Optional[str]:
    return soup.find(string=re.compile(r"^v\d\d\.\d\d")).string


def get_magnet_link(soup: BeautifulSoup):
    return soup.find(string=re.compile(r"^magnet:\?")).string


def get_torrent_medicat_versions(qbt_client: qbittorrentapi.Client) -> List[str]:
    torrents: List[str] = [torrent.name for torrent in qbt_client.torrents_info()]
    medicat_versions: List[str] = []
    for torrent in torrents:
        version_match = re.search(r"v\d\d\.\d\d", torrent)
        if version_match:
            medicat_versions.append(version_match[0])

    return medicat_versions


def get_torrent_status(qbt_client: qbittorrentapi.Client) -> str:
    status = ""
    for torrent in qbt_client.torrents_info():
        status += f'- {torrent.hash[-6:]}: {torrent.name} ({torrent.state})\r\n'

    return status


def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def get_medicat_torrent_status_html(qbt_client: qbittorrentapi.Client) -> str:
    table_style = "padding: 3px; border: 1px solid black; border-collapse: collapse;"
    table_headers = ["Name", "Size", "State", "Ratio", "Amount Uploaded", "Seeds", "Leechs"]
    torrent_data = []

    for torrent in qbt_client.torrents_info(sort="name"):
        if "medicat" in torrent.get("name", "").lower():
            torrent_data.append(
                [torrent.name, sizeof_fmt(torrent.size), torrent.state, torrent.ratio, sizeof_fmt(torrent.uploaded),
                 torrent.num_complete, f"{torrent.num_leechs} ({torrent.num_incomplete} total)"])

    table_html = tabulate.tabulate(torrent_data, headers=table_headers, tablefmt="html")
    # Ew, ich hasse HTML-E-Mails
    return table_html \
        .replace("<table>", f"<table style=\"{table_style}\">") \
        .replace("<th style=\"", f"<th style=\"{table_style}") \
        .replace("<th>", f"<th style=\"{table_style}\">") \
        .replace("<td style=\"", f"<td style=\"{table_style}") \
        .replace("<td>", f"<td style=\"{table_style}\">")


if __name__ == '__main__':
    with open("./config.json", "r", encoding="utf8") as fp:
        config = json.load(fp)

    _qbt_client = qbittorrentapi.Client(host=config["qbittorrent_host"],
                                        port=config["qbittorrent_port"],
                                        username=config["qbittorrent_username"],
                                        password=config["qbittorrent_password"])

    thread = request_thread(MEDICAT_THREAD)
    thread_version = get_thread_medicat_version(thread)
    thread_magnet_link = get_magnet_link(thread)

    if not thread_version or not thread_magnet_link:
        print("Error: Could not extract current version or magnet link. Exiting.")
        sys.exit(1)

    torrent_medicat_versions = get_torrent_medicat_versions(_qbt_client)
    torrent_medicat_versions.sort()

    if thread_version in torrent_medicat_versions:
        print(
            "Skip: Version {} is already in torrent ({})!".format(thread_version, ", ".join(torrent_medicat_versions)))
        sys.exit(0)

    print("-- Version {} is not yet in qBittorrent ({})!!".format(thread_version, ", ".join(torrent_medicat_versions)))
    print("-- Adding now...")
    resp = _qbt_client.torrents_add(urls=thread_magnet_link)
    print(resp)

    # Send mail
    mail.send_notification(thread_version, torrent_medicat_versions[-1], get_medicat_torrent_status_html(_qbt_client),
                           config["smtp_server"], config["smtp_username"], config["smtp_password"],
                           config["recipient_addresses"], config["sender_address"], config.get("sender_displayname"))
