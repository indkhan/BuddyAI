import asyncio
import re
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
from typing import Optional
from tkinter import font as tkfont
from PIL import Image, ImageTk
import io
import base64
from dotenv import load_dotenv
import os
import nest_asyncio
import queue
import sounddevice as sd
import soundfile as sf
import numpy as np
from groq import Groq
import tempfile
from datetime import datetime

from smart_agent import process_query
from app.logger import logger

# Load environment variables
load_dotenv()

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Create a queue for thread communication
response_queue = queue.Queue()

# Create and set the event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Initialize Groq client
groq_client = Groq()


def run_async_task(coro):
    """Run a coroutine in the main event loop"""
    return asyncio.run_coroutine_threadsafe(coro, loop)


def start_event_loop():
    """Start the event loop in a separate thread"""
    loop.run_forever()


# Start the event loop in a separate thread
threading.Thread(target=start_event_loop, daemon=True).start()


class AudioRecorder:
    def __init__(self):
        self.recording = False
        self.frames = []
        self.sample_rate = 44100
        self.channels = 1

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

        # Convert frames to numpy array
        audio_data = np.concatenate(self.frames, axis=0)

        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
            sf.write(temp_filename, audio_data, self.sample_rate)
            return temp_filename


class LoadingSpinner:
    def __init__(self, canvas, x, y, size=20):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.size = size
        self.angle = 0
        self.is_spinning = False
        self.spinner_id = None

    def start(self):
        self.is_spinning = True
        self._spin()

    def stop(self):
        self.is_spinning = False
        if self.spinner_id:
            self.canvas.after_cancel(self.spinner_id)
            self.spinner_id = None
        self.canvas.delete("spinner")

    def _spin(self):
        if not self.is_spinning:
            return

        self.canvas.delete("spinner")
        # Draw spinner
        for i in range(8):
            angle = self.angle + (i * 45)
            rad = angle * 3.14159 / 180
            x1 = self.x + self.size * 0.5 * (1 - abs(i - 4) / 4) * (1 if i < 4 else -1)
            y1 = self.y + self.size * 0.5 * (1 - abs(i - 4) / 4) * (1 if i < 4 else -1)
            x2 = self.x + self.size * 0.8 * (1 - abs(i - 4) / 4) * (1 if i < 4 else -1)
            y2 = self.y + self.size * 0.8 * (1 - abs(i - 4) / 4) * (1 if i < 4 else -1)
            self.canvas.create_line(
                x1, y1, x2, y2, fill="#0078d4", width=2, tags="spinner"
            )

        self.angle = (self.angle + 10) % 360
        self.spinner_id = self.canvas.after(50, self._spin)


class BuddyAIDesktopApp:
    """Desktop application for the BuddyAI Assistant"""

    def __init__(self, root):
        self.root = root
        self.root.title("BuddyAI Assistant")
        self.root.geometry("1000x800")
        self.root.minsize(800, 600)

        # Initialize audio recorder
        self.audio_recorder = AudioRecorder()
        self.is_recording = False

        # Set theme colors
        self.colors = {
            "bg": "#1e1e1e",
            "fg": "#ffffff",
            "accent": "#0078d4",
            "secondary": "#2d2d2d",
            "text": "#ffffff",
            "input_bg": "#2d2d2d",
            "button_bg": "#0078d4",
            "button_hover": "#106ebe",
            "message_bg": "#2d2d2d",
            "user_message_bg": "#0078d4",
            "assistant_message_bg": "#2d2d2d",
            "mic_active": "#ff4444",
        }

        self.processing = False
        self.loading = False

        # Configure root window
        self.root.configure(bg=self.colors["bg"])

        # Apply styling
        self._apply_styling()

        # Create UI elements
        self._create_ui()

        # Welcome message
        self._append_to_output(
            "Assistant: Welcome to BuddyAI! I'm here to help you with any task. How can I assist you today?"
        )

    def _apply_styling(self):
        """Apply modern styling to the application"""
        style = ttk.Style()

        # Configure custom styles
        style.configure("Modern.TFrame", background=self.colors["bg"])

        style.configure(
            "Modern.TLabelframe",
            background=self.colors["bg"],
            foreground=self.colors["text"],
        )

        style.configure(
            "Modern.TLabelframe.Label",
            background=self.colors["bg"],
            foreground=self.colors["text"],
            font=("Segoe UI", 10),
        )

        style.configure(
            "Modern.TButton",
            background=self.colors["button_bg"],
            foreground=self.colors["text"],
            font=("Segoe UI", 10),
            borderwidth=0,
            focusthickness=0,
            focuscolor=self.colors["button_bg"],
        )

        style.map(
            "Modern.TButton",
            background=[
                ("active", self.colors["button_hover"]),
                ("pressed", self.colors["button_hover"]),
            ],
            foreground=[
                ("active", self.colors["text"]),
                ("pressed", self.colors["text"]),
            ],
        )

    def _create_ui(self):
        """Create the modern user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, style="Modern.TFrame", padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top bar with title
        top_frame = ttk.Frame(main_frame, style="Modern.TFrame")
        top_frame.pack(fill=tk.X, pady=(0, 20))

        # Title
        title_font = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        title_label = ttk.Label(
            top_frame,
            text="BuddyAI",
            font=title_font,
            background=self.colors["bg"],
            foreground=self.colors["text"],
        )
        title_label.pack(side=tk.LEFT)

        # Chat area
        self.output_frame = ttk.LabelFrame(
            main_frame, text="Conversation", style="Modern.TLabelframe", padding="10"
        )
        self.output_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Custom font for chat
        chat_font = tkfont.Font(family="Segoe UI", size=10)

        # Create loading canvas first
        self.loading_canvas = tk.Canvas(
            self.output_frame,
            background=self.colors["bg"],
            highlightthickness=0,
            width=400,
            height=300,
        )

        # Create spinner
        self.spinner = LoadingSpinner(
            self.loading_canvas,
            self.loading_canvas.winfo_reqwidth() // 2,
            self.loading_canvas.winfo_reqheight() // 2,
        )

        # Create output area
        self.output_area = scrolledtext.ScrolledText(
            self.output_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=chat_font,
            background=self.colors["bg"],
            foreground=self.colors["text"],
            insertbackground=self.colors["text"],
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        self.output_area.pack(fill=tk.BOTH, expand=True)

        # Input area with mic button
        input_frame = ttk.Frame(main_frame, style="Modern.TFrame")
        input_frame.pack(fill=tk.X)

        # Create mic button
        self.mic_button = ttk.Button(
            input_frame,
            text="🎤",
            command=self._toggle_recording,
            style="Modern.TButton",
            padding=(10, 10),
        )
        self.mic_button.pack(side=tk.LEFT, padx=(0, 10))

        self.input_area = scrolledtext.ScrolledText(
            input_frame,
            wrap=tk.WORD,
            height=3,
            font=chat_font,
            background=self.colors["input_bg"],
            foreground=self.colors["text"],
            insertbackground=self.colors["text"],
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        self.input_area.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.input_area.bind("<Return>", self._on_enter)
        self.input_area.bind("<Control-Return>", self._insert_newline)

        self.submit_button = ttk.Button(
            input_frame,
            text="Send",
            command=self._process_input,
            style="Modern.TButton",
            padding=(20, 10),
        )
        self.submit_button.pack(side=tk.RIGHT)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            background=self.colors["secondary"],
            foreground=self.colors["text"],
            padding=(10, 5),
            font=("Segoe UI", 9),
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _on_enter(self, event):
        """Handle Enter key press"""
        if not event.state & 0x4:  # If Ctrl is not pressed
            self._process_input()
            return "break"  # Prevent default behavior
        return None

    def _insert_newline(self, event):
        """Handle Ctrl+Enter key press to insert a newline"""
        return None  # Allow default behavior (insert newline)

    def _toggle_recording(self):
        """Toggle audio recording on/off"""
        if not self.is_recording:
            # Start recording
            self.is_recording = True
            self.mic_button.configure(text="⏹", style="Recording.TButton")
            self.audio_recorder.start_recording()
            self.status_var.set("Recording... Click again to stop.")
        else:
            # Stop recording
            self.is_recording = False
            self.mic_button.configure(text="🎤", style="Modern.TButton")
            temp_filename = self.audio_recorder.stop_recording()
            self.status_var.set("Processing audio...")

            # Transcribe in a separate thread
            threading.Thread(
                target=self._transcribe_audio, args=(temp_filename,), daemon=True
            ).start()

    def _transcribe_audio(self, filename):
        """Transcribe the recorded audio using Groq Whisper"""
        try:
            with open(filename, "rb") as file:
                transcription = groq_client.audio.transcriptions.create(
                    file=(filename, file.read()),
                    model="whisper-large-v3",
                    response_format="verbose_json",
                )

                # Update UI with transcription
                self.root.after(
                    0, lambda: self._update_input_with_transcription(transcription.text)
                )

        except Exception as e:
            error_msg = f"Error transcribing audio: {str(e)}"
            self.root.after(0, lambda: self._update_input_with_transcription(error_msg))
        finally:
            # Clean up temporary file
            try:
                os.unlink(filename)
            except:
                pass
            self.status_var.set("Ready")

    def _update_input_with_transcription(self, text):
        """Update the input area with the transcribed text"""
        self.input_area.delete("1.0", tk.END)
        self.input_area.insert("1.0", text)

    def _show_loading(self):
        """Show loading spinner"""
        self.loading = True
        # Don't hide the output area, just show the spinner on top
        self.loading_canvas.pack(fill=tk.BOTH, expand=True)
        self.spinner.start()
        self.status_var.set("Processing your request...")

    def _hide_loading(self):
        """Hide loading spinner"""
        self.loading = False
        self.spinner.stop()
        self.loading_canvas.pack_forget()
        self.status_var.set("Ready")

    def _clean_output(self, text: str) -> str:
        """Clean and format the output"""
        try:
            # Remove any system messages or processing indicators
            text = re.sub(r"🔍.*?\.\.\.", "", text)
            text = re.sub(r"✅.*?completed\.", "", text)
            text = re.sub(r"System:.*?\n", "", text)

            # Clean up extra whitespace
            text = re.sub(r"\n\s*\n", "\n\n", text)
            text = text.strip()

            return text

        except Exception as e:
            logger.error(f"Error cleaning output: {str(e)}")
            return text

    def _process_input(self):
        """Process the user's input"""
        if self.processing:
            return

        user_input = self.input_area.get("1.0", tk.END).strip()
        if not user_input:
            return

        self._append_to_output(f"You: {user_input}")
        self.input_area.delete("1.0", tk.END)

        # Show loading state
        self._show_loading()

        # Standard processing mode
        self.processing = True
        self.submit_button.configure(state=tk.DISABLED)

        # Use a thread to avoid blocking the UI
        threading.Thread(
            target=self._run_agent, args=(user_input,), daemon=True
        ).start()

    def _run_agent(self, user_input: str):
        """Run the agent in a separate thread"""
        try:
            # Schedule the process_query coroutine in the main event loop
            future = run_async_task(process_query(user_input))

            # Wait for the result
            response = future.result(timeout=60)  # 60 second timeout

            # Clean and format the response
            cleaned_response = self._clean_output(response)

            # Update UI in main thread
            self.root.after(0, self._update_ui_after_processing, cleaned_response)

        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            self.root.after(0, lambda: self._update_ui_after_processing(error_msg))

    def _update_ui_after_processing(self, output: str):
        """Update the UI after processing is complete"""
        # Hide loading state
        self._hide_loading()

        # Add to conversation history
        if output:
            self._append_to_output(f"Assistant: {output}")

        # Reset UI state
        self.processing = False
        self.submit_button.configure(state=tk.NORMAL)

    def _append_to_output(self, text: str):
        """Append text to the output area with modern styling"""
        self.output_area.configure(state=tk.NORMAL)

        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M")

        # Determine if it's a user or assistant message
        if text.startswith("You:"):
            bg_color = self.colors["user_message_bg"]
            prefix = f"[{timestamp}] You:"
        else:
            bg_color = self.colors["assistant_message_bg"]
            prefix = f"[{timestamp}] {text.split(':')[0]}:"
            text = text.split(":", 1)[1].strip()

        # Create message bubble
        self.output_area.insert(tk.END, f"\n{prefix}\n", "prefix")
        self.output_area.insert(tk.END, f"{text}\n", "message")

        # Configure tags for styling
        self.output_area.tag_configure(
            "prefix", foreground="#888888", spacing1=10, spacing3=5
        )
        self.output_area.tag_configure(
            "message",
            background=bg_color,
            foreground=self.colors["text"],
            spacing1=5,
            spacing3=10,
            lmargin1=20,
            lmargin2=20,
            rmargin=20,
        )

        self.output_area.see(tk.END)
        self.output_area.configure(state=tk.DISABLED)


def main():
    """Main entry point for the application"""
    try:
        root = tk.Tk()
        app = BuddyAIDesktopApp(root)
        root.mainloop()
    finally:
        # Clean up the event loop when the application closes
        loop.call_soon_threadsafe(loop.stop)
        loop.close()


if __name__ == "__main__":
    main()
