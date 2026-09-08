# ws_calendar

每天自动生成的财经日历，来源是华尔街见闻和英为财经。

## 怎么用

复制下面任意一个链接，粘贴到日历 app 的「通过 URL 订阅」里，搞定。链接不会变，内容每天自动刷新。

### 华尔街见闻宏观日历

| 链接 | 说明 |
| ---- | ---- |
| [`macro_calendar_3.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/macro_calendar_3.ics) | 全球，3 级 |
| [`macro_calendar_2.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/macro_calendar_2.ics) | 全球，2 级及以上 |
| [`macro_calendar_1.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/macro_calendar_1.ics) | 全球，全部 |
| [`macro_calendar_us_3.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/macro_calendar_us_3.ics) | 美国，3 级 |
| [`macro_calendar_us_2.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/macro_calendar_us_2.ics) | 美国，2 级及以上 |
| [`macro_calendar_us_1.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/macro_calendar_us_1.ics) | 美国，全部 |
| [`macro_calendar_cn_3.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/macro_calendar_cn_3.ics) | 中国，3 级 |
| [`macro_calendar_cn_2.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/macro_calendar_cn_2.ics) | 中国，2 级及以上 |
| [`macro_calendar_cn_1.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/macro_calendar_cn_1.ics) | 中国，全部 |

### 英为财经经济日历

| 链接 | 说明 |
| ---- | ---- |
| [`investing_calendar_3.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/investing_calendar_3.ics) | 全球，3 级 |
| [`investing_calendar_2.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/investing_calendar_2.ics) | 全球，2 级及以上 |
| [`investing_calendar_1.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/investing_calendar_1.ics) | 全球，全部 |
| [`investing_calendar_us_3.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/investing_calendar_us_3.ics) | 美国，3 级 |
| [`investing_calendar_us_2.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/investing_calendar_us_2.ics) | 美国，2 级及以上 |
| [`investing_calendar_us_1.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/investing_calendar_us_1.ics) | 美国，全部 |
| [`investing_calendar_cn_3.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/investing_calendar_cn_3.ics) | 中国，3 级 |
| [`investing_calendar_cn_2.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/investing_calendar_cn_2.ics) | 中国，2 级及以上 |
| [`investing_calendar_cn_1.ics`](https://github.com/xgdxhh/ws_calendar/releases/download/latest/investing_calendar_cn_1.ics) | 中国，全部 |

## 本地运行

```bash
uv sync --locked
uv run python generate_ics.py
uv run python generate_investing.py
```
