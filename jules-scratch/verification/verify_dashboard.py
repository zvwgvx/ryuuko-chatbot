import re
from playwright.sync_api import sync_playwright, expect

def run_verification(playwright):
    """
    This script verifies the entire user flow for the new Ryuuko dashboard.
    1. Registers a new user.
    2. Logs the user in.
    3. Navigates to the "Link Account" page and generates a code.
    4. Navigates to the "Settings" page, modifies the settings, and saves them.
    5. Takes a screenshot of the successfully updated settings page.
    """
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # The web server is running on port 5173
    base_url = "http://localhost:5173"

    # --- 1. Registration ---
    print("Navigating to registration page...")
    page.goto(f"{base_url}/register")

    # Fill out the registration form
    page.get_by_label("Display Name:").fill("Jules the Engineer")
    page.get_by_label("Email:").fill("jules.engineer@test.com")
    page.get_by_label("Password:").fill("a-secure-password-123")

    # Submit the form
    page.get_by_role("button", name="Register").click()

    # --- 2. Login ---
    print("Navigating to login page...")
    # After registration, the app should navigate to /login
    expect(page).to_have_url(re.compile(r".*/login"))

    # Fill out the login form
    page.get_by_label("Email:").fill("jules.engineer@test.com")
    page.get_by_label("Password:").fill("a-secure-password-123")

    # Submit the form
    page.get_by_role("button", name="Login").click()

    # --- 3. Link Account ---
    print("Navigating to link account page...")
    # After login, we should be on the home page
    expect(page).to_have_url(re.compile(r".*/$"))
    page.get_by_role("link", name="Link Account").click()

    expect(page).to_have_url(re.compile(r".*/link-account"))
    page.get_by_role("button", name="Generate Link Code").click()

    # Expect the code to be visible
    link_code_locator = page.locator("p[style*='font-size: 2rem']")
    expect(link_code_locator).to_be_visible()
    print(f"Generated link code: {link_code_locator.inner_text()}")

    # --- 4. Settings Page ---
    print("Navigating to settings page...")
    page.get_by_role("link", name="Settings").click()
    expect(page).to_have_url(re.compile(r".*/settings"))

    # Wait for the form to be populated
    expect(page.get_by_label("AI Model:")).not_to_be_empty()

    # Change the settings
    page.get_by_label("AI Model:").fill("ryuuko-jules-verified-model")
    page.get_by_label("System Prompt:").fill("You are a helpful assistant created and verified by Jules.")

    # Save the settings
    page.get_by_role("button", name="Save Settings").click()

    # --- 5. Screenshot ---
    print("Taking screenshot...")
    # Verify the success message is visible
    expect(page.get_by_text("Settings updated successfully!")).to_be_visible()

    # Capture the final result
    page.screenshot(path="jules-scratch/verification/dashboard_verification.png")

    print("Verification script completed successfully.")
    browser.close()

if __name__ == "__main__":
    with sync_playwright() as p:
        run_verification(p)