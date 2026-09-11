import asyncio
import time
import os
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

async def test_nb2():
    prof = r"D:\youtube_automation_agent\.gflow\profiles\acc4"
    proj_id = "f32c61d3-c1ff-42a7-8b4a-492b63591811"
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=prof,
            headless=True,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_timeout(35000)
        
        target_url = f"https://flow.google.com/project/{proj_id}"
        print(f"Navigating to {target_url}...")
        await page.goto(target_url, timeout=35000)
        await asyncio.sleep(2)
        
        # Dismiss any modals
        for _ in range(3):
            close_btn = page.locator('button:has-text("Dismiss"), button:has-text("Got it"), button:has-text("close"), [aria-label="Close"]').first
            if await close_btn.count() and await close_btn.is_visible():
                await close_btn.click()
                await asyncio.sleep(0.5)
                
        # Clean failed cards
        del_btns = page.locator('button:has(span:has-text("delete_forever")), button:has(span:has-text("delete"))')
        for _ in range(await del_btns.count()):
            try:
                await del_btns.first.click()
                await asyncio.sleep(0.3)
            except Exception:
                break

        # Check model: look for model trigger or pill
        pill = page.locator('button:has-text("Nano Banana"), span:has-text("Nano Banana")').last
        if await pill.count():
            pill_text = await pill.inner_text()
            print(f"Current model indicator: {pill_text}")
            if "Nano Banana 2" not in pill_text or "Pro" in pill_text:
                print("Switching to Nano Banana 2...")
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
                        print("Selected Nano Banana 2!")
                        await asyncio.sleep(0.5)
                        
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.5)
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.5)

        if await pill.count():
            print("Model indicator after switch:", await pill.inner_text())

        prompt_file = r"D:\youtube_automation_agent\channels\history\The_Man_Who_Hid_Inside_a_Giant_Jar_During_an_Ancie_2026-09-08_154017\05_Image_Prompts\Scene_106_Prompt.txt"
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
            
        editor = page.locator('div.ProseMirror[contenteditable="true"]').first
        await editor.wait_for(state="visible", timeout=15000)
        
        before_urls = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img'))
                .filter(i => (i.naturalWidth > 400 || i.width > 400) && i.src)
                .map(i => i.currentSrc || i.src);
        }""")
        print(f"Canvas images before: {len(before_urls)}")
        
        await editor.click()
        await asyncio.sleep(0.3)
        await page.keyboard.press("ControlOrMeta+a")
        await page.keyboard.press("Backspace")
        await page.keyboard.insert_text(prompt)
        await asyncio.sleep(0.8)
        
        arrow_btn = page.locator('button[aria-label="Start generation"], button.generate-icon-button, button:has(span:has-text("arrow_forward")), button:has-text("arrow_forward")').first
        clicked = False
        if await arrow_btn.count() and await arrow_btn.is_enabled():
            await arrow_btn.click()
            clicked = True
            print("Clicked generate arrow button!")
        if not clicked:
            print("Pressing Ctrl+Enter...")
            await page.keyboard.press("ControlOrMeta+Enter")
            
        print("Prompt submitted! Polling for render...")
        t_poll = time.time()
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
                const texts = Array.from(document.querySelectorAll('*')).map(e => e.innerText || '');
                const hasUsageLimit = texts.some(t => t.includes('usage limit') || (t.includes('Failed') && t.includes('Please try again')));
                return {
                    brand_new_url: brandNew ? (brandNew.currentSrc || brandNew.src) : null,
                    top_url: imgs.length > 0 ? (imgs[0].currentSrc || imgs[0].src) : null,
                    count: imgs.length,
                    placeholders: placeholders.length,
                    has_limit: hasUsageLimit
                };
            }""", before_urls)
            
            print(f"[{elapsed:.0f}s] Imgs: {status['count']}, Placeholders: {status['placeholders']}, Limit error: {status['has_limit']}")
            
            if status['has_limit'] and elapsed >= 4:
                print("Usage limit error detected!")
                break
                
            target_url = status['brand_new_url']
            if not target_url and status['top_url'] and status['top_url'] not in set(before_urls):
                target_url = status['top_url']
                
            if target_url and status['placeholders'] == 0:
                bytes_arr = await page.evaluate("""async (url) => {
                    const res = await fetch(url);
                    if (!res.ok) return null;
                    const buf = await res.arrayBuffer();
                    return Array.from(new Uint8Array(buf));
                }""", target_url)
                if bytes_arr and len(bytes_arr) > 20000:
                    out = r"D:\youtube_automation_agent\channels\history\The_Man_Who_Hid_Inside_a_Giant_Jar_During_an_Ancie_2026-09-08_154017\06_Images\106_Scene_106.png"
                    with open(out, "wb") as f:
                        f.write(bytearray(bytes_arr))
                    print(f"SUCCESS! Saved Scene 106 ({len(bytes_arr)/1024:.1f} KB) in {elapsed:.1f}s")
                    break

        await context.close()

asyncio.run(test_nb2())
