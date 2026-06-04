import streamlit as st
import os
import re
import tempfile
from openai import OpenAI
import edge_tts
import asyncio
from yt_dlp import YoutubeDL
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip, ColorClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import requests

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="🎬 ဇာတ်ကားအကျဉ်းချုပ် စက်ရုံကြီး",
    page_icon="🎬",
    layout="wide"
)

# Initialize DeepSeek via OpenAI compatible endpoint
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
deepseek_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

# --- FUNCTIONS ---
def generate_summary(movie_title, language="my"):
    """Generate movie summary using DeepSeek AI"""
    prompt = f"""
    အောက်ပါဇာတ်ကားအကြောင်း အသေးစိတ်အကျဉ်းချုပ်ရေးပါ။
    ဇာတ်ကားအမည်: {movie_title}
    
    လိုအပ်ချက်များ:
    1. ဇာတ်လမ်းအစအဆုံးကို အကျဉ်းချုပ်ရေးပါ။
    2. အရေးကြီးသောအဖြစ်အပျက်များနှင့် ဇာတ်ကောင်များအကြောင်း ဖော်ပြပါ။
    3. ဘာသာစကား: မြန်မာစာ
    4. အရှည်: စာလုံးရေ ၃၀၀-၅၀၀ ကြား
    5. ပုံစံ: အပိုဒ်ခွဲ၍ ရှင်းလင်းစွာရေးပါ။
    """

    response = deepseek_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1000
    )
    return response.choices[0].message.content.strip()


async def text_to_speech(text, output_path):
    """Convert text to speech using Edge TTS"""
    voice = "my-MM-NilarNeural" # Myanmar female voice
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def download_video(url, output_path):
    """Download video from URL using yt-dlp"""
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def create_video_with_text(video_path, text, audio_path, output_path):
    """Create final video with text overlay and audio"""
    # Load video and audio
    video = VideoFileClip(video_path).resize(height=720) # Resize for standard
    audio = AudioFileClip(audio_path)

    # Trim video to match audio length
    video = video.subclip(0, min(video.duration, audio.duration))

    # Create text overlay
    txt_clip = TextClip(
        text,
        fontsize=24,
        color='white',
        font='Myanmar Sans Pro',
        method='caption',
        size=(video.w - 100, None) # Wrap text
    ).set_position('center').set_duration(video.duration)

    # Add semi-transparent background for text
    bg = ColorClip(size=(txt_clip.w + 20, txt_clip.h + 20), color=(0,0,0)).set_opacity(0.7)
    bg = bg.set_position(txt_clip.pos).set_duration(video.duration)

    # Combine everything
    final_video = CompositeVideoClip([video, bg, txt_clip])
    final_video = final_video.set_audio(audio)

    # Export
    final_video.write_videofile(output_path, codec='libx264', audio_codec='aac', fps=24, logger=None)

    # Cleanup
    video.close()
    audio.close()
    final_video.close()


# --- UI LAYOUT ---
st.title("🎬 **ဇာတ်ကားအကျဉ်းချုပ် စက်ရုံကြီး**")
st.markdown("#### 🤖 AI ဖြင့် အလိုအလျောက် ဇာတ်ကားအကျဉ်းချုပ် ရေးသားပေးမယ့် စက်ရုံကြီးပါ။")

tab1, tab2 = st.tabs(["📝 ခေါင်းစဉ်မှ ရေးမယ်", "🔗 လင့်ခ်မှ ယူမယ်"])

with tab1:
    movie_name = st.text_input("🎬 ဇာတ်ကားအမည် ရေးပါ", placeholder="ဥပမာ: ဘုရားဖြစ်တော်မူခြင်း")
    if st.button("✨ အကျဉ်းချုပ်ရေးမည်", type="primary") and movie_name:
        with st.spinner("🧠 AI စဉ်းစားနေပါတယ်... ခဏစောင့်ပါ..."):
            summary = generate_summary(movie_name)
            st.success("✅ ရေးပြီးပါပြီ!")
            st.text_area("📄 အကျဉ်းချုပ်အကြောင်းအရာ", summary, height=300)

            # Generate Audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_tmp:
                audio_path = audio_tmp.name
            asyncio.run(text_to_speech(summary, audio_path))
            st.audio(audio_path, format="audio/mp3")

with tab2:
    video_url = st.text_input("🔗 Video Link ထည့်ပါ (YouTube, Facebook, etc...)")
    custom_text = st.text_area("✍️ အကျဉ်းချုပ်စာသား သို့မဟုတ် မှတ်ချက်", placeholder="ဗီဒီယိုပေါ်မှာ ရေးပြမယ့် စာသားကို ဒီမှာရေးပါ...")

    if st.button("🎥 ဗီဒီယိုဖန်တီးမည်", type="primary") and video_url and custom_text:
        with st.spinner("⏳ ဖန်တီးနေပါတယ်... အချိန်အနည်းငယ်ကြာနိုင်ပါသည်..."):
            try:
                # 1. Download Video
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as video_tmp:
                    video_path = video_tmp.name
                download_video(video_url, video_path)

                # 2. Generate Audio
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_tmp:
                    audio_path = audio_tmp.name
                asyncio.run(text_to_speech(custom_text, audio_path))

                # 3. Create Final Video
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as final_tmp:
                    final_path = final_tmp.name
                create_video_with_text(video_path, custom_text, audio_path, final_path)

                # 4. Show & Download
                st.success("✅ ဗီဒီယိုအသစ် ဖန်တီးပြီးပါပြီ!")
                st.video(final_path)
                with open(final_path, "rb") as f:
                    st.download_button("💾 ဗီဒီယိုကို သိမ်းမယ်", f, file_name="movie_recap.mp4", mime="video/mp4")

            except Exception as e:
                st.error(f"❌ အမှားအယွင်းရှိနေပါသည်: {str(e)}")

# --- FOOTER ---
st.markdown("---")
st.markdown("📌 **မှတ်ချက်**: ဤစက်ရုံကြီးကို AI နည်းပညာများဖြင့် တည်ဆောက်ထားပါသည်။ မြန်မာစာဖြင့် အသံထွက်နိုင်ရန် ပြင်ဆင်ထားပါသည်။")
                    
