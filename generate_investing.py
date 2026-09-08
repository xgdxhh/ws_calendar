#!/usr/bin/env python

import html
import json
import re
import subprocess
import time
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path
import uuid
from zoneinfo import ZoneInfo

import pandas as pd


API_URL = "https://rp.icealtria.workers.dev/https://endpoints.investing.com/pd-instruments/v1/calendars/economic/events/occurrences"
CALENDAR_TZ = ZoneInfo("Asia/Shanghai")
COUNTRY_ID_MAP = {37: "中国", 5: "美国", 17: "德国", 35: "日本"}
IMPORTANCE_MAP = {"high": 3, "medium": 2, "low": 1}
IMPORTANCE_LABELS = {3: "高", 2: "中", 1: "低"}
COUNTRIES = [
    (None, "全球", "investing_calendar_{threshold}.ics"),
    ("美国", "美国", "investing_calendar_us_{threshold}.ics"),
    ("中国", "中国", "investing_calendar_cn_{threshold}.ics"),
]
THRESHOLDS = [3, 2, 1]


def build_date_range(reference: date | None = None) -> tuple[date, date]:
    today = reference or datetime.now(CALENDAR_TZ).date()
    start_day = today - timedelta(days=20)
    end_day = today + timedelta(days=60)
    return start_day, end_day


def fetch_investing_calendar(
    start_day: date, end_day: date, max_retries: int = 3
) -> pd.DataFrame:
    all_events = []
    all_occurrences = []
    cursor = None

    while True:
        params = [
            ("domain_id", "6"),
            ("limit", "200"),
            ("start_date", f"{start_day}T00:00:00.000+08:00"),
            ("end_date", f"{end_day}T23:59:59.999+08:00"),
            ("country_ids", "37,5,17,35"),
        ]
        if cursor:
            params.append(("cursor", cursor))

        query_parts = []
        for k, v in params:
            if k in ("start_date", "end_date"):
                query_parts.append(f"{k}={urllib.parse.quote(v, safe='')}")
            else:
                query_parts.append(f"{k}={v}")
        url = f"{API_URL}?{'&'.join(query_parts)}"

        last_error = None
        for attempt in range(max_retries):
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    url,
                    "-H",
                    "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "-H",
                    "Accept: application/json, text/plain, */*",
                    "-H",
                    "Referer: https://investing.com/economic-calendar/",
                    "-H",
                    "Origin: https://investing.com",
                    "--max-time",
                    "30",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                last_error = RuntimeError(f"curl failed: {result.stderr}")
                time.sleep(2**attempt)
                continue

            if not result.stdout.strip():
                last_error = ValueError("Empty response")
                time.sleep(2**attempt)
                continue

            try:
                payload = json.loads(result.stdout)
                break
            except json.JSONDecodeError as e:
                last_error = e
                time.sleep(2**attempt)
                continue
        else:
            raise RuntimeError(f"Failed after {max_retries} retries: {last_error}")
        all_events.extend(payload.get("events", []))
        all_occurrences.extend(payload.get("occurrences", []))
        cursor = payload.get("next_page_cursor")
        if not cursor:
            break

    event_map = {e["event_id"]: e for e in all_events}

    rows = []
    for occ in all_occurrences:
        event_id = occ.get("event_id")
        event_meta = event_map.get(event_id, {})
        country_id = event_meta.get("country_id")
        importance_str = event_meta.get("importance", "low")
        importance_value = IMPORTANCE_MAP.get(importance_str, 1)
        country_name = COUNTRY_ID_MAP.get(country_id, f"ID:{country_id}")

        occ_time_str = occ.get("occurrence_time", "")
        if not occ_time_str:
            continue
        try:
            occ_time_utc = datetime.fromisoformat(occ_time_str.replace("Z", "+00:00"))
            occ_time = occ_time_utc.astimezone(CALENDAR_TZ)
        except (ValueError, TypeError):
            continue

        unit = occ.get("unit", "")
        actual = occ.get("actual")
        forecast = occ.get("forecast")
        previous = occ.get("previous")

        event_translated = event_meta.get("event_translated", "")
        long_name = event_meta.get("long_name", "")
        short_name = event_meta.get("short_name", "")
        page_link = event_meta.get("page_link", "")
        url = f"https://investing.com{page_link}" if page_link else "-"
        description_raw = event_meta.get("description", "") or ""
        description_clean = html.unescape(description_raw)
        description_clean = re.sub(
            r"<BR\s*/?>", "\n", description_clean, flags=re.IGNORECASE
        )
        description_clean = re.sub(r"<[^>]+>", "", description_clean).strip()
        reference_period = occ.get("reference_period", "")
        cycle_suffix = event_meta.get("event_cycle_suffix", "")
        source = event_meta.get("source", "") or ""
        source_url = event_meta.get("source_url", "") or ""

        period_str = cycle_suffix or reference_period

        rows.append(
            {
                "时间": occ_time.strftime("%Y-%m-%d %H:%M:%S"),
                "地区": country_name,
                "事件": event_translated or long_name or short_name,
                "重要性": importance_value,
                "今值_raw": actual,
                "预期_raw": forecast,
                "前值_raw": previous,
                "精度": occ.get("precision"),
                "单位": unit,
                "周期": period_str,
                "详细": long_name if long_name != event_translated else "",
                "链接": url,
                "说明": description_clean,
                "来源": source,
                "来源链接": source_url,
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = (
        df.drop_duplicates(subset=["时间", "地区", "事件"])
        .sort_values("时间")
        .reset_index(drop=True)
    )
    return df


def escape_ics_text(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def format_value(value: object) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return "-"
    return str(value)


def generate_ics(
    df: pd.DataFrame, threshold: int, output_path: str, country: str | None = None
) -> None:
    filtered_df = df[df["重要性"] >= threshold].copy()
    if country:
        filtered_df = filtered_df[filtered_df["地区"] == country]
    cal_name = f"英为财经{' ' + country if country else ''} (重要性>={threshold})"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Investing.com//Economic Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-TIMEZONE:Asia/Shanghai",
        f"X-WR-CALNAME:{cal_name}",
    ]

    for _, row in filtered_df.iterrows():
        event_dt = datetime.strptime(row["时间"], "%Y-%m-%d %H:%M:%S")
        event_time = event_dt.strftime("%Y%m%dT%H%M%S")
        importance_value = int(row["重要性"])
        importance_label = IMPORTANCE_LABELS.get(
            importance_value, f"级别{importance_value}"
        )

        title = escape_ics_text(f"{format_value(row['事件'])}")

        precision = row.get("精度")
        unit = format_value(row["单位"])

        def fmt_num(val):
            if pd.isna(val) or val is None:
                return "-"
            p = (
                int(precision)
                if precision is not None and not pd.isna(precision)
                else None
            )
            if isinstance(val, float) and p is not None:
                return f"{val:.{p}f}"
            return str(val)

        actual_str = fmt_num(row["今值_raw"])
        forecast_str = fmt_num(row["预期_raw"])
        previous_str = fmt_num(row["前值_raw"])
        actual_display = (
            f"{actual_str} {unit}"
            if unit not in ("", "-") and actual_str != "-"
            else actual_str
        )
        forecast_display = (
            f"{forecast_str} {unit}"
            if unit not in ("", "-") and forecast_str != "-"
            else forecast_str
        )
        previous_display = (
            f"{previous_str} {unit}"
            if unit not in ("", "-") and previous_str != "-"
            else previous_str
        )

        desc_parts = [
            f"地区: {format_value(row['地区'])}",
            f"重要性: {importance_value} ({importance_label})",
            f"今值: {actual_display}",
            f"预期: {forecast_display}",
            f"前值: {previous_display}",
        ]
        period = format_value(row["周期"])
        if period and period != "-":
            desc_parts.append(f"周期: {period}")
        detail = format_value(row.get("详细", ""))
        if detail and detail != "-":
            desc_parts.append(f"详细: {detail}")
        explanation = format_value(row.get("说明", ""))
        if explanation and explanation != "-":
            desc_parts.append(f"说明: {explanation}")
        desc_parts.append(f"链接: {format_value(row['链接'])}")
        source = format_value(row.get("来源", ""))
        if source and source != "-":
            desc_parts.append(f"来源: {source}")
        source_url = format_value(row.get("来源链接", ""))
        if source_url and source_url != "-":
            desc_parts.append(f"来源链接: {source_url}")
        description = escape_ics_text("\n".join(desc_parts))

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uuid.uuid4()}@investing.com",
                f"DTSTAMP:{datetime.now(CALENDAR_TZ).astimezone(ZoneInfo('UTC')).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART;TZID=Asia/Shanghai:{event_time}",
                f"SUMMARY:{title}",
                f"DESCRIPTION:{description}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    print(
        f"Generated {output_path} with {len(filtered_df)} events (importance >= {threshold})"
    )


def main() -> None:
    start_day, end_day = build_date_range()
    macro_df = fetch_investing_calendar(start_day, end_day)
    for country, _, filename_template in COUNTRIES:
        for threshold in THRESHOLDS:
            output_file = filename_template.format(threshold=threshold)
            generate_ics(macro_df, threshold, output_file, country)


if __name__ == "__main__":
    main()
