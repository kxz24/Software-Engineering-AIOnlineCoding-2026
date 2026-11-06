/**
 * 时间格式化工具。
 * 后端返回带时区的 ISO 字符串（Asia/Shanghai），这里转成本地展示文案；
 * datetime-local 输入框需要「YYYY-MM-DD HH:mm」格式，见 toInputValue。
 */

/** 补零 */
function pad(value: number): string {
    return String(value).padStart(2, "0");
}

function parse(iso: string | null | undefined): Date | null {
    if (!iso) {
        return null;
    }
    const date = new Date(iso);
    return isNaN(date.getTime()) ? null : date;
}

/** 完整时间：「2026-11-08 09:00」 */
export function formatDateTime(iso: string | null | undefined): string {
    const date = parse(iso);
    if (!date) {
        return "—";
    }
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
        `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** 短时间（列表用）：「11-08 09:00」 */
export function formatShort(iso: string | null | undefined): string {
    const date = parse(iso);
    if (!date) {
        return "—";
    }
    return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** 时间段：「11-08 09:00–11:00」 */
export function formatPeriod(startIso: string | null, endIso: string | null): string {
    const start = parse(startIso);
    const end = parse(endIso);
    if (!start || !end) {
        return "时间待定";
    }
    const sameDay = start.toDateString() === end.toDateString();
    const startText = `${pad(start.getMonth() + 1)}-${pad(start.getDate())} ${pad(start.getHours())}:${pad(start.getMinutes())}`;
    const endText = sameDay
        ? `${pad(end.getHours())}:${pad(end.getMinutes())}`
        : `${pad(end.getMonth() + 1)}-${pad(end.getDate())} ${pad(end.getHours())}:${pad(end.getMinutes())}`;
    return `${startText}–${endText}`;
}

/** ISO → datetime-local 输入框的值：「2026-11-08T09:00」（原生控件要求 T 分隔） */
export function toInputValue(iso: string | null | undefined): string {
    const date = parse(iso);
    if (!date) {
        return "";
    }
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
        `T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** 距目标时刻的秒数（已过为 0） */
export function secondsUntil(iso: string | null | undefined, now: number = Date.now()): number {
    const date = parse(iso);
    if (!date) {
        return 0;
    }
    return Math.max(0, Math.floor((date.getTime() - now) / 1000));
}

/** 剩余秒数 → 「01:23:45」或超过 24 小时的「1 天 03:12:22」 */
export function formatCountdown(seconds: number): string {
    const total = Math.max(0, Math.floor(seconds));
    const days = Math.floor(total / 86400);
    const rest = total - days * 86400;
    const h = pad(Math.floor(rest / 3600));
    const m = pad(Math.floor((rest % 3600) / 60));
    const s = pad(rest % 60);
    const clock = `${h}:${m}:${s}`;
    return days > 0 ? `${days} 天 ${clock}` : clock;
}

/** 今天的日期文案：「11月4日 周三」 */
export function formatToday(now: Date = new Date()): string {
    const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
    return `${now.getMonth() + 1}月${now.getDate()}日 ${weekdays[now.getDay()]}`;
}
