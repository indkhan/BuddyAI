import argparse
import asyncio
import os
import sys
from typing import Optional

from app.agent.udsop import udsop
from app.logger import logger
from app.tool.terminal import Terminal
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading


class InterpreterMode:
    """Interactive mode for the udsop agent similar to Open Interpreter"""

    def __init__(self, agent: udsop):
        self.agent = agent
        self.terminal = Terminal()
        self.conversation_history = []
        self.running = True

    async def run(self):
        """Run the interpreter in interactive mode"""
        logger.info("🤖 Udsop Interpreter started. Type 'exit' to quit.")
        logger.info("💡 Type your message and press Enter to start a conversation.")

        while self.running:
            try:
                # Get user input
                user_input = input("\n👤 > ")

                if not user_input.strip():
                    continue

                if user_input.lower() in ['exit', 'quit']:
                    logger.info("👋 Exiting interpreter session...")
                    self.running = False
                    break

                # Process user input
                logger.info("🔍 Processing your request...")
                await self.agent.run(user_input)
                logger.info("✅ Request processing completed.")

            except KeyboardInterrupt:
                logger.warning("⚠️ Operation interrupted.")
                choice = input("\nDo you want to exit? (y/n): ")
                if choice.lower() == 'y':
                    self.running = False
                    break
            except Exception as e:
                logger.error(f"❌ An error occurred: {str(e)}")


async def main():
    parser = argparse.ArgumentParser(description="Udsop - An AI agent with Open Interpreter-like capabilities")
    parser.add_argument("--prompt", "-p", type=str, help="Input prompt to process once and exit")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode like Open Interpreter")
    parser.add_argument("--shell", "-s", action="store_true", help="Enable system shell access")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Create the udsop agent
    agent = udsop()

    # Add Terminal tool if shell access is enabled
    if args.shell:
        # Check if Terminal tool is already in available_tools
        terminal_exists = any(
            tool.name == 'execute_command'
            for tool in agent.available_tools.tools
        )

        if not terminal_exists:
            logger.info("🐚 Enabling system shell access...")
            agent.available_tools.add_tool(Terminal())

    try:
        if args.interactive:
            # Run in interactive mode
            interpreter = InterpreterMode(agent)
            await interpreter.run()
        elif args.prompt:
            # Process a single prompt
            logger.info("🔍 Processing your request...")
            await agent.run(args.prompt)
            logger.info("✅ Request processing completed.")
        else:
            # Default behavior: prompt for input once
            prompt = input("Enter your prompt: ")
            if not prompt.strip():
                logger.warning("⚠️ Empty prompt provided.")
                return

            logger.info("🔍 Processing your request...")
            await agent.run(prompt)
            logger.info("✅ Request processing completed.")
    except KeyboardInterrupt:
        logger.warning("⚠️ Operation interrupted.")


class UdsopDesktopApp:
    """Desktop application for the Udsop agent"""

    def __init__(self, root):
        self.root = root
        self.root.title("Udsop Desktop Assistant")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Initialize the agent
        self.agent = udsop()
        self.processing = False
        
        # Create UI elements
        self._create_ui()
        
    def _create_ui(self):
        """Create the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Output area
        self.output_frame = ttk.LabelFrame(main_frame, text="Conversation")
        self.output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.output_area = scrolledtext.ScrolledText(
            self.output_frame, wrap=tk.WORD, state=tk.DISABLED, 
            width=70, height=20, font=("TkDefaultFont", 10)
        )
        self.output_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Input area
        input_frame = ttk.Frame(main_frame, padding="5")
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.input_label = ttk.Label(input_frame, text="Your instruction:")
        self.input_label.pack(anchor=tk.W, padx=5)
        
        input_box_frame = ttk.Frame(input_frame)
        input_box_frame.pack(fill=tk.X, expand=True)
        
        self.input_area = scrolledtext.ScrolledText(
            input_box_frame, wrap=tk.WORD, height=3, 
            font=("TkDefaultFont", 10)
        )
        self.input_area.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_area.bind("<Return>", self._on_enter)
        self.input_area.bind("<Control-Return>", self._insert_newline)
        
        self.submit_button = ttk.Button(
            input_box_frame, text="Submit", command=self._process_input
        )
        self.submit_button.pack(side=tk.RIGHT)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
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
    
    def _process_input(self):
        """Process the user's input"""
        if self.processing:
            return
        
        user_input = self.input_area.get("1.0", tk.END).strip()
        if not user_input:
            return
        
        self._append_to_output(f"You: {user_input}")
        self.input_area.delete("1.0", tk.END)
        
        # Disable UI during processing
        self.processing = True
        self.status_var.set("Processing...")
        self.submit_button.configure(state=tk.DISABLED)
        
        # Use a thread to avoid blocking the UI
        threading.Thread(target=self._run_agent, args=(user_input,), daemon=True).start()
    
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
            self.root.after(0, self._update_ui_after_processing, output_collector.get_output())
    
    def _update_ui_after_processing(self, output: str):
        """Update the UI after processing is complete"""
        # If output looks like just a question answer, format it nicely
        if output and "Request processing completed" in output:
            # Extract the answer part between the processing messages
            parts = output.split("🔍 Processing your request...")
            if len(parts) > 1:
                answer_parts = parts[1].split("✅ Request processing completed.")
                if len(answer_parts) > 1:
                    answer = answer_parts[0].strip()
                    output = f"Assistant: {answer}"
        
        self._append_to_output(output)
        self.processing = False
        self.status_var.set("Ready")
        self.submit_button.configure(state=tk.NORMAL)
    
    def _append_to_output(self, text: str):
        """Append text to the output area"""
        self.output_area.configure(state=tk.NORMAL)
        if self.output_area.index(tk.END) != "1.0":
            self.output_area.insert(tk.END, "\n\n")
        self.output_area.insert(tk.END, text)
        self.output_area.configure(state=tk.DISABLED)
        self.output_area.see(tk.END)


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
