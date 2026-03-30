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
    local_source = "source_video.mp4" if args.format == 'mp4' else "source_audio.webm"
    final_output = f"final_output.{args.format}"

    if os.path.exists(local_source): os.remove(local_source)
    if os.path.exists(final_output): os.remove(final_output)

    print(f"🎬 Target URL: {video_url}")
    
    # --- EXACT CONFIGS FROM YOUR APP.PY ---
    configs = [
        {'client': 'tv', 'proxy': None, 'use_cookies': False},
        {'client': 'android', 'proxy': None, 'use_cookies': False},
        {'client': 'ios', 'proxy': None, 'use_cookies': False},
        {'client': 'tv', 'proxy': 'socks5://127.0.0.1:40000', 'use_cookies': False},
        {'client': 'android', 'proxy': 'socks5://127.0.0.1:40000', 'use_cookies': False},
        {'client': 'tv', 'proxy': None, 'use_cookies': True},
        {'client': 'tv', 'proxy': 'socks5://127.0.0.1:40000', 'use_cookies': True}
    ]
    
    download_success = False
    
    # Reduced internal loop to 3. If it fails 3 times, we let GitHub nuke the server and restart from Step 1.
    MAX_ATTEMPTS = 10

    # --- EXACT RETRY LOGIC FROM YOUR APP.PY ---
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt > 1:
            print("\n🔄 Cycling Cloudflare WARP...")
            subprocess.run("warp-cli --accept-tos disconnect", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
            subprocess.run("warp-cli --accept-tos connect", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(8)
            
        print(f"\n🚀 --- DOWNLOAD ATTEMPT {attempt}/{MAX_ATTEMPTS} ---")

        for cfg in configs:
            network = "WARP Proxy" if cfg['proxy'] else "GitHub Native IP"
            print(f"🎥 Trying client: {cfg['client']} | Network: {network} | Cookies: {cfg['use_cookies']}")
            
            # Use exact format string logic from app.py, adjusting resolution from args
            if args.format == 'mp4':
                res = args.resolution
                dl_format = f'bestvideo[height<={res}][vcodec^=avc][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={res}]+bestaudio/best'
            else:
                dl_format = 'bestaudio/best'

            # Exact ydl_opts dictionary format from your app.py
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
                # Using yt_dlp exactly as written in app.py
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([video_url])
                
                # Check for > 1000000 exactly as app.py does (for MP4 only, MP3 might be smaller)
                min_size = 1000000 if args.format == 'mp4' else 50000
                if os.path.exists(local_source) and os.path.getsize(local_source) > min_size:
                    print(f"✅ Download Success!")
                    download_success = True
                    break
            except Exception as e:
                print(f"⚠️ Failed: {e}")
                if os.path.exists(local_source): os.remove(local_source)
                
        if download_success: break

    # Exact exit text trigger
    if not download_success: 
        print("❌ Download failed completely. Exiting to trigger GitHub workflow restart.")
        # Exiting with code 1 fails the script and triggers the GitHub 'if: failure()' reboot
        sys.exit(1)

    # --- FFMPEG PROCESSING (FORMATTING & CLIPPING) ---
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

    print("✨ ALL DONE.")
    print(f"✅ Final Output Saved: {final_output}")

if __name__ == "__main__":
    main()
