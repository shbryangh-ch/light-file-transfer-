#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
serve_offline.py — 在電腦上開一個本地 HTTPS 伺服器，讓手機透過同一個區域網路
（不需要連上網際網路，只要兩台裝置在同一個 WiFi / 熱點下）打開離線版接收頁面。

為什麼要 HTTPS？
    手機瀏覽器的相機權限（getUserMedia）只有在「安全來源」下才能使用：
    https、或是 localhost。單純用 http://電腦IP:port/ 手機瀏覽器會擋掉相機權限。
    所以這裡自動產生一份自我簽署憑證，讓連線走 https（手機第一次連線時
    會跳出「憑證不受信任」的警告，屬正常現象，選擇繼續 / 進階 / 仍要前往即可）。

用法：
    pip install cryptography
    python serve_offline.py

    接著手機連到跟這台電腦「同一個網路」（例如電腦開的個人熱點，
    完全不需要有網際網路連線），用瀏覽器打開程式印出來的網址即可。

需求：
    receiver_offline.html 要跟這支程式放在同一個資料夾。
"""

import http.server
import ssl
import socket
import os
import sys
import ipaddress
import datetime

CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"
PORT = 8443
HTML_FILE = "receiver_offline.html"


def get_local_ips():
    """列出這台電腦在區域網路上可能的 IP，方便使用者知道要輸入哪個網址。"""
    ips = set()
    hostname = socket.gethostname()
    try:
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if not ip.startswith("127.") and ":" not in ip:
                ips.add(ip)
    except Exception:
        pass
    # 額外用連線的方式抓一次（較準確，尤其多網卡時）
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    return sorted(ips) if ips else ["<找不到，請自行用 ipconfig / ifconfig 查詢>"]


def ensure_cert():
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        print("缺少 cryptography 套件，請先執行：pip install cryptography")
        sys.exit(1)

    print("首次執行，正在產生自我簽署憑證（僅這台電腦與手機之間使用）…")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "light-transfer.local")]
    )

    san_list = [x509.DNSName("localhost")]
    for ip in get_local_ips():
        try:
            san_list.append(x509.IPAddress(ipaddress.ip_address(ip)))
        except ValueError:
            pass
    san_list.append(x509.IPAddress(ipaddress.ip_address("127.0.0.1")))

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
        .sign(key, hashes.SHA256())
    )

    with open(KEY_FILE, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print("憑證已產生：{} / {}".format(CERT_FILE, KEY_FILE))


def main():
    if not os.path.isfile(HTML_FILE):
        print("找不到 {}，請確認這支程式跟接收頁面放在同一個資料夾。".format(HTML_FILE))
        sys.exit(1)

    ensure_cert()

    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.HTTPServer(("0.0.0.0", PORT), handler)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

    print("\n伺服器已啟動！")
    print("請確認手機跟這台電腦在『同一個網路』下（例如這台電腦開的個人熱點，")
    print("完全不需要接網際網路），然後用手機瀏覽器打開以下其中一個網址：\n")
    for ip in get_local_ips():
        print("    https://{}:{}/{}".format(ip, PORT, HTML_FILE))
    print("\n第一次連線手機會跳出「憑證不受信任」的警告，這是正常的（因為是自簽憑證），")
    print("選擇「進階」→「仍要前往」即可繼續。按 Ctrl+C 可關閉伺服器。\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n伺服器已關閉。")


if __name__ == "__main__":
    main()
