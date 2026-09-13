import asyncio
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, async_playwright

MAIN_URL = "https://welfare.army.mil.kr/main.do"
ROOM_URL = "https://welfare.army.mil.kr/ro/room.do"


class SessionExpired(RuntimeError):
    pass


class SiteBackoff(RuntimeError):
    pass


class AccessBlocked(RuntimeError):
    pass


class SiteChanged(RuntimeError):
    pass


@dataclass(frozen=True)
class Room:
    room_type: str
    rcnt: int
    cnt: int


def parse_search_response(data: object) -> list[Room]:
    if not isinstance(data, dict):
        raise SiteChanged("search response is not a JSON object")
    if data.get("msg") == 1:
        raise SiteBackoff("site overload response")
    items = data.get("list")
    if not isinstance(items, list):
        raise SiteChanged("search response does not contain a room list")

    rooms = []
    for item in items:
        if not isinstance(item, dict):
            continue
        room_type = str(item.get("qrtrs_type") or "").strip()
        if not room_type:
            continue
        try:
            rooms.append(Room(room_type, int(item.get("rcnt") or 0), int(item.get("cnt") or 0)))
        except (TypeError, ValueError) as exc:
            raise SiteChanged(f"invalid room counts for {room_type}") from exc
    return rooms


class HudreamClient:
    def __init__(self, profile_dir: Path, instltn_no: str, sclpst: str):
        self.profile_dir = profile_dir
        self.instltn_no = instltn_no
        self.sclpst = sclpst
        self._pw = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.lock = asyncio.Lock()

    async def start(self):
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.profile_dir.chmod(0o700)
        self._pw = await async_playwright().start()
        self.context = await self._pw.chromium.launch_persistent_context(
            str(self.profile_dir), headless=True, viewport={"width": 1280, "height": 900}
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

    async def close(self):
        if self.context:
            await self.context.close()
        if self._pw:
            await self._pw.stop()

    async def check(self, checkin: str, checkout: str) -> list[Room]:
        if not self.page:
            raise RuntimeError("client not started")
        async with self.lock:
            room_url = f"{ROOM_URL}?instltn_no={self.instltn_no}"
            response = await self.page.goto(room_url, wait_until="domcontentloaded", timeout=45_000)
            if response and response.status in (403, 429, 503):
                if response.status == 403:
                    raise AccessBlocked("HTTP 403")
                raise SiteBackoff(f"HTTP {response.status}")
            if "/login" in self.page.url.lower():
                raise SessionExpired("login session is unavailable")
            if await self.page.locator("#sclpst").count() == 0:
                raise SiteChanged("identity selector not found; login or site UI must be checked")

            try:
                await self.page.locator("#sclpst").select_option(self.sclpst)
                await self.page.locator("#sclpst").dispatch_event("change")
                await self.page.wait_for_timeout(800)
                await self.page.locator("#datepicker").fill(checkin)
                await self.page.locator("#datepicker").dispatch_event("change")
                await self.page.locator("#datepicker2").fill(checkout)
                await self.page.locator("#datepicker2").dispatch_event("change")
                for selector in ("#use_guide", "#indv_info_prcss_agr", "#refnd"):
                    if await self.page.locator(selector).count():
                        await self.page.locator(selector).check()

                button = self.page.locator('[onclick*="formCheck"]').first
                if await button.count() == 0:
                    raise SiteChanged("search button not found; site UI may have changed")

                self.page.once("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
                async with self.page.expect_response(
                    lambda item: item.url.endswith("/ro/search_ajax.do"), timeout=15_000
                ) as response_info:
                    await button.click()
                search_response = await response_info.value
                status = search_response.status
                if status in (403, 429, 503):
                    if status == 403:
                        raise AccessBlocked("HTTP 403")
                    raise SiteBackoff(f"HTTP {status}")
                try:
                    data = await search_response.json()
                except Exception as exc:
                    content_type = (await search_response.header_value("content-type") or "").lower()
                    if "text/html" in content_type:
                        raise SessionExpired("search returned HTML; login may have expired") from exc
                    raise SiteChanged("search did not return JSON") from exc
                return parse_search_response(data)
            except PlaywrightTimeoutError as exc:
                raise SiteChanged("normal search flow did not produce a response") from exc
