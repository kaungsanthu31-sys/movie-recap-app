import streamlit as st
import os
import re
import tempfile
import numpy as np
import edge_tts
import asyncio
from dotenv import load_dotenv
from deepseek import DeepSeek
from yt_dlp import YoutubeDL
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont

# ------------------- CONFIGURATION -------------------
load_dotenv()
st.set_page_config(
    page_title="🎬 ဇာတ်ကားအကျဉ်းချုပ် စက်ရုံ",
    page_icon="🎬",
    layout="wide"
)

# Initialize ONLY DeepSeek (No Google!)
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
deepseek_client = DeepSeek(api_key=DEEPSEEK_KEY)

# ------------------- FUNCTIONS -------------------

def generate_script_and_caption(movie_name, duration_min):
    prompt = f"""
    သင်သည် TikTok, Facebook, YouTube အတွက် အကောင်းဆုံး ဇာတ်ကားအကျဉ်းချုပ်ရေးဆရာကြီးဖြစ်သည်။
    ဇာတ်ကားအမည်: {movie_name}
    ကြာမြင့်ချိန်: {duration_min} မိနစ်ခန့် ဖတ်ရှုနိုင်ရန်
    ဘာသာစကား: မြန်မာစာအပြည့်

    စည်းကမ်းချက်များ:
    1. ပထမစာကြောင်းကို အလွန်စိတ်ဝင်စားဖွယ်၊ အံ့အားသင့်စရာ ဖြင့်စပါ။
    2. ဇာတ်လမ်းအစ၊ အလယ်၊ အဆုံး အပြည့်အစုံပါရမည်။ အဓိကအဖြစ်အပျက်များပဲယူပါ။
    3. ပြောပုံမြန်မြန်ဆန်ဆန်၊ စိတ်လှုပ်ရှားဖွယ်ရှိပါစေ။ "ဘယ်လိုဖြစ်သွားလဲဆိုတော့", "အဆုံးမှာတော့" စသုံးပါ။
    4. အောက်တွင် "---CAPTION---" ခံပြီးနောက် တင်ရန်စာသား + Hashtag 5-7 ခု ရေးပေးပါ။
    5. Hashtag: #ဇာတ်ကားအကျဉ်းချုပ် #ရုပ်ရှင်သုံးသပ်ချက် #မြန်မာTikTok စသည်ဖြင့်ထည့်ပါ။

    ရလဒ်ပုံစံ:
    ---SCRIPT---
    (ဒီမှာဇာတ်လမ်း)
    ---CAPTION---
    (ဒီမှာစာသား + #hashtag)
    """

    res = deepseek_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role":"user", "content":prompt}]
    )
    text_output = res.choices[0].message.content

    try:
        script = re.search(r'---SCRIPT---(.*?)---CAPTION---', text_output, re.DOTALL).group(1).strip()
        caption = re.search(r'---CAPTION---(.*)', text_output, re.DOTALL).group(1).strip()
    except:
        script = text_output
        caption = f"ဇာတ်ကား: {movie_name}\n#ဇာတ်ကားအကျဉ်းချုပ် #MovieRecap"

    return script, caption

async def text_to_speech_edge(script_text):
    output_path = "temp_audio.mp3"
    communicate = edge_tts.Communicate(
        text=script_text,
        voice="my-MM-NyarLayNeural",
        rate="+25%",
        volume="+0%"
    )
    await communicate.save(output_path)
    return output_path

def download_video_youtube(movie_name):
    try:
        query = f"{movie_name} official trailer HD"
        ydl_opts = {
            'format': 'best[ext=mp4][height<=1080]',
            'outtmpl': 'source_video.mp4',
            'quiet': True,
            'default_search': 'ytsearch1:',
            'no_warnings': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([query])
        return "source_video.mp4"
    except Exception as e:
        st.error(f"ဗီဒီယိုရှာမတွေ့ပါ: {e}")
        return None

def create_text_image(text, size, bg_color=(0,0,0,200), text_color=(255,215,0)):
    width, height = size
    img = Image.new('RGBA', size, bg_color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("Pyidaungsu.ttf", 60)
    except:
        try:
            font = ImageFont.truetype("Arial.ttf", 60)
        except:
            font = ImageFont.load_default()
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    pos = ((width - (right-left))/2, (height - (bottom-top))/2)
    draw.text(pos, text, font=font, fill=text_color)
    return np.array(img)

def process_all_formats(video_path, audio_path, movie_title, logo_file=None):
    main_video = VideoFileClip(video_path).without_audio()
    main_audio = AudioFileClip(audio_path)
    audio_duration = main_audio.duration

    if main_video.duration < audio_duration:
        main_video = main_video.loop(duration=audio_duration)
    else:
        main_video = main_video.subclip(0, audio_duration)

    logo_clip = None
    if logo_file:
        logo_img = Image.open(logo_file).convert("RGBA").resize((100,100))
        logo_clip = ImageClip(np.array(logo_img)).set_duration(audio_duration).set_position(("left","top")).margin(20,20)

    formats = {
        "tiktok_reels": {"size":(1080,1920), "name":"TikTok_Reels", "desc":"📱 TikTok / Reels"},
        "square": {"size":(1080,1080), "name":"Facebook_Square", "desc":"🔲 Facebook Post"},
        "youtube_wide": {"size":(1920,1080), "name":"YouTube_Wide", "desc":"🖥️ YouTube / Watch"}
    }

    output_files = {}

    for key, fmt in formats.items():
        w, h = fmt["size"]
        if key == "tiktok_reels":
            new_w = int(main_video.h * 9 / 16)
            vid = main_video.crop(x_center=main_video.w/2, width=new_w, height=main_video.h).resize((w,h))
        elif key == "square":
            side = min(main_video.w, main_video.h)
            vid = main_video.crop(x_center=main_video.w/2, y_center=main_video.h/2, width=side, height=side).resize((w,h))
        else:
            vid = main_video.resize((w,h))

        title_img = create_text_image(movie_title, (w,h))
        title_clip = ImageClip(title_img).set_duration(3)

        bar = ColorClip((w,70), color=(0,0,0)).set_duration(audio_duration).set_position(("bottom")).margin(opacity=0.6)
        txt_img = Image.new('RGBA', (w,70), (0,0,0,0))
        draw = ImageDraw.Draw(txt_img)
        try: font = ImageFont.truetype("Pyidaungsu.ttf", 30)
        except: font = ImageFont.load_default()
        draw.text((20,10), f"🎬 {movie_title} | အကျဉ်းချုပ်", font=font, fill=(255,255,255))
        txt_clip = ImageClip(np.array(txt_img)).set_duration(audio_duration).set_position("bottom")

        layers = [vid, bar, txt_clip]
        if logo_file: layers.append(logo_clip.resize((w,h)))
        content = CompositeVideoClip(layers).set_audio(main_audio)

        final = concatenate_videoclips([title_clip, content.set_start(3)])

        out_path = f"{fmt['name']}.mp4"
        final.write_videofile(out_path, fps=30, bitrate="8000k", codec="libx264", audio_codec="aac", verbose=False, logger=None)
        output_files[key] = {"path":out_path, "info":fmt}

    return output_files

# ------------------- MAIN UI -------------------
def main():
    st.title("🎬 ဇာတ်ကားအကျဉ်းချုပ် စက်ရုံကြီး")
    st.subheader("TikTok • Facebook • YouTube အားလုံးအတွက်")

    with st.sidebar:
        st.header("⚙️ ဆက်တင်များ")
        duration = st.selectbox("⏱️ ကြာချိန် (မိနစ်)", [3,5,8,10], index=1)
        logo_file = st.file_uploader("🖼️ Logo ထည့်ရန်", type=['png','jpg'])
        st.info("✅ Google မလိုတော့ဘူး | ✅ လုံးဝအခမဲ့")

    movie_name = st.text_input("🎥 ဇာတ်ကားအမည် ထည့်ပါ", placeholder="ဥပမာ: Avatar, သူငယ်ချင်း...")

    if st.button("🚀 ဗီဒီယိုဖန်တီးမည်", type="primary", use_container_width=True):
        if not movie_name:
            st.warning("ဇာတ်ကားအမည်ထည့်ပါ"); return

        with st.status("လုပ်ဆောင်နေသည်...", expanded=True) as status:
            st.write("🔄 1/4: AI ဇာတ်လမ်းရေးနေသည်...")
            script, caption = generate_script_and_caption(movie_name, duration)
            st.success("ပြီးပါပြီ")

            st.write("🔄 2/4: အသံဖန်တီးနေသည်...")
            audio_path = asyncio.run(text_to_speech_edge(script))
            st.success("ပြီးပါပြီ")

            st.write("🔄 3/4: ဗီဒီယိုရှာဖွေနေသည်...")
            video_path = download_video_youtube(movie_name)
            if not video_path: st.error("ဗီဒီယိုမရှိပါ"); return
            st.success("ပြီးပါပြီ")

            st.write("🔄 4/4: အရွယ်အစားများခွဲဖြတ်နေသည်...")
            results = process_all_formats(video_path, audio_path, movie_name, logo_file)
            st.success("ပြီးပါပြီ")

            status.update(label="✅ အားလုံးပြီးဆုံးပါပြီ!", state="complete")

        st.divider()
        st.header("📥 ဒေါင်းယူရန်")
        c1,c2,c3 = st.columns(3)
        cols=[c1,c2,c3]
        for i,(k,d) in enumerate(results.items()):
            with cols[i]:
                st.subheader(d['info']['desc'])
                st.video(d['path'])
                with open(d['path'],"rb") as f:
                    st.download_button(f"⬇️ {d['info']['name']}", f, file_name=f"{movie_name}_{d['info']['name']}.mp4", use_container_width=True)

        st.divider()
        st.header("📝 တင်ရန်စာသား")
        st.code(caption)

        for f in [audio_path, video_path]:
            if os.path.exists(f): os.remove(f)
        for d in results.values():
            if os.path.exists(d['path']): os.remove(d['path'])

if __name__ == "__main__":
    main()
