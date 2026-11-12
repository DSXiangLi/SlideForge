"""无头渲染 24 张试点页：逐张 bounding-box 截图，命名 PILOT-<theme>-<page>.png，并报告越界元素。"""
import os
from playwright.sync_api import sync_playwright

ANALYSIS = r"C:\Users\lixiang\Desktop\SlideForge\analysis"
URL = "file:///" + os.path.join(ANALYSIS, "dna-pilot.html").replace("\\", "/")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 2160, "height": 2400}, device_scale_factor=2)
    page.goto(URL, wait_until="load")
    page.wait_for_timeout(400)

    slides = page.locator(".slide")
    n = slides.count()
    print("SLIDE_COUNT", n)
    for i in range(n):
        el = slides.nth(i)
        theme = el.get_attribute("data-theme")
        pg = el.get_attribute("data-page")
        path = os.path.join(ANALYSIS, "PILOT-%s-%s.png" % (theme, pg))
        el.screenshot(path=path)

    overflow = page.evaluate("""() => {
      const out = [];
      document.querySelectorAll('.slide').forEach((s) => {
        const r = s.getBoundingClientRect();
        s.querySelectorAll('*').forEach(e => {
          const b = e.getBoundingClientRect();
          if (b.width === 0 && b.height === 0) return;
          if (b.bottom > r.bottom + 2 || b.right > r.right + 2 || b.top < r.top - 2 || b.left < r.left - 2) {
            out.push([s.getAttribute('data-theme'), s.getAttribute('data-page'), e.className || e.tagName,
                      Math.round(b.top-r.top), Math.round(b.left-r.left), Math.round(b.bottom-r.bottom), Math.round(b.right-r.right)]);
          }
        });
      });
      return out;
    }""")
    print("OUT_OF_BOUNDS", overflow)
    import json
    with open(os.path.join(ANALYSIS, "_render_report.json"), "w", encoding="utf-8") as f:
        json.dump({"slide_count": n, "overflow": overflow}, f, ensure_ascii=False, indent=2)
    browser.close()
