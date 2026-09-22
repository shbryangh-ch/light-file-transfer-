#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sender.py — 用一連串 QR Code 把檔案「播放」在螢幕上，讓手機鏡頭掃描接收。

用法：
    python sender.py <檔案路徑> [--chunk 300] [--delay 0.25] [--size 800]

參數：
    --chunk   每個 QR Code 承載的原始資料大小（bytes），越小越好掃但畫面數越多
    --delay   每個畫面停留秒數，太快手機來不及對焦/拍到會漏格（但沒關係，會循環重播）
    --size    QR Code 顯示的像素邊長（正方形），依螢幕大小調整

需求套件：
    pip install qrcode opencv-python pillow numpy
    注意：這裡要用一般的 opencv-python（不是 headless 版），才能開視窗顯示畫面。

操作：
    執行後會全螢幕顯示 QR Code，並不斷循環播放整個檔案的所有分片。
    手機那邊打開接收網頁掃描即可，收到多少會自動顯示進度，全部收齊後這邊可以按 ESC 結束。
"""

import sys
import os
import argparse
import base64
import zlib

import qrcode
import numpy as np
import cv2


def build_frames(filepath: str, chunk_size: int):
    """把檔案切成分片，並產生每個要顯示的 QR Code 文字內容。"""
    with open(filepath, "rb") as f:
        data = f.read()

    filename = os.path.basename(filepath).encode("utf-8")
    total_size = len(data)
    total_chunks = max(1, (total_size + chunk_size - 1) // chunk_size)

    frames = []

    # 第一張：META 畫面，告訴接收端檔名、總大小、總分片數
    meta = "META|{}|{}|{}".format(
        total_chunks, total_size, base64.b64encode(filename).decode("ascii")
    )
    frames.append(meta)

    # 之後每張：F<index>/<total>|<crc32 hex>|<base64 payload>
    for i in range(total_chunks):
        chunk = data[i * chunk_size : (i + 1) * chunk_size]
        crc = zlib.crc32(chunk) & 0xFFFFFFFF
        payload = base64.b64encode(chunk).decode("ascii")
        frames.append("F{}/{}|{:08x}|{}".format(i, total_chunks, crc, payload))

    return frames, total_chunks, total_size


def make_qr_image(text: str, box_size: int = 8, border: int = 4):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    arr = np.array(img)
    return arr[:, :, ::-1]  # PIL 的 RGB 轉成 OpenCV 用的 BGR


def main():
    parser = argparse.ArgumentParser(description="用 QR Code 序列在螢幕上播放檔案")
    parser.add_argument("filepath", help="要傳送的檔案路徑")
    parser.add_argument("--chunk", type=int, default=300, help="每格資料大小（bytes），預設 300")
    parser.add_argument("--delay", type=float, default=0.25, help="每格停留秒數，預設 0.25")
    parser.add_argument("--size", type=int, default=800, help="QR Code 顯示像素邊長，預設 800")
    args = parser.parse_args()

    if not os.path.isfile(args.filepath):
        print("找不到檔案：{}".format(args.filepath))
        sys.exit(1)

    frames, total_chunks, total_size = build_frames(args.filepath, args.chunk)
    print("檔案大小：{} bytes".format(total_size))
    print("分片數：{}（+1 張 META 畫面）".format(total_chunks))
    print("每格 {} bytes，每格停留 {} 秒".format(args.chunk, args.delay))
    print("估計每輪播放時間：約 {:.1f} 秒".format((total_chunks + 1) * args.delay))
    print("視窗顯示後按 ESC 可離開（會不斷循環播放，直到手機收齊為止）")

    window_name = "QR Sender"
    cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    idx = 0
    n = len(frames)
    while True:
        img = make_qr_image(frames[idx])
        img = cv2.resize(img, (args.size, args.size), interpolation=cv2.INTER_NEAREST)

        # 加一點白邊 padding，避免螢幕邊緣裁切造成手機對焦困難
        canvas = np.full((args.size + 100, args.size + 100, 3), 255, dtype=np.uint8)
        y0 = 50
        x0 = 50
        canvas[y0 : y0 + args.size, x0 : x0 + args.size] = img

        # 左上角顯示目前進度（人看的，不影響掃描）
        label = "{}/{}".format(idx, n - 1)
        cv2.putText(canvas, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

        cv2.imshow(window_name, canvas)
        key = cv2.waitKey(int(args.delay * 1000))
        if key == 27:  # ESC
            break
        idx = (idx + 1) % n

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
