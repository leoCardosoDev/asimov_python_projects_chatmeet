from pathlib import Path
from datetime import datetime
import time
import queue
import pydub
from streamlit_webrtc import WebRtcMode, webrtc_streamer
import streamlit as st
import openai
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())
client = openai.OpenAI()
PASTA_AUDIOS = Path(__file__).parent / 'audios'
PASTA_AUDIOS.mkdir(exist_ok=True)

def transcreve_audio(path_file, language='pt-BR', response_format='text'):
    with open(path_file, 'rb') as audio:
        transcript = client.audio.transcriptions.create(
            model='whisper-1',
            file=audio,
            language=language,
            response_format=response_format)
    return transcript.text

def chat_openai(transcript, model='gpt-4o-mini'):
    response = client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': transcript}]
    )
    return response.choices[0].message.content
    

def tab_gravar_reuniao():
    st.subheader('Gravar Reunião')
    st.write('Clique no botão abaixo para gravar uma reunião')
    webrtx_ctx = webrtc_streamer(
        key='recebe_audio',
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        media_stream_constraints={
            'audio': True,
            'video': False
        }
    )
    if not webrtx_ctx.state.playing:
        return
    container = st.empty()
    container.markdown('Comece a falar')
    pasta_reuniao = PASTA_AUDIOS / datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    pasta_reuniao.mkdir(exist_ok=True)
    audio_chunks = pydub.AudioSegment.empty()
    while True:
        if webrtx_ctx.audio_receiver:
            container.markdown('Estou recebendo audio')
            try:
                audio_frame = webrtx_ctx.audio_receiver.get_frames(timeout=1)
            except queue.Empty:
                time.sleep(0.1)
                continue
            for frame in audio_frame:
                sound = pydub.AudioSegment(
                    data=frame.to_ndarray().tobytes(),
                    sample_width=frame.format.bytes,
                    frame_rate=frame.sample_rate,
                    channels=len(frame.layout.channels)
                )
                audio_chunks += sound
            if len(audio_chunks) > 0:
                audio_chunks.export(pasta_reuniao / 'audio_temp.mp3', format='mp3')
        else:
            break
        
def tab_selecao_reuniao():
    st.subheader('Selecionar Reunião')
    st.write('Clique no botão abaixo para selecionar uma reunião')
    if st.button('Selecionar Reunião'):
        st.write('Reunião selecionada com sucesso')

def main():
    st.header('Bem-vindo ao MeetTranscription')
    tab_gravar, tab_selecao = st.tabs(['Gravar Reunião', 'Ver Transcrição Salva'])
    with tab_gravar:
        tab_gravar_reuniao()
    with tab_selecao:
        tab_selecao_reuniao()

if __name__ == '__main__':
    main()