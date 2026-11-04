"""Opt-in real browser test. Set FIELDSHIFT_BROWSER_TEST=1 and install Playwright.

FIELDSHIFT_BROWSER_CHANNEL can select an installed Chromium browser (e.g. msedge).
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

import pytest


@pytest.mark.skipif(os.getenv("FIELDSHIFT_BROWSER_TEST") != "1", reason="opt-in browser check")
def test_map_selects_climate_points_and_pilot_farms():
    from playwright.sync_api import expect, sync_playwright
    expect.set_options(timeout=25000)  # Streamlit streams complex form widgets after the heading.

    root = Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    address = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.address", "127.0.0.1",
         "--server.port", str(port), "--server.headless", "true"], cwd=root,
    )
    try:
        for _ in range(80):
            try:
                with urlopen(address + "/_stcore/health", timeout=1) as response:
                    if response.read() == b"ok":
                        break
            except URLError:
                time.sleep(.25)
        with sync_playwright() as driver:
            browser = driver.chromium.launch(channel=os.getenv("FIELDSHIFT_BROWSER_CHANNEL"))
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            page.set_default_timeout(30000)
            page.goto(address)
            atlas = page.get_by_role("group", name="World location picker")
            page.get_by_role("link", name="Find my field").click()
            atlas.scroll_into_view_if_needed()
            page.get_by_role("button", name="Zoom in", exact=True).click()
            expect(atlas).to_have_attribute("viewBox", "180 90 360 180")
            page.get_by_role("button", name="Zoom out", exact=True).click()
            expect(atlas).to_have_attribute("viewBox", "0 0 720 360")
            size = atlas.bounding_box()
            # A free point near 21 S, 50 W in Brazil, outside the pilot catalogues.
            atlas.click(position={"x": size["width"] * 130 / 360, "y": size["height"] * 111 / 180})
            expect(page.locator(".reticle.scan")).to_be_visible()
            expect(page.locator("output").filter(has_text="Climate location")).to_contain_text("°S")
            expect(page.get_by_role("heading", name="Location report")).to_be_visible()
            if os.getenv("RUN_POWER_INTEGRATION") == "1":
                expect(page.get_by_text("Recorded rainfall", exact=True)).to_be_visible(timeout=60000)
            page.get_by_role("button", name="Explore this location", exact=True).click()
            expect(page.get_by_role("heading", name="Crop calendars", exact=True)).to_be_visible()
            expect(page.get_by_text("calendar combinations.", exact=False)).to_be_visible()
            # Global calendar workspaces share the persistent top-level climate route.
            page.get_by_role("button", name="Climate", exact=True).click()
            expect(page.get_by_role("heading", name="Climate context")).to_be_visible()
            expect(page.get_by_text("Request:", exact=False)).to_contain_text("-")
            expect(page.get_by_role("button", name="Retrieve NASA POWER data", exact=False)).to_be_visible()
            expect(page.get_by_role("button", name="Load saved NASA POWER response", exact=False)).to_have_count(0)
            if os.getenv("RUN_POWER_INTEGRATION") == "1":
                expect(page.get_by_text("Mode: Live NASA POWER API Data", exact=False)).to_be_visible(timeout=60000)
                expect(page.get_by_text("Calculated precipitation total", exact=True)).to_be_visible()
            page.get_by_role("button", name="Compare", exact=True).click()
            expect(page.get_by_role("heading", name="Compare crop sequences")).to_be_visible()
            for pilot_id, lat in (("punjab", "30.901"), ("us_corn_belt", "41.878"),
                                  ("mediterranean", "37.3891"), ("semi_arid_tropics", "19.076")):
                page.get_by_role("button", name="Atlas", exact=True).click()
                page.locator(f'[data-pilot="{pilot_id}"]').focus()
                page.keyboard.press("Enter")
                page.get_by_role("button", name="Open farm profile", exact=True).click()
                expect(page.get_by_label("Latitude (degrees)", exact=True)).to_have_value(lat)
                expect(page.get_by_label("pH (unitless, optional)", exact=True)).to_have_value("")
                page.get_by_role("button", name="Rotations", exact=True).click()
                expect(page.get_by_text("engine-generated alternative(s)", exact=False)).to_be_visible()
                expect(page.locator('[data-testid="stException"]')).to_have_count(0)
            mobile = browser.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
            mobile.goto(address)
            mobile.get_by_role("link", name="Find my field").click()
            mobile.get_by_label("Choose a pilot by name", exact=True).select_option("mediterranean")
            expect(mobile.locator(".reticle")).to_have_css("animation-name", "none")
            assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
            if os.getenv("FIELDSHIFT_UI_PREVIEWS") == "1":
                previews = root / "outputs"
                previews.mkdir(exist_ok=True)
                mobile.screenshot(path=previews / "atlas-mobile.png")
                page.get_by_role("button", name="Atlas", exact=True).click()
                page.get_by_role("heading", name="What will you grow next?").scroll_into_view_if_needed()
                page.screenshot(path=previews / "atlas-desktop.png")
            mobile.get_by_role("button", name="Open farm profile", exact=True).click()
            expect(mobile.get_by_label("Latitude (degrees)", exact=True)).to_have_value("37.3891")
            mobile.get_by_role("button", name="Menu", exact=True).click()
            expect(mobile.get_by_role("combobox", name="Pages")).to_be_visible()
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=15)
