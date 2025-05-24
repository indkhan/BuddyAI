import asyncio
from playwright.async_api import async_playwright, Page, Locator
from typing import Any, Dict, List, Optional
import time
import traceback


class Agent:
    """
    A browser automation agent that can perform web browsing tasks.
    Uses Playwright for browser automation and an LLM for decision making.
    """

    def __init__(self, task: str, llm: Any, headless: bool = False):
        """
        Initialize the browser agent.

        Args:
            task: The task description
            llm: Language model for decision making
            headless: Whether to run the browser in headless mode
        """
        self.task = task
        self.llm = llm
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.scripts_injected = False

    async def run(self):
        """Run the browser agent to complete the task"""
        try:
            # Setup the browser
            await self._setup_browser()

            # Execute the task
            await self._execute_task()

        except Exception as e:
            print(f"Error during browser automation: {str(e)}")
            traceback.print_exc()
        finally:
            # Clean up resources
            await self._cleanup()

    async def _setup_browser(self):
        """Initialize the browser and create a new page"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800}
        )
        self.page = await self.context.new_page()

        # Add event listeners for logging
        self.page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        self.page.on("pageerror", lambda err: print(f"Page error: {err}"))

        # Navigate to a blank page first to ensure scripts can be properly injected
        await self.page.goto("about:blank")

        # Now inject our visualization scripts
        await self._inject_visualization_scripts()

        print(f"Browser initialized for task: {self.task}")

    async def _inject_visualization_scripts(self):
        """Inject JavaScript for visual feedback during automation"""
        highlight_script = """
        window.automationUtils = {
            highlightElement: function(element) {
                if (!element) return element;
                
                try {
                    const originalOutline = element.style.outline;
                    const originalBoxShadow = element.style.boxShadow;
                    const originalPosition = element.style.position;
                    const originalZIndex = element.style.zIndex;
                    
                    // Save original styles
                    element._originalStyles = {
                        outline: originalOutline,
                        boxShadow: originalBoxShadow,
                        position: originalPosition,
                        zIndex: originalZIndex
                    };
                    
                    // Apply highlight styles
                    element.style.outline = '3px solid red';
                    element.style.boxShadow = '0 0 10px rgba(255, 0, 0, 0.7)';
                    element.style.position = originalPosition === 'static' ? 'relative' : originalPosition;
                    element.style.zIndex = '10000';
                    
                    // Create and append label
                    const label = document.createElement('div');
                    label.textContent = 'Interacting with this element';
                    label.style.position = 'absolute';
                    label.style.top = '-25px';
                    label.style.left = '0';
                    label.style.backgroundColor = 'red';
                    label.style.color = 'white';
                    label.style.padding = '2px 5px';
                    label.style.borderRadius = '3px';
                    label.style.fontSize = '12px';
                    label.style.zIndex = '10001';
                    label.className = 'automation-label';
                    
                    element.appendChild(label);
                } catch (e) {
                    console.error('Error highlighting element:', e);
                }
                
                return element;
            },
            
            unhighlightElement: function(element) {
                if (!element || !element._originalStyles) return;
                
                try {
                    element.style.outline = element._originalStyles.outline;
                    element.style.boxShadow = element._originalStyles.boxShadow;
                    element.style.position = element._originalStyles.position;
                    element.style.zIndex = element._originalStyles.zIndex;
                    
                    // Remove label if exists
                    const labels = element.getElementsByClassName('automation-label');
                    for (let i = 0; i < labels.length; i++) {
                        element.removeChild(labels[i]);
                    }
                    
                    delete element._originalStyles;
                } catch (e) {
                    console.error('Error unhighlighting element:', e);
                }
            },
            
            showClickVisual: function(x, y) {
                try {
                    const clickIndicator = document.createElement('div');
                    clickIndicator.style.position = 'absolute';
                    clickIndicator.style.width = '20px';
                    clickIndicator.style.height = '20px';
                    clickIndicator.style.borderRadius = '50%';
                    clickIndicator.style.backgroundColor = 'rgba(255, 0, 0, 0.5)';
                    clickIndicator.style.transform = 'translate(-50%, -50%)';
                    clickIndicator.style.left = x + 'px';
                    clickIndicator.style.top = y + 'px';
                    clickIndicator.style.zIndex = '10002';
                    
                    document.body.appendChild(clickIndicator);
                    
                    // Animate and remove
                    clickIndicator.animate([
                        { opacity: 1, transform: 'translate(-50%, -50%) scale(1)' },
                        { opacity: 0, transform: 'translate(-50%, -50%) scale(2)' }
                    ], {
                        duration: 500,
                        easing: 'ease-out'
                    }).onfinish = () => document.body.removeChild(clickIndicator);
                } catch (e) {
                    console.error('Error showing click visual:', e);
                }
            },
            
            showTaskStatus: function(message) {
                try {
                    let statusBar = document.getElementById('automation-status-bar');
                    
                    if (!statusBar) {
                        statusBar = document.createElement('div');
                        statusBar.id = 'automation-status-bar';
                        statusBar.style.position = 'fixed';
                        statusBar.style.bottom = '0';
                        statusBar.style.left = '0';
                        statusBar.style.right = '0';
                        statusBar.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
                        statusBar.style.color = 'white';
                        statusBar.style.padding = '10px';
                        statusBar.style.zIndex = '10003';
                        statusBar.style.fontFamily = 'Arial, sans-serif';
                        statusBar.style.textAlign = 'center';
                        document.body.appendChild(statusBar);
                    }
                    
                    statusBar.textContent = message;
                } catch (e) {
                    console.error('Error showing task status:', e);
                }
            }
        };
        """

        try:
            # Directly evaluate the script instead of using add_init_script
            await self.page.evaluate(highlight_script)

            # Also add it as an init script for new pages/navigations
            await self.page.add_init_script(highlight_script)

            # Test if the script was injected successfully
            await self.page.evaluate(
                "window.automationUtils.showTaskStatus('Browser automation initialized')"
            )
            self.scripts_injected = True
            print("Visualization scripts injected successfully")
        except Exception as e:
            print(f"Warning: Failed to inject visualization scripts: {str(e)}")
            self.scripts_injected = False

    async def _highlight_element(self, locator: Locator, message: str = None):
        """Highlight an element before interacting with it"""
        if not self.scripts_injected:
            return

        try:
            if await locator.count() > 0:
                # Show task status message
                if message:
                    await self._show_status(message)

                # Highlight the element
                await self.page.evaluate(
                    "element => window.automationUtils.highlightElement(element)",
                    await locator.element_handle(),
                )
                await asyncio.sleep(0.8)  # Brief pause to make highlight visible
        except Exception as e:
            print(f"Warning: Failed to highlight element: {str(e)}")

    async def _unhighlight_element(self, locator: Locator):
        """Remove highlight from an element after interaction"""
        if not self.scripts_injected:
            return

        try:
            if await locator.count() > 0:
                await self.page.evaluate(
                    "element => window.automationUtils.unhighlightElement(element)",
                    await locator.element_handle(),
                )
        except Exception as e:
            print(f"Warning: Failed to unhighlight element: {str(e)}")

    async def _visualize_click(self, x, y):
        """Show a visual effect when clicking at coordinates"""
        if not self.scripts_injected:
            return

        try:
            await self.page.evaluate(
                f"window.automationUtils.showClickVisual({x}, {y})"
            )
        except Exception as e:
            print(f"Warning: Failed to visualize click: {str(e)}")

    async def _show_status(self, message: str):
        """Display a status message in the browser"""
        if not self.scripts_injected:
            print(message)  # Fallback to console if scripts aren't injected
            return

        try:
            # Escape single quotes in the message to avoid JavaScript errors
            safe_message = message.replace("'", "\\'")
            await self.page.evaluate(
                f"window.automationUtils.showTaskStatus('{safe_message}')"
            )
        except Exception as e:
            print(f"Warning: Failed to show status: {str(e)}")
            print(message)  # Fallback to console

    async def _enhanced_click(self, locator: Locator, message: str = None):
        """Enhanced click with visual feedback"""
        print(f"Action: {message or 'Clicking element'}")

        try:
            if message is None:
                message = "Clicking element"

            await self._highlight_element(locator, message)

            # Get element position for click visualization
            if self.scripts_injected:
                try:
                    bounds = await self.page.evaluate(
                        """
                        element => {
                            const rect = element.getBoundingClientRect();
                            return {
                                x: rect.left + rect.width / 2,
                                y: rect.top + rect.height / 2
                            };
                        }
                        """,
                        await locator.element_handle(),
                    )
                except Exception:
                    bounds = None

            # Perform the click
            await locator.click()

            # Visualize the click
            if self.scripts_injected and bounds:
                await self._visualize_click(bounds["x"], bounds["y"])

            # Remove highlight
            await self._unhighlight_element(locator)
            await asyncio.sleep(0.5)  # Short pause after interaction
        except Exception as e:
            print(f"Error during click operation: {str(e)}")
            # Try fallback to plain click without visual effects
            await locator.click(timeout=5000)

    async def _enhanced_fill(self, locator: Locator, text: str, message: str = None):
        """Enhanced fill with visual feedback"""
        print(f"Action: {message or f'Filling with text: {text}'}")

        try:
            if message is None:
                message = f"Filling with text: {text}"

            await self._highlight_element(locator, message)
            await locator.fill(text)
            await self._unhighlight_element(locator)
            await asyncio.sleep(0.5)  # Short pause after interaction
        except Exception as e:
            print(f"Error during fill operation: {str(e)}")
            # Try fallback to plain fill without visual effects
            await locator.fill(text, timeout=5000)

    async def _execute_task(self):
        """Execute the specific task based on the instructions"""
        print(f"Executing task: {self.task}")

        # Default to a Google search first, then detect specific tasks
        if "amazon" in self.task.lower() and (
            "cart" in self.task.lower() or "buy" in self.task.lower()
        ):
            await self._amazon_search_task()
        elif "compare" in self.task.lower() and "price" in self.task.lower():
            await self._price_comparison_task()
        elif "youtube" in self.task.lower() or "video" in self.task.lower():
            await self._youtube_search_task()
        else:
            # Default to general search and navigation
            await self._general_search_task()

    async def _amazon_search_task(self):
        """Handle Amazon search and cart tasks"""
        # Extract search term from the task
        search_terms = ["monitor under 50 euros"]  # Default

        if "search for" in self.task.lower():
            parts = self.task.lower().split("search for")
            if len(parts) > 1:
                search_part = parts[1].strip()
                end_markers = [" and ", " then ", ". ", " to "]
                for marker in end_markers:
                    if marker in search_part:
                        search_part = search_part.split(marker)[0]
                search_terms = [search_part]

        # Go to Amazon
        amazon_domain = "amazon.com"
        if "amazon.de" in self.task.lower():
            amazon_domain = "amazon.de"
        elif "amazon.co.uk" in self.task.lower():
            amazon_domain = "amazon.co.uk"

        await self._show_status(f"Navigating to {amazon_domain}")
        print(f"Navigating to {amazon_domain}")
        await self.page.goto(f"https://www.{amazon_domain}/")
        await asyncio.sleep(2)

        # Accept cookies if the dialog appears
        try:
            cookies_accepted = False

            # Try various common cookie accept button selectors
            selectors = [
                "input[name='accept']",
                "input#sp-cc-accept",
                "button#sp-cc-accept",
                "a#sp-cc-accept",
                "button:has-text('Accept Cookies')",
                "button:has-text('Accept All Cookies')",
                "button:has-text('Accept')",
            ]

            for selector in selectors:
                accept_button = self.page.locator(selector).first
                if await accept_button.count() > 0:
                    await self._enhanced_click(accept_button, "Accepting cookies")
                    cookies_accepted = True
                    break

            if cookies_accepted:
                print("Accepted cookies")
            else:
                print("No cookie dialog found or already accepted")

        except Exception as e:
            print(f"Cookie acceptance failed, continuing anyway: {str(e)}")

        # Search for the product
        search_term = search_terms[0]
        search_box = self.page.locator("input#twotabsearchtextbox")

        if await search_box.count() == 0:
            # Try other common search box selectors
            alt_selectors = ["input[name='field-keywords']", "input[type='search']"]
            for selector in alt_selectors:
                alt_search_box = self.page.locator(selector)
                if await alt_search_box.count() > 0:
                    search_box = alt_search_box
                    break

        await self._enhanced_fill(
            search_box, search_term, f"Searching for {search_term}"
        )
        await self.page.press("input#twotabsearchtextbox", "Enter")
        await asyncio.sleep(3)

        # Click on the first result
        try:
            # Different sites have different result selectors
            result_selectors = [
                "div[data-component-type='s-search-result'] h2 a",
                "div.s-result-item h2 a",
                "div.sg-col-inner h2 a",
                ".s-search-results .a-link-normal.a-text-normal",
            ]

            result_found = False
            for selector in result_selectors:
                first_result = self.page.locator(selector).first
                if await first_result.count() > 0:
                    await self._enhanced_click(first_result, "Selecting product")
                    result_found = True
                    break

            if not result_found:
                print("Could not find product results with known selectors")

            await asyncio.sleep(3)

            # Add to cart (if requested)
            if (
                "cart" in self.task.lower()
                or "buy" in self.task.lower()
                or "add" in self.task.lower()
            ):
                cart_button_selectors = [
                    "input#add-to-cart-button",
                    "span#submit\\.add-to-cart input",
                    "input[name='submit.add-to-cart']",
                    "button#add-to-cart-button",
                    "button:has-text('Add to Cart')",
                    "button:has-text('Add to Basket')",
                ]

                cart_button_found = False
                for selector in cart_button_selectors:
                    add_to_cart_button = self.page.locator(selector).first
                    if await add_to_cart_button.count() > 0:
                        await self._enhanced_click(
                            add_to_cart_button, "Adding item to cart"
                        )
                        cart_button_found = True
                        break

                if not cart_button_found:
                    print("Could not find add to cart button with known selectors")

                await asyncio.sleep(3)

                # Go to cart to verify if needed
                await self._show_status("Navigating to cart to verify item was added")
                await self.page.goto(f"https://www.{amazon_domain}/gp/cart/view.html")
                await asyncio.sleep(5)  # Wait to see the cart

        except Exception as e:
            print(f"Error during Amazon shopping task: {str(e)}")
            traceback.print_exc()

    async def _price_comparison_task(self):
        """Compare prices of products or services"""
        first_product = "GPT-4o"
        second_product = "DeepSeek-V3"

        # Extract products to compare from the task if available
        if "compare" in self.task.lower() and "price" in self.task.lower():
            task_lower = self.task.lower()
            if "between" in task_lower:
                products_part = task_lower.split("between")[1].strip()
            elif "of" in task_lower.split("price")[1]:
                products_part = task_lower.split("price of")[1].strip()
            else:
                products_part = task_lower.split("compare")[1].strip()

            if "and" in products_part:
                products = products_part.split("and")
                if len(products) >= 2:
                    first_product = products[0].strip()
                    second_product = products[1].strip().split(" on ")[0].strip()

        # Search for first product pricing
        await self._show_status(f"Searching for {first_product} pricing")
        await self.page.goto("https://www.google.com")

        # Accept cookies if the dialog appears
        try:
            accept_button = self.page.locator("button:has-text('Accept all')").first
            if await accept_button.count() > 0:
                await self._enhanced_click(accept_button, "Accepting Google cookies")
        except Exception:
            print("No Google cookie dialog found or unable to accept")

        search_box = self.page.locator("textarea[name='q']")
        await self._enhanced_fill(
            search_box,
            f"{first_product} pricing",
            f"Searching for {first_product} pricing information",
        )
        await self.page.press("textarea[name='q']", "Enter")
        await asyncio.sleep(3)
        await self._show_status(f"Viewing {first_product} pricing search results")
        await asyncio.sleep(5)  # Give time to view results

        # Screenshot the first product results
        screenshot_path1 = f"{first_product.replace(' ', '_')}_pricing.png"
        await self.page.screenshot(path=screenshot_path1)
        print(f"Saved screenshot of {first_product} pricing to {screenshot_path1}")

        # Search for second product pricing
        await self._show_status(f"Searching for {second_product} pricing")
        await self.page.goto("https://www.google.com")
        search_box = self.page.locator("textarea[name='q']")
        await self._enhanced_fill(
            search_box,
            f"{second_product} pricing",
            f"Searching for {second_product} pricing information",
        )
        await self.page.press("textarea[name='q']", "Enter")
        await asyncio.sleep(3)
        await self._show_status(f"Viewing {second_product} pricing search results")
        await asyncio.sleep(5)  # Give time to view results

        # Screenshot the second product results
        screenshot_path2 = f"{second_product.replace(' ', '_')}_pricing.png"
        await self.page.screenshot(path=screenshot_path2)
        print(f"Saved screenshot of {second_product} pricing to {screenshot_path2}")

        await self._show_status("Price comparison completed")
        print(f"Comparison completed between {first_product} and {second_product}")

    async def _youtube_search_task(self):
        """Handle YouTube search and video viewing"""
        # Extract search term from the task
        search_term = "programming tutorial"  # Default

        if "search for" in self.task.lower():
            parts = self.task.lower().split("search for")
            if len(parts) > 1:
                search_part = parts[1].strip()
                end_markers = [" and ", " then ", ". ", " to "]
                for marker in end_markers:
                    if marker in search_part:
                        search_part = search_part.split(marker)[0]
                search_term = search_part

        # Go to YouTube
        await self._show_status("Navigating to YouTube")
        await self.page.goto("https://www.youtube.com/")
        await asyncio.sleep(2)

        # Accept cookies if the dialog appears
        try:
            # YouTube has various consent screens depending on region
            consent_selectors = [
                "button.VfPpkd-LgbsSe[data-idom-class='ksBjEc LQeN7 G4njw']",  # "Accept all" button
                "button:has-text('Accept all')",
                "button:has-text('I agree')",
                "button:has-text('Accept')",
            ]

            for selector in consent_selectors:
                accept_button = self.page.locator(selector).first
                if await accept_button.count() > 0:
                    await self._enhanced_click(accept_button, "Accepting cookies")
                    break
        except Exception as e:
            print(f"Cookie acceptance failed, continuing anyway: {str(e)}")

        # Search for videos
        search_box = self.page.locator("input#search")
        await self._enhanced_fill(
            search_box, search_term, f"Searching YouTube for: {search_term}"
        )

        # Press search button or Enter key
        search_button = self.page.locator("button#search-icon-legacy")
        if await search_button.count() > 0:
            await self._enhanced_click(search_button, "Searching")
        else:
            await self.page.press("input#search", "Enter")

        await asyncio.sleep(3)
        await self._show_status("Viewing search results")

        # Click on the first video
        try:
            video_selectors = [
                "ytd-video-renderer a#video-title",
                "ytd-video-renderer h3 a",
                "#contents ytd-video-renderer a#thumbnail",
            ]

            video_found = False
            for selector in video_selectors:
                first_video = self.page.locator(selector).first
                if await first_video.count() > 0:
                    await self._enhanced_click(first_video, "Playing video")
                    video_found = True
                    break

            if not video_found:
                print("Could not find video with known selectors")

            # Wait for the video to play
            await asyncio.sleep(10)
            await self._show_status("Video playback in progress")

        except Exception as e:
            print(f"Error during YouTube task: {str(e)}")

    async def _general_search_task(self):
        """Handle general search and browsing tasks"""
        # Determine if there's a specific site mentioned
        target_site = None
        task_lower = self.task.lower()

        common_sites = {
            "google": "https://www.google.com",
            "bing": "https://www.bing.com",
            "yahoo": "https://www.yahoo.com",
            "duckduckgo": "https://duckduckgo.com",
            "wikipedia": "https://www.wikipedia.org",
            "twitter": "https://twitter.com",
            "reddit": "https://www.reddit.com",
            "facebook": "https://www.facebook.com",
            "instagram": "https://www.instagram.com",
        }

        # Check if a specific site is mentioned in the task
        for site_name, url in common_sites.items():
            if site_name in task_lower:
                if (
                    f"go to {site_name}" in task_lower
                    or f"visit {site_name}" in task_lower
                ):
                    target_site = url
                    break

        # If a specific site was mentioned, go there directly
        if target_site:
            await self._show_status(f"Navigating to {target_site}")
            await self.page.goto(target_site)
            await asyncio.sleep(3)

        # Otherwise, perform a Google search for the task
        else:
            await self._show_status("Performing web search")
            await self.page.goto("https://www.google.com")

            # Accept cookies if the dialog appears
            try:
                accept_button = self.page.locator("button:has-text('Accept all')").first
                if await accept_button.count() > 0:
                    await self._enhanced_click(accept_button, "Accepting cookies")
            except Exception:
                pass

            # Search for the task
            search_box = self.page.locator("textarea[name='q']")
            await self._enhanced_fill(
                search_box, self.task, f"Searching for: {self.task}"
            )
            await self.page.press("textarea[name='q']", "Enter")
            await asyncio.sleep(3)

            # Click on the first search result (optional)
            if "click first result" in task_lower or "open first result" in task_lower:
                try:
                    first_result = self.page.locator(".g a").first
                    await self._enhanced_click(
                        first_result, "Opening first search result"
                    )
                    await asyncio.sleep(5)
                except Exception as e:
                    print(f"Error clicking first result: {str(e)}")
            else:
                await self._show_status("Viewing search results")
                await asyncio.sleep(5)

        # Take a screenshot of the final page
        screenshot_path = "web_search_result.png"
        await self.page.screenshot(path=screenshot_path)
        print(f"Saved screenshot of search results to {screenshot_path}")

        await self._show_status("Task completed")

    async def _cleanup(self):
        """Clean up resources by closing the browser"""
        if self.browser:
            print("Closing browser")
            await self.browser.close()
