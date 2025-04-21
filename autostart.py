# -*- coding: utf-8 -*-
import requests
import json
from datetime import datetime
from urllib.parse import urlparse
import sys
from typing import Dict, Tuple, Optional, Any, List

BASE_URL = "http://restream.cdn-4k.cloud:80/stalker_portal"
MAC = "00:1A:79:AB:CD:EF"

def print_colored(text: str, color: str) -> None:
    colors = {
        "green": "\033[92m", "red": "\033[91m", "blue": "\033[94m",
        "yellow": "\033[93m", "cyan": "\033[96m", "magenta": "\033[95m"
    }
    print(f"{colors.get(color.lower(), '')}{text}\033[0m")

def get_headers(mac: str) -> Dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)",
        "Referer": f"http://localhost/stalker_portal/c/",
        "X-User-Agent": "Model: MAG254; Link: Ethernet",
        "Cookie": f"mac={mac}; stb_lang=en; timezone=Europe/Berlin",
        "Connection": "Keep-Alive", "Accept": "*/*",
    }

def get_token(session: requests.Session, base_url: str, mac: str) -> Optional[str]:
    url = f"{base_url}/portal.php?action=handshake&type=stb&token=&JsHttpRequest=1-xml"
    headers = get_headers(mac)
    try:
        res = session.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        token = res.json()['js']['token']
        print_colored(f"Token erhalten: {token}", "green")
        return token
    except Exception as e:
        print_colored(f"Fehler beim Token holen: {e}", "red")
        return None

def get_profile(session: requests.Session, base_url: str, token: str, mac: str) -> Optional[str]:
    url = f"{base_url}/portal.php?type=account_info&action=get_main_info&JsHttpRequest=1-xml"
    headers = get_headers(mac)
    headers["Authorization"] = f"Bearer {token}"
    try:
        res = session.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()['js']
            expiry = data.get('phone', 'Unbekannt')
            print_colored(f"MAC: {data.get('mac', 'Unbekannt')} – Abo endet: {expiry}", "green")
            return expiry
        return None
    except Exception as e:
        print_colored(f"Fehler beim Profilabruf: {e}", "red")
        return None

def get_channel_list(session: requests.Session, base_url: str, token: str, mac: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[int, str]]]:
    headers = get_headers(mac)
    headers["Authorization"] = f"Bearer {token}"
    try:
        url_genres = f"{base_url}/portal.php?type=itv&action=get_genres&JsHttpRequest=1-xml"
        res_genres = session.get(url_genres, headers=headers, timeout=10)
        group_info = {g['id']: g['title'] for g in res_genres.json().get('js', [])}
        url_channels = f"{base_url}/portal.php?type=itv&action=get_all_channels&JsHttpRequest=1-xml"
        res_channels = session.get(url_channels, headers=headers, timeout=10)
        channels_data = res_channels.json()['js']['data']
        return channels_data, group_info
    except Exception as e:
        print_colored(f"Fehler beim Laden der Kanäle: {e}", "red")
        return None, None

def save_channel_list(base_url: str, expiry: str, channels_data: List[Dict[str, Any]], group_info: Dict[int, str], mac: str) -> None:
    safe_url = base_url.replace("http://", "").replace("/", "_").replace(".", "_")
    expiry_clean = expiry.replace(" ", "_").replace(":", "-").replace("/", "-")
    filename = f"{safe_url}_Abo_bis_{expiry_clean}.m3u"
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write('#EXTM3U\n')
            file.write(f"#EXTINF:-1, Abo gültig bis {expiry}\n")
            for ch in channels_data:
                group_id = ch.get('tv_genre_id')
                group_name = group_info.get(group_id, "General")
                name = ch['name']
                logo = ch.get('logo', '')
                cmd_url = ch['cmds'][0]['url'].replace("ffmpeg ", "")
                file.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_name}",{name}\n{cmd_url}\n')
        print_colored(f"\n✅ Kanalliste gespeichert in: {filename}", "blue")
    except Exception as e:
        print_colored(f"Fehler beim Speichern: {e}", "red")

def main():
    try:
        session = requests.Session()
        session.cookies.set("mac", MAC)
        token = get_token(session, BASE_URL, MAC)
        if not token:
            return
        expiry = get_profile(session, BASE_URL, token, MAC)
        if not expiry:
            return
        channels_data, group_info = get_channel_list(session, BASE_URL, token, MAC)
        if channels_data and group_info:
            save_channel_list(BASE_URL, expiry, channels_data, group_info, MAC)
    except KeyboardInterrupt:
        print_colored("Abgebrochen vom Benutzer", "yellow")
        sys.exit(0)

if __name__ == "__main__":
    main()
