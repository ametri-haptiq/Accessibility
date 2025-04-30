import csv
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# Set up WebDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

urls = [
    "https://silvur-web-git-staging-kindur.vercel.app/",
    "https://silvur-web-git-staging-kindur.vercel.app/about-us",
    "https://silvur-web-git-staging-kindur.vercel.app/technology-and-security",
    "https://silvur-web-git-staging-kindur.vercel.app/blog",
    "https://silvur-web-git-staging-kindur.vercel.app/blog/taxes/2025-president-budget-proposal",
    "https://silvur-web-git-staging-kindur.vercel.app/signIn",
    "https://silvur-web-git-staging-kindur.vercel.app/onboarding/name",
    "https://silvur-web-git-staging-kindur.vercel.app/onboarding/marital-status",
]

accessibility_issues = []

def wait_for_page_load():
    """Waits for the page to fully load before running Axe."""
    time.sleep(3)  # Allow initial load
    driver.execute_script("return document.readyState == 'complete'")  # Ensure full load

def inject_axe():
    """Injects axe-core into the page for accessibility testing."""
    try:
        axe_loaded = driver.execute_script("return typeof axe !== 'undefined';")
        
        if axe_loaded:
            print("✅ Axe-core is already loaded.")
            return True

        # Try loading from local file
        try:
            with open("axe.min.js", "r", encoding="utf-8") as file:
                axe_script = file.read()
            driver.execute_script(axe_script)
            time.sleep(2)  # Allow time for script execution
        except Exception as e:
            print(f"⚠️ Local axe.min.js not found, trying CDN...")

        # Fallback: Load axe-core from CDN
        driver.execute_script("""
            var script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.7.2/axe.min.js';
            script.async = false;
            document.head.appendChild(script);
        """)
        time.sleep(3)  # Give time to load

        axe_loaded = driver.execute_script("return typeof axe !== 'undefined';")
        if not axe_loaded:
            print("❌ Axe-core failed to load!")
            return False
        
        print("✅ Axe-core successfully loaded.")
        return True

    except Exception as e:
        print(f"⚠️ Error injecting axe-core: {e}")
        return False

def interact_with_dynamic_elements():
    """Interacts with buttons, links, and interactive elements before accessibility testing."""
    try:
        elements = driver.find_elements(By.XPATH, "//button | //a | //input | //select | //textarea")
        actions = ActionChains(driver)

        for el in elements[:5]:  # Limit interactions to prevent excessive clicks
            try:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", el)
                time.sleep(1)
                actions.move_to_element(el).click().perform()
                time.sleep(1)
            except Exception:
                continue
        print("✅ Interacted with dynamic elements.")
    except Exception as e:
        print(f"⚠️ Failed to interact with elements: {e}")

def categorize_warnings(issue):
    """Categorizes WCAG issues into A, AA, AAA, or Best Practices."""
    wcag_tags = issue.get("tags", [])
    if "wcag2a" in wcag_tags:
        return "A"
    elif "wcag2aa" in wcag_tags:
        return "AA"
    elif "wcag2aaa" in wcag_tags:
        return "AAA"
    elif "best-practice" in wcag_tags:
        return "Best Practices"
    return "Uncategorized"

def check_accessibility(url):
    """Checks accessibility for the given URL."""
    driver.get(url)
    wait_for_page_load()

    print(f"\n🔍 Testing accessibility for: {url}")

    if not inject_axe():
        print(f"🚫 Skipping {url} due to Axe injection failure.")
        return

    interact_with_dynamic_elements()

    # Run Axe after ensuring it's injected
    try:
        axe_results = driver.execute_script("""
        return new Promise((resolve) => {
            if (typeof axe === 'undefined') {
                resolve(null);  // Handle missing Axe case
            } else {
                axe.run().then(results => resolve(results.violations));
            }
        });
        """)

        if axe_results is None:
            print(f"⚠️ Axe-core is still missing on {url}, retrying...")

            # Retry injecting and running Axe
            if inject_axe():
                axe_results = driver.execute_script("return axe.run().then(results => results.violations);")

            if axe_results is None:
                print(f"❌ Still unable to analyze {url}, skipping.")
                return

    except Exception as e:
        print(f"❌ Error running axe on {url}: {e}")
        return

    if axe_results:
        print(f"❌ Found {len(axe_results)} total accessibility issues for {url}")
    else:
        print(f"✅ No accessibility issues found for {url}")

    for issue in axe_results:
        category = categorize_warnings(issue)
        description = issue["description"]
        impact = issue.get("impact", "unknown")
        wcag_tags = ", ".join(issue.get("tags", []))  

        accessibility_issues.append({
            "URL": url,
            "Issue": description,
            "Impact": impact,
            "WCAG Guidelines": wcag_tags,
            "WCAG Level": category
        })

    print(f"✅ Categorized {len(axe_results)} issues under WCAG Levels.")

for url in urls:
    check_accessibility(url)

driver.quit()

# Save report as CSV
csv_report = "accessibility_report.csv"
with open(csv_report, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=["URL", "Issue", "Impact", "WCAG Guidelines", "WCAG Level"])
    writer.writeheader()
    writer.writerows(accessibility_issues)

# Save report as JSON
json_report = "accessibility_report.json"
with open(json_report, "w", encoding="utf-8") as file:
    json.dump(accessibility_issues, file, indent=4)

print(f"\n✅ Accessibility reports saved as {csv_report} and {json_report}")