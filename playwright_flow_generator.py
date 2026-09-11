import asyncio
import os
import sys
import time
import shutil
import hashlib
import subprocess
from playwright.async_api import async_playwright

PROFILES = [
    r"D:\youtube_automation_agent\.gflow\profiles\acc4",
    r"D:\youtube_automation_agent\.gflow\profiles\acc3",
    r"D:\youtube_automation_agent\.gflow\profiles\acc2",
]

PROJECT_IDS = {
    "acc4": "f32c61d3-c1ff-42a7-8b4a-492b63591811",
    "acc3": "8f2fb080-2b43-49c9-8882-7bb66e812d6d",
    "acc2": "04011aab-afc8-4105-8a89-cf1d8fccbbeb",
}

_LAST_PROFILE_IDX = 0
_PROFILE_COOLDOWNS = {}  # {profile_path: cooldown_until_timestamp}

def _kill_profile_processes(prof_dir: str):
    """Terminates any orphan background Chrome processes locking this specific profile."""
    try:
        prof_name = os.path.basename(prof_dir)
        subprocess.run([
            "powershell", "-NoProfile", "-Command",
            f"Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
            f"Where-Object {{$_.CommandLine -like '*{prof_name}*'}} | "
            f"ForEach-Object {{Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue}}"
        ], capture_output=True, timeout=5)
    except Exception:
        pass

def _clean_profile_locks(prof_dir: str):
    """Removes stale Chromium Singleton locks to avoid ProcessSingleton collisions."""
    _kill_profile_processes(prof_dir)
    for lf in ["SingletonLock", "SingletonCookie", "SingletonSocket", "DevToolsActivePort", "lockfile", "LOCK"]:
        lp = os.path.join(prof_dir, lf)
        if os.path.exists(lp):
            try:
                os.remove(lp)
            except Exception:
                pass

async def _dismiss_modals(page):
    """Dismisses Google Flow's new changelog/announcement modal dialogs."""
    try:
        modal_btns = page.locator('button:has-text("Get started"), button:has-text("Start Creating"), button:has-text("Start creating"), button:has-text("Dismiss"), button:has-text("Got it"), button:has-text("close"), [aria-label="Close"], [aria-label="close"], [aria-label="Dismiss"]')
        for _ in range(3):
            if await modal_btns.count() and await modal_btns.first.is_visible():
                await modal_btns.first.click()
                await asyncio.sleep(0.5)
            else:
                break
    except Exception:
        pass

async def _clean_failed_cards(page):
    """Clears any error/failed cards from canvas so they don't block new generations."""
    try:
        del_btns = page.locator('button:has(span:has-text("delete_forever")), button:has(span:has-text("delete"))')
        for _ in range(5):
            if await del_btns.count():
                try:
                    await del_btns.first.click()
                    await asyncio.sleep(0.5)
                except Exception:
                    break
            else:
                break
    except Exception:
        pass

async def _ensure_image_mode(page):
    """Ensures Google Flow prompt box is set to Image mode (not Video mode)."""
    try:
        settings_btn = page.locator('button[aria-label="Settings trigger"]').first
        if await settings_btn.count():
            btn_text = (await settings_btn.inner_text()).lower()
            if "video" in btn_text:
                print("[Playwright Flow] Switching from Video mode to Image mode...", flush=True)
                await settings_btn.click()
                await asyncio.sleep(0.5)
                img_tab = page.locator('button:has-text("Image"), [role="menuitem"]:has-text("Image")').first
                if await img_tab.count():
                    await img_tab.click()
                    await asyncio.sleep(0.5)
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.5)
    except Exception as e:
        print(f"[Playwright Flow] Warning ensuring image mode: {e}", flush=True)

async def _ensure_nano_banana_2(page):
    """Ensures Google Flow prompt box is using Nano Banana 2 (which has available quota)."""
    try:
        pill = page.locator('button:has-text("Nano Banana"), span:has-text("Nano Banana")').last
        if await pill.count():
            pill_text = await pill.inner_text()
            if "Nano Banana 2" not in pill_text or "Pro" in pill_text:
                print(f"[Playwright Flow] Switching model to Nano Banana 2...", flush=True)
                settings_btn = page.locator('button[aria-label="Settings trigger"], button:has-text("Nano Banana")').first
                await settings_btn.click()
                await asyncio.sleep(0.8)
                
                model_btn = page.locator('button:has(span.model-select-trigger-content), span.model-select-trigger-content, button[aria-label="Select model family"]').first
                if await model_btn.count() and await model_btn.is_visible():
                    await model_btn.click()
                    await asyncio.sleep(0.8)
                    nb2_opt = page.locator('mat-option:has-text("Nano Banana 2"):not(:has-text("Lite")), [role="menuitem"]:has-text("Nano Banana 2"):not(:has-text("Lite")), button:has-text("Nano Banana 2"):not(:has-text("Lite"))').first
                    if await nb2_opt.count() and await nb2_opt.is_visible():
                        await nb2_opt.click()
                        print("[Playwright Flow] Selected Nano Banana 2 successfully!", flush=True)
                        await asyncio.sleep(0.5)
                        
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.4)
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.4)
    except Exception as e:
        print(f"[Playwright Flow] Warning ensuring Nano Banana 2: {e}", flush=True)

async def _generate_async(prompt: str, output_path: str, aspect_ratio: str = "16:9") -> bool:
    global _LAST_PROFILE_IDX
    abs_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    now = time.time()
    rotated = PROFILES[_LAST_PROFILE_IDX:] + PROFILES[:_LAST_PROFILE_IDX]
    ready = [p for p in rotated if _PROFILE_COOLDOWNS.get(p, 0) <= now]
    cooling = [p for p in rotated if _PROFILE_COOLDOWNS.get(p, 0) > now]
    profiles_order = ready + cooling

    for prof in profiles_order:
        prof_name = os.path.basename(prof)
        print(f"[Playwright Flow] Using profile: {prof_name}...", flush=True)

        _clean_profile_locks(prof)
        await asyncio.sleep(0.5)

        context = None
        try:
            async with async_playwright() as p:
                real_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=prof,
                    headless=True,
                    channel="chrome",
                    user_agent=real_ua,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )
                page = context.pages[0] if context.pages else await context.new_page()
                page.set_default_timeout(35000)

                proj_id = PROJECT_IDS.get(prof_name)
                target_url = f"https://flow.google.com/project/{proj_id}" if proj_id else "https://flow.google.com"
                await page.goto(target_url, timeout=35000)
                await asyncio.sleep(1)
                await _dismiss_modals(page)

                if "/project/" not in page.url:
                    item = page.locator("a[href*='/project/']").first
                    await item.wait_for(state="visible", timeout=20000)
                    await item.click()
                    await asyncio.sleep(2)

                print(f"[Playwright Flow] {prof_name} active project URL: {page.url}", flush=True)

                await _dismiss_modals(page)
                await _ensure_image_mode(page)
                await _ensure_nano_banana_2(page)
                await _clean_failed_cards(page)

                editor = page.locator('div.ProseMirror[contenteditable="true"]').first
                await editor.wait_for(state="visible", timeout=25000)

                before_urls = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('img'))
                        .filter(i => (i.naturalWidth > 400 || i.width > 400) && i.src)
                        .map(i => i.currentSrc || i.src);
                }""")
                before_urls_set = set(before_urls)

                await editor.click()
                await asyncio.sleep(0.3)
                await page.keyboard.press("ControlOrMeta+a")
                await page.keyboard.press("Backspace")
                await page.keyboard.insert_text(prompt)
                await asyncio.sleep(0.8)

                arrow_btn = page.locator('button[aria-label="Start generation"], button.generate-icon-button, button:has(span:has-text("arrow_forward")), button:has-text("arrow_forward")').first
                clicked = False
                try:
                    await arrow_btn.wait_for(state="visible", timeout=3000)
                    for _ in range(10):
                        if await arrow_btn.is_enabled():
                            break
                        await asyncio.sleep(0.2)
                    if await arrow_btn.is_enabled():
                        await arrow_btn.click()
                        clicked = True
                except Exception:
                    pass

                if not clicked:
                    await page.keyboard.press("ControlOrMeta+Enter")

                print(f"[Playwright Flow] Submitted prompt on {prof_name}. Polling for render...", flush=True)

                t_poll = time.time()
                seen_placeholder = False

                for attempt in range(40):
                    await asyncio.sleep(2)
                    elapsed = time.time() - t_poll

                    status = await page.evaluate("""(known) => {
                        const knownSet = new Set(known);
                        const imgs = Array.from(document.querySelectorAll('img'))
                            .filter(i => (i.naturalWidth > 400 || i.width > 400) && i.src);
                        const placeholders = Array.from(document.querySelectorAll('*')).filter(e => {
                            const txt = e.innerText || '';
                            return txt.includes('%') && e.offsetHeight > 50 && e.offsetWidth > 50;
                        });
                        const brandNew = imgs.find(i => !knownSet.has(i.currentSrc || i.src));
                        return {
                            brand_new_url: brandNew ? (brandNew.currentSrc || brandNew.src) : null,
                            top_url: imgs.length > 0 ? (imgs[0].currentSrc || imgs[0].src) : null,
                            count: imgs.length,
                            placeholders: placeholders.length
                        };
                    }""", before_urls)

                    if status['placeholders'] > 0:
                        seen_placeholder = True

                    if attempt % 5 == 0:
                        print(f"[{elapsed:.0f}s] Poll {attempt+1}: {status['count']} canvas imgs, {status['placeholders']} generating placeholders", flush=True)

                    target_url = status['brand_new_url']
                    if not target_url and status['top_url'] and status['top_url'] not in before_urls_set:
                        target_url = status['top_url']

                    if target_url and status['placeholders'] == 0:
                        bytes_arr = await page.evaluate("""async (url) => {
                            const res = await fetch(url);
                            if (!res.ok) return null;
                            const buf = await res.arrayBuffer();
                            return Array.from(new Uint8Array(buf));
                        }""", target_url)

                        if bytes_arr and len(bytes_arr) > 20000:
                            raw_bytes = bytearray(bytes_arr)
                            with open(abs_path, "wb") as f:
                                f.write(raw_bytes)
                            print(f"[Playwright Flow] SUCCESS! Saved ({len(raw_bytes)/1024:.1f} KB) in {elapsed:.1f}s -> {os.path.basename(abs_path)}", flush=True)
                            _LAST_PROFILE_IDX = (PROFILES.index(prof) + 1) % len(PROFILES)
                            _PROFILE_COOLDOWNS.pop(prof, None)
                            await context.close()
                            _clean_profile_locks(prof)
                            return True

                    # Check for explicit failure / usage limit card
                    failed_card = await page.evaluate("""() => {
                        const texts = Array.from(document.querySelectorAll('*')).map(e => e.innerText || '');
                        return texts.some(t => t.includes('usage limit') || (t.includes('Failed') && t.includes('Please try again')));
                    }""")
                    if failed_card and elapsed >= 3:
                        print(f"[Playwright Flow] ⚠️ Google Flow Rate limit / Unusual Activity detected on {prof_name}. Rotating...", flush=True)
                        _PROFILE_COOLDOWNS[prof] = time.time() + 180
                        await _clean_failed_cards(page)
                        break

                    # Detection:
                    # 1. If we never saw any placeholder and elapsed >= 18s:
                    if elapsed >= 18 and not seen_placeholder and not target_url:
                        print(f"[Playwright Flow] ⚠️ Generation idle / not started on {prof_name} after {elapsed:.0f}s. Rotating...", flush=True)
                        _PROFILE_COOLDOWNS[prof] = time.time() + 45
                        await _clean_failed_cards(page)
                        break

                    # 2. If we saw a placeholder, but it vanished with 0 placeholders and no new image AFTER at least 25s:
                    if seen_placeholder and status['placeholders'] == 0 and not target_url and elapsed >= 25:
                        print(f"[Playwright Flow] ⚠️ Generation card disappeared without image on {prof_name} after {elapsed:.0f}s. Rotating...", flush=True)
                        _PROFILE_COOLDOWNS[prof] = time.time() + 45
                        await _clean_failed_cards(page)
                        break

                _PROFILE_COOLDOWNS[prof] = time.time() + 45
                await context.close()
                _clean_profile_locks(prof)
        except Exception as e:
            print(f"[Playwright Flow] Error on {prof_name}: {e}", flush=True)
            _PROFILE_COOLDOWNS[prof] = time.time() + 300
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            _clean_profile_locks(prof)

    return False

def generate_image_playwright(prompt: str, output_path: str, aspect_ratio: str = "16:9") -> bool:
    """Synchronous entry point to generate image via Playwright Google Flow."""
    try:
        return asyncio.run(_generate_async(prompt, output_path, aspect_ratio))
    except Exception as e:
        print(f"[Playwright Flow Exception]: {e}", flush=True)
        return False
