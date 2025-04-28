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

def lista_arquivos():
    lista_reunioes = PASTA_AUDIOS.glob('*')
    lista_reunioes = list(lista_reunioes)
    lista_reunioes.sort(reverse=True)
    reunioes_dict = {}
    for pasta_reuniao in lista_reunioes:
        data_reunião = pasta_reuniao.stem
        data, hora = data_reunião.split('_')
        ano, mes, dia = data.split('-')
        hora, minuto, segundo = hora.split('-')
        reunioes_dict[data_reunião] = f'{dia}-{mes}-{ano} {hora}:{minuto}:{segundo}'
    return reunioes_dict

def salva_arquivo(path_file, data):
    with open(path_file, 'w') as file:
        file.write(data)

def transcreve_audio(path_file, language='pt', response_format='text'):
    with open(path_file, 'rb') as audio:
        transcript = client.audio.transcriptions.create(
            model='whisper-1',
            file=audio,
            language=language,
            response_format=response_format)
    return transcript

def chat_openai(transcript, model='gpt-4o-mini'):
    response = client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': transcript}]
    )
    return response.choices[0].message.content

def adiciona_audio(audio_frame, audio_chunks):
    for frame in audio_frame:
        sound = pydub.AudioSegment(
            data=frame.to_ndarray().tobytes(),
            sample_width=frame.format.bytes,
            frame_rate=frame.sample_rate,
            channels=len(frame.layout.channels)
        )
        audio_chunks += sound
    return audio_chunks
    

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
    ultima_transcricao = time.time()
    audio_chunks = pydub.AudioSegment.empty()
    audio_completo = pydub.AudioSegment.empty()
    transcript = ''
    while True:
        if webrtx_ctx.audio_receiver:
            try:
                audio_frame = webrtx_ctx.audio_receiver.get_frames(timeout=1)
            except queue.Empty:
                time.sleep(0.1)
                continue
            audio_chunks = adiciona_audio(audio_frame, audio_chunks)
            audio_completo = adiciona_audio(audio_frame, audio_chunks)
            if len(audio_chunks) > 0:
                audio_completo.export(pasta_reuniao / 'audio.mp3', format='mp3')
                agora = time.time()
                if agora - ultima_transcricao > 15:
                    ultima_transcricao = agora
                    audio_chunks.export(pasta_reuniao / 'audio_temp.mp3', format='mp3')
                    transcript_chunck = transcreve_audio(pasta_reuniao / 'audio_temp.mp3')
                    transcript += transcript_chunck
                    salva_arquivo(pasta_reuniao / 'transcript.txt', transcript)
                    container.markdown(f'Transcricao: {transcript}')
                    audio_chunks = pydub.AudioSegment.empty()
        else:
            break
        
def tab_selecao_reuniao():
    st.subheader('Selecionar Reunião')
    reunioes_dict = lista_arquivos()
    if len(reunioes_dict) > 0:
        reuniao_selecionada = st.selectbox('Selecione uma reunião', list(reunioes_dict.values()))
        st.divider()
        reuniao_data = [k for k, v in reunioes_dict.items() if v == reuniao_selecionada][0]
        pasta_reuniao = PASTA_AUDIOS / reuniao_data
        if not (pasta_reuniao / 'titulo.txt').exists():
            st.warning('Adicione um titulo')
            titulo = st.text_input('Titulo da reunião')
            st.button('Salvar', on_click=salvar_titulo(pasta_reuniao, titulo))
        else:
            titulo = ler_arquivos(pasta_reuniao / 'titulo.txt')
            transcript = ler_arquivos(pasta_reuniao / 'transcript.txt')
            st.markdown(f'# {titulo}')
            st.markdown(transcript)
    else:
        st.write('Nenhuma reunião encontrada')

def salvar_titulo(pasta_reuniao, titulo):
    salva_arquivo(pasta_reuniao / 'titulo.txt', titulo)

def ler_arquivos(caminho_arquivo):
    if caminho_arquivo.exists():
        with open(caminho_arquivo) as file:
            return file.read()
    else:
        return ''

def main():
    st.header('Bem-vindo ao MeetTranscription')
    tab_gravar, tab_selecao = st.tabs(['Gravar Reunião', 'Ver Transcrição Salva'])
    with tab_gravar:
        tab_gravar_reuniao()
    with tab_selecao:
        tab_selecao_reuniao()

if __name__ == '__main__':
    main()