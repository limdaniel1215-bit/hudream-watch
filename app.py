import asyncio
import logging
from datetime import date

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import load_config
from hudream import AccessBlocked, HudreamClient, SessionExpired, SiteBackoff, SiteChanged
from storage import Storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("hudream-watch")
cfg = load_config()
store = Storage(cfg.db_path)
client = HudreamClient(cfg.profile_dir, cfg.instltn_no, cfg.sclpst)


async def authorized(update: Update) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or user.id != cfg.allowed_user_id or chat.id != cfg.allowed_chat_id:
        if update.message:
            await update.message.reply_text("허용되지 않은 사용자입니다.")
        return False
    return True


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorized(update): return
    try:
        checkin, nights_text, *room_parts = context.args
        date.fromisoformat(checkin)
        nights = int(nights_text)
        if nights < 1 or nights > 30 or not room_parts: raise ValueError
        watch_id = store.add(cfg.allowed_chat_id, checkin, nights, " ".join(room_parts))
        await update.message.reply_text(f"감시 #{watch_id} 추가 완료")
    except (ValueError, TypeError):
        await update.message.reply_text("사용법: /add YYYY-MM-DD 숙박일수 객실명")


async def listing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorized(update): return
    rows = store.list(cfg.allowed_chat_id)
    text = "\n".join(f"#{w.id} {'ON' if w.enabled else 'OFF'} {w.checkin}~{w.checkout} {w.room_type}" for w in rows) or "감시 조건이 없습니다."
    await update.message.reply_text(text)


def id_handler(action):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await authorized(update): return
        try: watch_id = int(context.args[0])
        except (ValueError, IndexError):
            await update.message.reply_text("ID가 필요합니다."); return
        ok = action(watch_id)
        await update.message.reply_text("완료" if ok else "해당 ID가 없습니다.")
    return handler


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await authorized(update):
        await update.message.reply_text(f"실행 중 · 주기 {cfg.interval_seconds}초 · 활성 {len(store.list(cfg.allowed_chat_id, True))}개")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await authorized(update):
        await update.message.reply_text("/add 날짜 숙박일수 객실명\n/list\n/delete ID\n/start ID\n/stop ID\n/status")


async def watcher(application: Application):
    backoff = cfg.interval_seconds
    transient_failures = 0
    while True:
        watches = store.list(cfg.allowed_chat_id, True)
        groups = {}
        for w in watches:
            groups.setdefault((w.checkin, w.checkout), []).append(w)
        try:
            for key, group in groups.items():
                rooms = await client.check(*key)
                by_name = {r.room_type: r for r in rooms}
                for w in group:
                    room = by_name.get(w.room_type)
                    rcnt, cnt = (room.rcnt, room.cnt) if room else (0, 0)
                    store.record(w.id, rcnt, cnt)
                    log.info("check %s~%s room=%s rcnt=%s cnt=%s", w.checkin, w.checkout, w.room_type, rcnt, cnt)
                    if rcnt > 0 and cnt > 0:
                        await application.bot.send_message(cfg.allowed_chat_id, f"[휴드림 잔여객실 발견]\n시설: 로카우스 나인트리 호텔\n체크인: {w.checkin}\n체크아웃: {w.checkout}\n객실: {w.room_type}\n잔여표시(rcnt): {rcnt}\n예약가능수(cnt): {cnt}\n\n지금 휴드림에서 직접 예약하세요.")
                        if w.notify_once: store.set_enabled(w.chat_id, w.id, False)
            backoff = cfg.interval_seconds
            transient_failures = 0
        except SessionExpired:
            await application.bot.send_message(cfg.allowed_chat_id, "휴드림 로그인 세션이 만료되었습니다. 재로그인이 필요합니다. 감시를 중단합니다.")
            return
        except AccessBlocked:
            log.warning("access blocked; watcher stopped")
            await application.bot.send_message(cfg.allowed_chat_id, "휴드림 접근이 거부되었습니다(HTTP 403). 재로그인 또는 사이트 확인이 필요해 감시를 중단합니다.")
            return
        except SiteChanged as exc:
            log.warning("site flow validation failed: %s", exc)
            await application.bot.send_message(cfg.allowed_chat_id, "휴드림 정상 조회 흐름을 확인할 수 없습니다. 로그인 또는 사이트 변경 여부를 확인해야 해 감시를 중단합니다.")
            return
        except SiteBackoff as exc:
            transient_failures += 1
            backoff = min(max(backoff * 2, 60), 900)
            log.warning("site backoff: %s; next=%ss", exc, backoff)
            if transient_failures >= 3:
                await application.bot.send_message(cfg.allowed_chat_id, "휴드림 과부하 또는 요청 제한이 반복되어 감시를 중단합니다. 잠시 후 수동으로 다시 시작해 주세요.")
                return
        except Exception:
            log.exception("watch cycle failed")
        await asyncio.sleep(backoff)


async def post_init(application: Application):
    await client.start()
    application.create_task(watcher(application))


async def post_shutdown(application: Application):
    await client.close()


def main():
    app = Application.builder().token(cfg.telegram_token).post_init(post_init).post_shutdown(post_shutdown).build()
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", listing))
    app.add_handler(CommandHandler("delete", id_handler(lambda i: store.delete(cfg.allowed_chat_id, i))))
    app.add_handler(CommandHandler("start", id_handler(lambda i: store.set_enabled(cfg.allowed_chat_id, i, True))))
    app.add_handler(CommandHandler("stop", id_handler(lambda i: store.set_enabled(cfg.allowed_chat_id, i, False))))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_cmd))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
