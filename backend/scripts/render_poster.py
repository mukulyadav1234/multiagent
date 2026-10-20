import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeout


async def render_html_to_png_async(html: str, out_path: Path, width: int, height: int, format: str = "png") -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            java_script_enabled=True,
        )

        # Keep the render sandboxed: block all network requests while still allowing
        # inline JavaScript and SVG/CSS animation within the rendered page itself.
        await context.route("**/*", lambda route, request: route.abort())

        page = await context.new_page()
        await page.set_viewport_size({"width": width, "height": height})
        await page.set_content(html, wait_until="networkidle")
        try:
            if format == "png":
                await page.screenshot(path=str(out_path), clip={"x": 0, "y": 0, "width": width, "height": height})
            elif format == "jpeg":
                await page.screenshot(path=str(out_path), type="jpeg", quality=90, clip={"x": 0, "y": 0, "width": width, "height": height})
            elif format == "pdf":
                await page.pdf(path=str(out_path), width=f"{width}px", height=f"{height}px")
            else:
                raise ValueError("Unsupported format")
        except PWTimeout:
            raise RuntimeError("Rendering timed out")
        finally:
            await context.close()
            await browser.close()


def render_html_to_png(html: str, out_path: Path, width: int, height: int, format: str = "png") -> None:
    asyncio.run(render_html_to_png_async(html, out_path, width, height, format=format))


if __name__ == "__main__":
    html_file = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    width = int(sys.argv[3])
    height = int(sys.argv[4])
    fmt = sys.argv[5] if len(sys.argv) > 5 else "png"
    html = html_file.read_text(encoding="utf-8")
    asyncio.run(render_html_to_png_async(html, out_path, width, height, format=fmt))
