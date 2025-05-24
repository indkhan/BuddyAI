import json
import os
import asyncio
import gradio as gr
from dotenv import load_dotenv

# Load environment variables from .env file (ensure your .env is correctly formatted)
load_dotenv()

# Import LLM messaging components and Google Generative AI LLM
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# Import browser-use components for real browser automation
from browser_use import Agent, Controller
from browser_use.browser.browser import Browser, BrowserConfig

# Initialize the LLM using the experimental Gemini 2.0 Flash model
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.3)

##############################################
# PART 1: Interactive Plan Refinement
##############################################

system_prompt = SystemMessage(
    content="""
You are an assistant that refines user task instructions for browser automation.
When given a user's task along with additional context or modifications, determine whether there is enough 
information to generate a detailed, step-by-step plan.
Important:
- Do not ask for the current date or year; assume they are known.
- If the user provides modifications, update the plan accordingly.
Respond in valid JSON:
If complete, respond with:
  { "complete": true, "plan": "Detailed step-by-step plan..." }
If more info is needed, respond with:
  { "complete": false, "missing": ["Missing detail 1", "Missing detail 2"] }
Respond in valid JSON only.
"""
)


def clean_response(text: str) -> str:
    """Remove markdown code fences so JSON can be parsed."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def query_agent(task: str, history: str) -> dict:
    prompt_text = history + "\nUser Task: " + task
    messages = [system_prompt, HumanMessage(content=prompt_text)]
    response = llm.invoke(messages)
    cleaned = clean_response(response.content)
    try:
        return json.loads(cleaned)
    except Exception as e:
        print("Error parsing agent response:", e)
        print("Raw response after cleaning:", cleaned)
        return {"error": str(e), "raw": cleaned}


def generate_plan(task, additional_detail, conversation_history):
    """
    Update the conversation history and call the agent to generate/refine a plan.
    """
    if conversation_history.strip() == "":
        conversation_history = "User: " + task + "\n"
    if additional_detail:
        conversation_history += "Additional: " + additional_detail + "\n"
    result = query_agent(task, conversation_history)
    return conversation_history, result


##############################################
# PART 2: Browser Execution with Real Browser
##############################################


async def execute_plan_with_resume(plan: str):
    """
    Executes the accepted plan using the browser-use agent.
    This will launch a real browser (non-headless) and attempt to execute the plan.
    """
    # Configure the browser; update chrome_instance_path for your OS.
    # browser_config = BrowserConfig(
    #     headless=False,
    #     chrome_instance_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # Update as needed
    # )
    # browser = Browser(config=browser_config)
    controller = Controller()  # Ensure that your Controller supports context updates

    # Create the agent with the accepted plan and a real browser instance.
    browser_agent = Agent(task=plan, llm=llm, controller=controller)

    while True:
        try:
            # This call should open the browser and execute the steps from the plan.
            await browser_agent.run(max_steps=100)
            try:
                browser_agent.create_history_gif()  # Optional: record history
            except AttributeError:
                pass
            return "✅ Task executed successfully! Browser automation completed."
        except Exception as e:
            error_str = str(e)
            print("\n⚠️  Error encountered:", error_str)
            analysis = analyze_error(error_str)
            print("\nAgent's analysis of the error:")
            print("Problem:", analysis.get("problem", "No analysis provided."))
            # In this example, we simply return the error details.
            return f"Error encountered: {error_str}\nAgent analysis: {analysis}"


def analyze_error(error_msg: str) -> dict:
    """
    Uses the LLM to analyze an error message from browser automation.
    Returns a JSON dict with 'problem' and 'question' keys.
    """
    error_analysis_prompt = SystemMessage(
        content="""
You are an assistant that analyzes error messages from a browser automation agent.
Given an error message, provide a brief description of the problem and ask a clarifying question 
that will help resolve the issue.
Respond in valid JSON format with two keys:
{
  "problem": "A brief description of the error in one sentence.",
  "question": "A clarifying question asking what additional detail is needed."
}
Respond in valid JSON only.
"""
    )
    messages = [error_analysis_prompt, HumanMessage(content="Error: " + error_msg)]
    response = llm.invoke(messages)
    cleaned = clean_response(response.content)
    try:
        return json.loads(cleaned)
    except Exception as e:
        print("Error parsing error analysis:", e)
        print("Raw error analysis response:", cleaned)
        return {"problem": "Unknown error", "question": "Provide additional info?"}


def run_plan(plan: str):
    try:
        logs = asyncio.run(execute_plan_with_resume(plan))
        return logs
    except Exception as e:
        return f"Error during execution: {e}"


##############################################
# GRADIO APP: Combining Planning & Execution
##############################################

with gr.Blocks() as demo:
    gr.Markdown("# Browser Automation Agent with Real Browser Execution")
    gr.Markdown(
        "1. In the **Generate Plan** tab, enter your task (e.g., "
        '"go to youtube and search bruno mars playlist and play it") along with any additional details. '
        "The agent will refine the instructions into a detailed plan (JSON with `complete: true`).\n"
        "2. Copy the `plan` text from the Agent Response and paste it into the **Execute Plan** tab.\n"
        "3. Click **Run Plan** to launch real browser automation."
    )

    with gr.Tabs():
        with gr.TabItem("Generate Plan"):
            with gr.Row():
                task_input = gr.Textbox(
                    lines=2,
                    placeholder="Enter your task instruction",
                    label="Task Instruction",
                )
                additional_input = gr.Textbox(
                    lines=2,
                    placeholder="Enter additional details (if needed)",
                    label="Additional Detail",
                )
            conversation_history = gr.Textbox(
                lines=4,
                placeholder="Conversation History",
                label="Conversation History",
                value="",
                interactive=True,
            )
            generate_button = gr.Button("Generate Plan")
            updated_history = gr.Textbox(label="Updated Conversation History")
            agent_response = gr.JSON(label="Agent Response (JSON)")

            generate_button.click(
                generate_plan,
                inputs=[task_input, additional_input, conversation_history],
                outputs=[updated_history, agent_response],
            )

        with gr.TabItem("Execute Plan"):
            plan_text = gr.Textbox(
                label="Plan Text",
                placeholder="Paste the accepted plan here...",
                lines=4,
            )
            run_button = gr.Button("Run Plan")
            execution_logs = gr.Textbox(label="Execution Logs", lines=10)

            run_button.click(run_plan, inputs=[plan_text], outputs=[execution_logs])

demo.launch()
