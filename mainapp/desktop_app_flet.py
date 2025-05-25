import flet as ft
import asyncio
from smart_agent import process_query
from datetime import datetime
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
from groq import Groq
import os

# Initialize Groq client
groq_client = Groq()


class AudioRecorder:
    def __init__(self):
        self.recording = False
        self.frames = []
        self.sample_rate = 44100
        self.channels = 1
        self.stream = None

    def start_recording(self):
        self.recording = True
        self.frames = []

        def callback(indata, frames, time, status):
            if status:
                print(status)
            if self.recording:
                self.frames.append(indata.copy())

        self.stream = sd.InputStream(
            channels=self.channels, samplerate=self.sample_rate, callback=callback
        )
        self.stream.start()

    def stop_recording(self):
        self.recording = False
        self.stream.stop()
        self.stream.close()
        audio_data = np.concatenate(self.frames, axis=0)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
            sf.write(temp_filename, audio_data, self.sample_rate)
            return temp_filename


def main(page: ft.Page):
    page.title = "BuddyAI Assistant"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.Colors.BLACK
    page.padding = 0
    page.window_min_width = 900
    page.window_min_height = 700
    page.window_width = 1100
    page.window_height = 800

    # Sidebar (left)
    sidebar = ft.Container(
        width=260,
        bgcolor=ft.Colors.with_opacity(0.97, ft.Colors.BLUE_GREY_900),
        padding=ft.padding.only(top=30, left=20, right=20),
        content=ft.Column(
            [
                ft.Text(
                    "BuddyAI Copilot",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                ),
                ft.Divider(
                    height=30, color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE)
                ),
                ft.Text("Conversation History", size=14, color=ft.Colors.GREY_400),
                ft.Container(
                    ft.Text(
                        "Sign in to keep your conversations.",
                        size=12,
                        color=ft.Colors.GREY_500,
                    ),
                    margin=ft.margin.only(top=8, bottom=8),
                ),
                ft.ElevatedButton(
                    "Sign In",
                    icon=ft.Icons.PERSON,
                    bgcolor=ft.Colors.BLUE_800,
                    color=ft.Colors.WHITE,
                    disabled=True,
                ),
                ft.Container(height=30),
                ft.Text("Quick Actions", size=14, color=ft.Colors.GREY_400),
                ft.Row(
                    [
                        ft.Chip(label=ft.Text("Write a first draft", size=12)),
                        ft.Chip(label=ft.Text("Get advice", size=12)),
                        ft.Chip(label=ft.Text("Learn something new", size=12)),
                        ft.Chip(label=ft.Text("Create an image", size=12)),
                        ft.Chip(label=ft.Text("Make a plan", size=12)),
                        ft.Chip(label=ft.Text("Brainstorm ideas", size=12)),
                        ft.Chip(label=ft.Text("Practice a language", size=12)),
                        ft.Chip(label=ft.Text("Take a quiz", size=12)),
                    ],
                    spacing=6,
                ),
                ft.Container(expand=True),
            ],
            expand=True,
        ),
    )

    # Chat area (right)
    chat_messages = ft.ListView(
        expand=True,
        spacing=10,
        auto_scroll=True,
        padding=ft.padding.only(left=20, right=20, top=30, bottom=10),
    )

    # Welcome message
    def add_message(text, sender="assistant"):
        now = datetime.now().strftime("%H:%M")
        if sender == "user":
            bubble_color = ft.Colors.BLUE_700
            align = ft.alignment.center_right
            prefix = f"[{now}] You:"
        else:
            bubble_color = ft.Colors.BLUE_GREY_800
            align = ft.alignment.center_left
            prefix = f"[{now}] Assistant:"
        chat_messages.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(prefix, size=12, color=ft.Colors.GREY_400),
                        ft.Text(text, size=16, color=ft.Colors.WHITE),
                    ],
                    spacing=2,
                ),
                bgcolor=bubble_color,
                border_radius=ft.border_radius.all(14),
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                alignment=align,
                margin=ft.margin.only(left=0, right=0, top=0, bottom=0),
            )
        )
        page.update()

    add_message(
        "Welcome to BuddyAI! I'm here to help you with any task. How can I assist you today?",
        sender="assistant",
    )

    # Input area
    user_input = ft.TextField(
        hint_text="Message Copilot",
        multiline=True,
        min_lines=1,
        max_lines=4,
        border_radius=12,
        filled=True,
        fill_color=ft.Colors.BLUE_GREY_900,
        border_color=ft.Colors.BLUE_700,
        text_style=ft.TextStyle(size=16, color=ft.Colors.WHITE),
        expand=True,
    )

    send_button = ft.IconButton(
        icon=ft.Icons.SEND_ROUNDED,
        icon_color=ft.Colors.BLUE_400,
        tooltip="Send",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
    )

    # Audio recorder
    audio_recorder = AudioRecorder()
    is_recording = False
    status_text = ft.Text("Ready", size=12, color=ft.Colors.GREY_400)

    # Mic button logic
    def toggle_recording(e):
        nonlocal is_recording
        if not is_recording:
            is_recording = True
            mic_button.icon = ft.Icons.STOP
            mic_button.icon_color = ft.Colors.RED_400
            status_text.value = "Recording... Click again to stop."
            page.update()
            audio_recorder.start_recording()
        else:
            is_recording = False
            mic_button.icon = ft.Icons.MIC_NONE
            mic_button.icon_color = ft.Colors.GREY_600
            status_text.value = "Processing audio..."
            page.update()
            temp_filename = audio_recorder.stop_recording()
            # Transcribe in background
            page.run_task(transcribe_audio, temp_filename)

    mic_button = ft.IconButton(
        icon=ft.Icons.MIC_NONE,
        icon_color=ft.Colors.GREY_600,
        tooltip="Voice input",
        on_click=toggle_recording,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
    )

    # Loading indicator
    loading_indicator = ft.ProgressRing(visible=False, color=ft.Colors.BLUE_400)

    async def transcribe_audio(filename):
        try:
            with open(filename, "rb") as file:
                transcription = await asyncio.to_thread(
                    lambda: groq_client.audio.transcriptions.create(
                        file=(filename, file.read()),
                        model="whisper-large-v3",
                        response_format="verbose_json",
                    )
                )
            user_input.value = transcription.text
            status_text.value = "Ready"
            page.update()
        except Exception as e:
            user_input.value = f"Error transcribing audio: {str(e)}"
            status_text.value = "Ready"
            page.update()
        finally:
            try:
                os.unlink(filename)
            except:
                pass

    # Send message handler
    async def send_message(e=None):
        text = user_input.value.strip()
        if not text:
            return
        add_message(text, sender="user")
        user_input.value = ""
        loading_indicator.visible = True
        status_text.value = "Processing your request..."
        page.update()
        try:
            response = await process_query(text)
        except Exception as ex:
            response = f"An error occurred: {ex}"
        loading_indicator.visible = False
        status_text.value = "Ready"
        add_message(response, sender="assistant")
        page.update()

    send_button.on_click = send_message
    user_input.on_submit = send_message

    # Layout
    chat_column = ft.Column(
        [
            chat_messages,
            ft.Row(
                [
                    mic_button,
                    user_input,
                    send_button,
                    loading_indicator,
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.END,
                spacing=8,
            ),
            status_text,
        ],
        expand=True,
    )

    # Main layout
    page.add(
        ft.Row(
            [
                sidebar,
                ft.VerticalDivider(
                    width=1, color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE)
                ),
                ft.Container(
                    chat_column,
                    expand=True,
                    bgcolor=ft.Colors.with_opacity(0.98, ft.Colors.BLACK),
                ),
            ],
            expand=True,
        )
    )


if __name__ == "__main__":
    ft.app(target=main)
