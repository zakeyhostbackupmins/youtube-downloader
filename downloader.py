import os
import sys
import subprocess
import time
import argparse
import yt_dlp

YOUTUBE_COOKIES_PATH = "cookies_yt.txt"

def main():
    parser = argparse.ArgumentParser(description="YouTube Downloader for MP4 and MP3 with exact slicing.")
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument("--format", choices=['mp4', 'mp3'], default='mp4', help="Download format (mp4 or mp3)")
    parser.add_argument("--resolution", default='1080', help="Video resolution")
    parser.add_argument("--start", help="Start time for cut", default="")
    parser.add_argument("--end", help="End time for cut", default="")
    
    args = parser.parse_args()

    video_url = args.url
    local_source = "raw_download.mp4" if args.format == 'mp4' else "raw_download.webm"
    final_output = f"final_output.{args.format}"

    if os.path.exists(local_source): os.remove(local_source)
    if os.path.exists(final_output): os.remove(final_output)

    print(f"🔗 URL: {video_url}")
    print(f"🎯 Target Format: {args.format.upper()}")

    configs = [
        {'client': 'tv', 'proxy': None, 'use_cookies': False},
        {'client': 'android', 'proxy': None, 'use_cookies': False},
        {'client': 'ios', 'proxy': None, 'use_cookies': False},
        {'client': 'tv', 'proxy': 'socks5://127.0.0.1:40000', 'use_cookies': False},
        {'client': 'android', 'proxy': 'socks5://127.0.0.1:40000', 'use_cookies': False}
    ]
    
    download_success = False
    MAX_ATTEMPTS = 10

    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt > 1:
            print("\n🔄 Cycling Cloudflare WARP...")
            subprocess.run("warp-cli --accept-tos disconnect", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
            subprocess.run("warp-cli --accept-tos connect", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(8)
            
        print(f"\n🚀 --- DOWNLOAD ATTEMPT {attempt}/{MAX_ATTEMPTS} ---")

        for cfg in configs:
            if args.format == 'mp4':
                res = args.resolution
                dl_format = f'bestvideo[height<={res}][vcodec^=avc][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={res}]+bestaudio/best'
            else:
                dl_format = 'bestaudio/best'

            ydl_opts = {
                'format': dl_format,
                'outtmpl': local_source,
                'extractor_args': {'youtube': [f"player_client={cfg['client']}", "player_skip=web,web_embedded"]},
                'quiet': False, 'no_warnings': True
            }
            
            if args.format == 'mp4':
                ydl_opts['merge_output_format'] = 'mp4'

            if cfg['proxy']: ydl_opts['proxy'] = cfg['proxy']
            if cfg['use_cookies'] and os.path.exists(YOUTUBE_COOKIES_PATH): ydl_opts['cookiefile'] = YOUTUBE_COOKIES_PATH

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: 
                    ydl.download([video_url])
                
                if os.path.exists(local_source) and os.path.getsize(local_source) > 50000:
                    print(f"✅ Download Success!")
                    download_success = True
                    break
            except Exception as e:
                print(f"⚠️ Failed: {e}")
                if os.path.exists(local_source): os.remove(local_source)
                
        if download_success: break

    if not download_success: 
        print("❌ Download failed completely.")
        sys.exit(1)

    print(f"\n🎬 Processing file with FFmpeg into {final_output}...")
    ffmpeg_cmd = ["ffmpeg", "-v", "warning", "-y"]

    if args.start:
        ffmpeg_cmd.extend(["-ss", str(args.start)])
    if args.end:
        ffmpeg_cmd.extend(["-to", str(args.end)])

    ffmpeg_cmd.extend(["-i", local_source])

    if args.format == 'mp3':
        ffmpeg_cmd.extend(["-vn", "-c:a", "libmp3lame", "-q:a", "2", final_output])
    else:
        if args.start or args.end:
            ffmpeg_cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", final_output])
        else:
            ffmpeg_cmd.extend(["-c", "copy", final_output])

    proc = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"❌ FFmpeg Error:\n{proc.stderr}")
        sys.exit(1)

    if os.path.exists(local_source): 
        os.remove(local_source)

    print(f"✨ SUCCESS! File saved as: {final_output}")

if __name__ == "__main__":
    main()
