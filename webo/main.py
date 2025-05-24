import json
import os
import asyncio
from dotenv import load_dotenv

# LangChain LLM imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# browser-use imports
from browser_use import Agent, Controller
from browser_use.browser.browser import Browser, BrowserConfig

load_dotenv()


from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

##############################################
# PART 1: Interactive Plan Refinement (Steps 1 & 2)
##############################################

system_prompt = SystemMessage(
    content="""
You are an assistant that refines user task instructions for browser automation.
When given a user's task along with additional context or modifications, determine whether there is enough 
information to generate a detailed, step-by-step plan.
Important:
- Do not ask for the current date or year; assume they are known.
- If the user provides modifications , update the plan accordingly.
Respond in valid JSON:
If complete, respond with:
  { "complete": true, "plan": "Detailed step-by-step plan..." }
If more info is needed, respond with:
  { "complete": false, "missing": ["Missing detail 1", "Missing detail 2"] }
Respond in valid JSON only.
"""
)


def clean_response(text: str) -> str:
    """Remove markdown code fences (e.g., ```json) so that JSON can be parsed."""
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
        return None


# Initialize the LLM for planning


async def interactive_plan_refinement() -> str:
    """
    Interactive loop to get a task, refine it until a complete plan is generated,
    and let the user confirm or modify it.
    Returns the final accepted plan.
    """
    conversation_history = ""
    user_task = input("Enter your task instruction: ")
    conversation_history += "User: " + user_task + "\n"

    print("\n[Step 1] Gathering information for a detailed plan...")
    result = query_agent(user_task, conversation_history)
    while not (result and result.get("complete")):
        missing = result.get("missing", []) if result else []
        if missing:
            print("\nThe agent indicates the task is missing the following details:")
            for detail in missing:
                print(" - " + detail)
        else:
            print("\nAgent response unclear. Please provide additional details.")
        additional = input("Enter additional details: ")
        conversation_history += "Additional: " + additional + "\n"
        result = query_agent(user_task, conversation_history)

    plan = result.get("plan", "No plan provided.")
    # Step 2: Confirm or refine the plan
    while True:
        print("\n=== Proposed Step-by-Step Plan ===\n")
        print(plan)
        print("\n===================================")
        confirmation = input(
            "\nDo you accept this plan? (if not, type your modification): "
        ).strip()
        if confirmation.lower().startswith("y"):
            print("\n✅ Plan accepted!")
            break
        else:
            conversation_history += "Modification: " + confirmation + "\n"
            result = query_agent(user_task, conversation_history)
            if result and result.get("complete"):
                plan = result.get("plan", plan)
            else:
                print(
                    "Agent still indicates missing info. Please provide more details."
                )
    return plan


##############################################
# PART 2: Error Analysis using LLM
##############################################

# Define a system prompt for error analysis
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


def analyze_error(error_msg: str) -> dict:
    """
    Uses an LLM to analyze an error message.
    Returns a JSON dict with 'problem' and 'question' keys.
    """
    messages = [error_analysis_prompt, HumanMessage(content="Error: " + error_msg)]
    response = llm.invoke(messages)
    cleaned = clean_response(response.content)
    try:
        return json.loads(cleaned)
    except Exception as e:
        print("Error parsing error analysis:", e)
        print("Raw error analysis response:", cleaned)
        return {
            "problem": "Unknown error",
            "question": "What additional information do you want to provide?",
        }


##############################################
# PART 3: Browser Execution with Resume & Interactive Error Handling
##############################################


async def execute_plan_with_resume(plan: str):
    """
    Execute the accepted plan using a browser-use agent.
    If an error occurs during execution, use the LLM to analyze the error,
    then ask the user for additional details to update the context and resume.
    """
    # Configure the browser-use Browser (update chrome_instance_path as needed)
    # browser_config = BrowserConfig(
    #     headless=False,
    #     chrome_instance_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"  # Modify for your OS
    # )
    # browser = Browser(config=browser_config)
    controller = Controller()  # Ensure Controller has an update_context method.

    # Create the browser-use agent with the accepted plan.
    browser_agent = Agent(
        task=plan,
        llm=llm,
        controller=controller,
        # browser=browser,
    )

    while True:
        try:
            # Run the agent while preserving browser state.
            await browser_agent.run(max_steps=100)
            # Optionally, if available, record a history GIF.
            try:
                browser_agent.create_history_gif()
            except AttributeError:
                pass
            print("\n✅ Task executed successfully!")
            break
        except Exception as e:
            error_str = str(e)
            print(f"\n⚠️  Error encountered: {error_str}")
            # Use LLM to analyze the error message.
            analysis = analyze_error(error_str)
            print("\nAgent's analysis of the error:")
            print("Problem: " + analysis.get("problem", "No analysis provided."))
            user_detail = input(
                analysis.get("question", "Please provide additional details: ") + " "
            )
            # Update the context generically with the user's response.
            # Here, we use a generic context key "error_feedback".
            controller.update_context("error_feedback", user_detail)
            print("Resuming execution with updated context...\n")
            # The loop will retry running browser_agent.run without restarting the browser.


##############################################
# MAIN: Interactive Planning then Browser Execution
##############################################


async def main():
    """Main entry point for the web browsing agent"""
    print("Starting web browsing agent...")

    # Create and run the agent
    agent = Agent(task="Compare the price of gpt-4o and DeepSeek-V3", llm=llm)
    await agent.run()

    print("Web browsing completed.")


if __name__ == "__main__":
    """Run the main function when executed directly"""
    asyncio.run(main())
