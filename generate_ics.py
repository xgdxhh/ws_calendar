#!/usr/bin/env python

import calendar
from datetime import date, datetime, time, timedelta
from pathlib import Path
import uuid
from zoneinfo import ZoneInfo

import pandas as pd
import requests


API_URL = "https://api-one-wscn.awtmt.com/apiv1/finance/macrodatas"
CALENDAR_TZ = ZoneInfo("Asia/Shanghai")
COUNTRIES = [
    (None, "全球", "macro_calendar_{threshold}.ics"),
    ("美国", "美国", "macro_calendar_us_{threshold}.ics"),
    ("中国", "中国", "macro_calendar_cn_{threshold}.ics"),
]
THRESHOLDS = [3, 2, 1]
IMPORTANCE_LABELS = {
    4: "极高",
    3: "高",
    2: "中",
    1: "低",
}
RAW_COLUMNS = [
    "时间",
    "地区",
    "事件",
    "重要性",
    "今值",
    "预期",
    "前值",
    "修正",
    "链接",
    "period",
    "event",
]
OUTPUT_COLUMNS = [
    "时间",
    "地区",
    "事件",
    "重要性",
    "今值",
    "预期",
    "前值",
    "链接",
    "period",
    "event",
]


def shift_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_date_range(reference: date | None = None) -> tuple[datetime, datetime]:
    today = reference or datetime.now(CALENDAR_TZ).date()
    start_day = shift_months(today, -1)
    end_day = shift_months(today, 1)
    start_at = datetime.combine(start_day, time.min, tzinfo=CALENDAR_TZ)
    end_at = datetime.combine(end_day + timedelta(days=1), time.min, tzinfo=CALENDAR_TZ)
    return start_at, end_at


def fetch_macro_calendar(start_at: datetime, end_at: datetime) -> pd.DataFrame:
    items = []
    chunk_start = start_at

    while chunk_start < end_at:
        chunk_end = min(chunk_start + timedelta(days=7), end_at)
        response = requests.get(
            API_URL,
            params={
                "start": int(chunk_start.timestamp()),
                "end": int(chunk_end.timestamp()),
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 20000:
            raise ValueError(payload.get("message", "Unknown API error"))

        items.extend(payload.get("data", {}).get("items", []))
        chunk_start = chunk_end

    if not items:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df = pd.DataFrame(items).rename(
        columns={
            "public_date": "时间",
            "country": "地区",
            "title": "事件",
            "importance": "重要性",
            "actual": "今值",
            "forecast": "预期",
            "previous": "前值",
            "revised": "修正",
            "uri": "链接",
        }
    )

    for column in RAW_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    df = df[RAW_COLUMNS].copy()
    df["时间"] = pd.to_datetime(
        df["时间"], errors="coerce", unit="s", utc=True
    ).dt.tz_convert(CALENDAR_TZ)
    df = (
        df.dropna(subset=["时间"])
        .drop_duplicates(subset=["时间", "地区", "事件"])
        .sort_values("时间")
        .reset_index(drop=True)
    )

    for column in ["重要性", "今值", "预期", "前值", "修正"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["前值"] = df["修正"].combine_first(df["前值"])
    df["重要性"] = df["重要性"].fillna(0).astype(int)
    df["时间"] = df["时间"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return df[OUTPUT_COLUMNS]


def escape_ics_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def format_value(value: object) -> str:
    return "-" if pd.isna(value) else str(value)


def generate_ics(
    df: pd.DataFrame, threshold: int, output_path: str, country: str | None = None
) -> None:
    filtered_df = df[df["重要性"] >= threshold].copy()
    if country:
        filtered_df = filtered_df[filtered_df["地区"] == country]
    cal_name = (
        f"华尔街见闻-宏观日历{' ' + country if country else ''} (重要性>={threshold})"
    )
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Wallstreetcn//Macro Calendar//EN",
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

        event_name = format_value(row.get("event", ""))
        event_detail = (
            f"\n详细: {event_name}" if event_name and event_name != "-" else ""
        )
        period_val = format_value(row.get("period", ""))
        period_str = f"\n周期: {period_val}" if period_val and period_val != "-" else ""
        url_val = row.get("链接", "")
        url_str = (
            "-"
            if (pd.isna(url_val) or str(url_val).strip() == "")
            else str(url_val).strip()
        )
        actual_val = row["今值"]
        forecast_val = row["预期"]
        previous_val = row["前值"]
        actual_str = (
            "-"
            if pd.isna(actual_val) or str(actual_val).strip() == ""
            else f"{float(actual_val):g}"
        )
        forecast_str = (
            "-"
            if pd.isna(forecast_val) or str(forecast_val).strip() == ""
            else f"{float(forecast_val):g}"
        )
        previous_str = (
            "-"
            if pd.isna(previous_val) or str(previous_val).strip() == ""
            else f"{float(previous_val):g}"
        )
        title = escape_ics_text(f"{format_value(row['事件'])}")
        description = escape_ics_text(
            "\n".join(
                [
                    f"地区: {format_value(row['地区'])}",
                    f"重要性: {importance_value} ({importance_label})",
                    f"今值: {actual_str}",
                    f"预期: {forecast_str}",
                    f"前值: {previous_str}",
                ]
            )
        )

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uuid.uuid4()}@wallstreetcn",
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
    start_at, end_at = build_date_range()
    macro_df = fetch_macro_calendar(start_at, end_at)
    for country, _, filename_template in COUNTRIES:
        for threshold in THRESHOLDS:
            output_file = filename_template.format(threshold=threshold)
            generate_ics(macro_df, threshold, output_file, country)


if __name__ == "__main__":
    main()
