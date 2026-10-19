# MinuteMate — Claude Code Guidelines

راهنمای کامل و قراردادهای پروژه در [`AGENTS.md`](./AGENTS.md) است؛ همان را بخوان.

نکات کلیدی:

- موتور: `engine/minutemate` (entry point: `python -m minutemate`).
- دسکتاپ: `desktop/MinuteMate.Desktop.sln` (.NET 8 / WPF) — موتور را به‌صورت sidecar با job JSON روی stdin و رویدادهای NDJSON روی stdout اجرا می‌کند.
- مدل‌ها از `models/` (junction به `../meeting-text/models`) خوانده می‌شوند؛ مدل جدید دانلود نکن.
- ریپوی خواهر `../meeting-text` مرجع خواندنی است؛ تغییری در آن نده.
- مهارت‌ها در `.agents/skills/`: `persian-meeting-minutes`، `diarization-speaker-mapper`، `meeting-action-tracker`.

دستورهای تأیید نهایی:

```powershell
python -m pytest -q                                   # از پوشه engine
python scripts\smoke_job.py scratch\sample30.wav      # از ریشهٔ پروژه
dotnet build desktop\MinuteMate.Desktop.sln
```
