"""无头浏览器真值渲染：整页校验 + 逐张 DNA 演示页截图。"""
import os
from playwright.sync_api import sync_playwright

ANALYSIS = os.path.dirname(os.path.abspath(__file__))
URL = "file:///" + os.path.join(ANALYSIS, "dna-soul.html").replace("\\", "/")
NAMES = ["b1", "e5", "c3", "h1"]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
    page.goto(URL, wait_until="load")
    page.wait_for_timeout(500)

    imgs = page.evaluate("""() => Array.from(document.querySelectorAll('img')).map(
        i => [i.getAttribute('src'), i.naturalWidth, i.naturalHeight])""")
    print("IMAGES", imgs)
    print("BLIND_BTN", page.locator("#btnBlind").inner_text())

    slides = page.locator(".grid > .card > .slide")
    print("SLIDE_COUNT", slides.count())
    for i, name in enumerate(NAMES):
        el = slides.nth(i)
        box = el.bounding_box()
        path = os.path.join(ANALYSIS, "DNA-0%d-%s.png" % (i + 1, name))
        el.screenshot(path=path)
        print("SHOT", path, "BOX", box)

    # 检查每个 slide 内是否有元素越过画布
    overflow = page.evaluate("""() => {
      const out = [];
      document.querySelectorAll('.grid > .card > .slide').forEach((s, i) => {
        const r = s.getBoundingClientRect();
        s.querySelectorAll('*').forEach(e => {
          const b = e.getBoundingClientRect();
          if (b.width === 0 && b.height === 0) return;
          if (b.bottom > r.bottom + 2 || b.right > r.right + 2 || b.top < r.top - 2 || b.left < r.left - 2) {
            out.push([i, e.className || e.tagName, Math.round(b.top-r.top), Math.round(b.left-r.left), Math.round(b.bottom-r.bottom), Math.round(b.right-r.right)]);
          }
        });
      });
      return out.slice(0, 30);
    }""")
    print("OUT_OF_BOUNDS", overflow)

    page.screenshot(path=os.path.join(ANALYSIS, "_full.png"), full_page=True)
    # 盲测态整页截图
    page.locator("#btnBlind").click()
    page.wait_for_timeout(250)
    page.locator(".grid").screenshot(path=os.path.join(ANALYSIS, "DNA-盲测对照.png"))
    browser.close()
