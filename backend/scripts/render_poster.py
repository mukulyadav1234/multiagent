import asyncio
import sys
from pathlib import Path
from typing import List
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# Only Google Fonts may load; every other request is blocked so the render stays sandboxed.
ALLOWED_HOSTS = ("https://fonts.googleapis.com/", "https://fonts.gstatic.com/")


async def _route(route, request):
    if request.url.startswith(ALLOWED_HOSTS) or request.url.startswith("data:"):
        await route.continue_()
    else:
        await route.abort()


async def render_html_to_png_async(html: str, out_path: Path, width: int, height: int, format: str = "png", scale: float = 2) -> List[str]:
    """Render `html` to png/jpeg/pdf at `scale` x device pixels. Returns browser console errors."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    errors: List[str] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=scale,
            java_script_enabled=True,
            # The corporate TLS proxy re-signs Google Fonts; nothing else is reachable anyway.
            ignore_https_errors=True,
        )
        await context.route("**/*", _route)

        page = await context.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "net::ERR" not in m.text else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        try:
            await page.set_content(html, wait_until="networkidle", timeout=60000)
            try:
                await page.wait_for_function("window.__POSTER_READY === true", timeout=15000)
            except PWTimeout:
                errors.append("window.__POSTER_READY was never set (script missing or crashed)")
            # Faces load lazily on first use, so fonts.ready alone can resolve before they arrive.
            await page.evaluate("""Promise.race([
                Promise.allSettled([...document.fonts].map(f => f.load())),
                new Promise(r => setTimeout(r, 15000))
            ]).then(() => document.fonts.ready)
              .then(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))))""")

            clip = {"x": 0, "y": 0, "width": width, "height": height}
            if format == "png":
                await page.screenshot(path=str(out_path), clip=clip, timeout=120000)
            elif format == "jpeg":
                await page.screenshot(path=str(out_path), type="jpeg", quality=95, clip=clip, timeout=120000)
            elif format == "pdf":
                await page.pdf(path=str(out_path), width=f"{width}px", height=f"{height}px", print_background=True, page_ranges="1")
            else:
                raise ValueError("Unsupported format")
        except PWTimeout:
            raise RuntimeError("Rendering timed out")
        finally:
            await context.close()
            await browser.close()
    return errors


def render_html_to_png(html: str, out_path: Path, width: int, height: int, format: str = "png", scale: float = 2) -> List[str]:
    return asyncio.run(render_html_to_png_async(html, out_path, width, height, format=format, scale=scale))


if __name__ == "__main__":
    html_file = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    width = int(sys.argv[3])
    height = int(sys.argv[4])
    fmt = sys.argv[5] if len(sys.argv) > 5 else "png"
    scale = float(sys.argv[6]) if len(sys.argv) > 6 else 2
    html = html_file.read_text(encoding="utf-8")
    print(asyncio.run(render_html_to_png_async(html, out_path, width, height, format=fmt, scale=scale)))
