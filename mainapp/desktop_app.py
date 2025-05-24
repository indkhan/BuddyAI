import asyncio
import re
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
from typing import Optional
from tkinter import font as tkfont

from app.agent.manus import Manus
from app.logger import logger


class UdsopDesktopApp:
    """Desktop application for the UdS_OP agent"""

    def __init__(self, root):
        self.root = root
        self.root.title("BuddyAI Assistant")
        self.root.geometry("1000x800")
        self.root.minsize(800, 600)

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
        }

        # Initialize the agent
        self.agent = Manus()
        self.processing = False
        self.web_mode = False

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

        style.configure(
            "Web.TButton",
            background=self.colors["accent"],
            foreground=self.colors["text"],
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )

        style.map(
            "Web.TButton",
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

        # Top bar with Web button
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

        # Web button
        self.web_button = ttk.Button(
            top_frame,
            text="Web Mode",
            command=self._toggle_web_mode,
            style="Web.TButton",
            padding=(15, 8),
        )
        self.web_button.pack(side=tk.RIGHT)

        # Chat area
        self.output_frame = ttk.LabelFrame(
            main_frame, text="Conversation", style="Modern.TLabelframe", padding="10"
        )
        self.output_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Custom font for chat
        chat_font = tkfont.Font(family="Segoe UI", size=10)

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

        # Input area
        input_frame = ttk.Frame(main_frame, style="Modern.TFrame")
        input_frame.pack(fill=tk.X)

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

    def _toggle_web_mode(self):
        """Toggle web mode on/off"""
        self.web_mode = not self.web_mode

        if self.web_mode:
            # Activate web mode
            self.web_button.configure(text="Web Mode: ON", style="WebMode.TButton")
            self.status_var.set("Web Mode: Type your browser instruction")
            self._append_to_output(
                "System: Web Mode activated. Your instructions will be executed in a browser."
            )
        else:
            # Deactivate web mode
            self.web_button.configure(text="Web", style="Web.TButton")
            self.status_var.set("Ready")
            self._append_to_output(
                "System: Web Mode deactivated. Returning to normal assistant mode."
            )

    def _run_web_agent(self, user_instruction):
        """Run the web browsing agent with the user's instruction"""
        if self.processing:
            return

        self.processing = True
        self.status_var.set("Running browser automation...")
        self.web_button.configure(state=tk.DISABLED)
        self._append_to_output("System: Launching browser automation...")

        # Use a thread to avoid blocking the UI
        threading.Thread(
            target=self._execute_web_agent, args=(user_instruction,), daemon=True
        ).start()

    def _execute_web_agent(self, task):
        """Execute the web browsing agent in a separate thread with the user's task"""
        try:
            # Create and run a new event loop for the thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Import and execute web browsing functionality
            import sys
            import os

            # Add the parent directory to sys.path to find the webo module
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if parent_dir not in sys.path:
                sys.path.append(parent_dir)

            try:
                # Import the browser agent functionality
                from webo.browser_use import Agent as BrowserAgent
                from langchain_google_genai import ChatGoogleGenerativeAI
                from dotenv import load_dotenv

                # Load environment variables and initialize LLM
                load_dotenv()
                llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

                # Create and run the browser agent with the user's task
                async def run_browser_task():
                    agent = BrowserAgent(task=task, llm=llm, headless=False)
                    await agent.run()

                # Run the browser task
                loop.run_until_complete(run_browser_task())
                self.root.after(0, self._on_web_agent_success)
            except Exception as e:
                error_msg = f"Error running web agent: {str(e)}"
                self.root.after(0, lambda: self._on_web_agent_error(error_msg))
        finally:
            loop.close()

    def _on_web_agent_success(self):
        """Handle successful web agent execution"""
        self._append_to_output("System: Browser automation completed successfully.")
        self.processing = False
        self.status_var.set("Ready")
        self.web_button.configure(state=tk.NORMAL)
        # Reset web mode after completion
        self.web_mode = False
        self.web_button.configure(text="Web", style="Web.TButton")

    def _on_web_agent_error(self, error_msg):
        """Handle web agent execution error"""
        self._append_to_output(f"Error: {error_msg}")
        self.processing = False
        self.status_var.set("Ready")
        self.web_button.configure(state=tk.NORMAL)
        # Reset web mode after completion
        self.web_mode = False
        self.web_button.configure(text="Web", style="Web.TButton")

    def _on_enter(self, event):
        """Handle Enter key press"""
        if not event.state & 0x4:  # If Ctrl is not pressed
            self._process_input()
            return "break"  # Prevent default behavior
        return None

    def _insert_newline(self, event):
        """Handle Ctrl+Enter key press to insert a newline"""
        return None  # Allow default behavior (insert newline)

    def _process_input(self):
        """Process the user's input"""
        if self.processing:
            return

        user_input = self.input_area.get("1.0", tk.END).strip()
        if not user_input:
            return

        self._append_to_output(f"You: {user_input}")
        self.input_area.delete("1.0", tk.END)

        # Check if we're in web mode
        if self.web_mode:
            # Run the web agent with the user's instruction
            self._run_web_agent(user_input)
            return

        # Standard processing mode
        # Disable UI during processing
        self.processing = True
        self.status_var.set("Processing...")
        self.submit_button.configure(state=tk.DISABLED)

        # Use a thread to avoid blocking the UI
        threading.Thread(
            target=self._run_agent, args=(user_input,), daemon=True
        ).start()

    def _run_agent(self, user_input: str):
        """Run the agent in a separate thread"""
        # Create and run a new event loop for the thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create a future for the agent's response
        output_collector = OutputCollector()

        # Patch the agent's logger to capture output
        original_info = logger.info
        original_error = logger.error

        try:
            # Override logger.info and logger.error
            def capture_info(msg, *args, **kwargs):
                original_info(msg, *args, **kwargs)
                output_collector.add_output(msg)

            def capture_error(msg, *args, **kwargs):
                original_error(msg, *args, **kwargs)
                output_collector.add_output(f"Error: {msg}")

            logger.info = capture_info
            logger.error = capture_error

            # Run the agent
            loop.run_until_complete(self.agent.run(user_input))
        except Exception as e:
            output_collector.add_output(f"An error occurred: {str(e)}")
        finally:
            # Restore original logger methods
            logger.info = original_info
            logger.error = original_error
            loop.close()

            # Update UI in main thread
            self.root.after(
                0, self._update_ui_after_processing, output_collector.get_output()
            )

    def _update_ui_after_processing(self, output: str):
        """Update the UI after processing is complete"""
        # Extract only the answer part for all interactions
        formatted_output = output

        if output and "Request processing completed" in output:
            # Extract the answer part between the processing messages
            parts = output.split("🔍 Processing your request...")
            if len(parts) > 1:
                answer_parts = parts[1].split("✅ Request processing completed.")
                if len(answer_parts) > 1:
                    answer = answer_parts[0].strip()
                    formatted_output = f"Assistant: {answer}"

        # Add to conversation history
        self._append_to_output(formatted_output)

        # Reset UI state
        self.processing = False
        self.status_var.set("Ready")
        self.submit_button.configure(state=tk.NORMAL)

    def _append_to_output(self, text: str):
        """Append text to the output area with modern styling"""
        self.output_area.configure(state=tk.NORMAL)

        # Add timestamp
        from datetime import datetime

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


class OutputCollector:
    """Helper class to collect output from the agent"""

    def __init__(self):
        self.output = []

    def add_output(self, msg: str):
        self.output.append(str(msg))

    def get_output(self) -> str:
        return "\n".join(self.output)


def main():
    """Main entry point for the application"""
    root = tk.Tk()
    app = UdsopDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
