# قرارداد مرحلهٔ صورت‌جلسه (Minutes Stage)

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| پیاده‌سازی‌شده (M3a) | 1405-07-28 | Engine / Contracts |

این سند قرارداد مرحلهٔ `minutes` است. صورت‌جلسه در موتور پایتون تولید می‌شود (نه در C#) و خروجی ساختاریافتهٔ آن منبع حقیقت برای رندر و ویرایش نام گویندگان است. پیاده‌سازی در `engine/minutemate/minutes/` و اتصال خط لوله در `engine/minutemate/pipeline.py` است.

## ۱. جایگاه در خط لوله

```
preprocess → diarization → transcription → merge → export → minutes
```

- ورودی: `02_diarized_cleaned_transcript.md` و `<stem>_transcript.json` (utteranceهای دارای `speaker`, `start`, `end`, `text`).
- خروجی: `03_official_meeting_minutes.md`، `04_action_items.md`، `<stem>.minutes.json`.
- مرحله اختیاری است. اگر `minutes.enabled=false` یا `provider=none` باشد، مرحله با `stage(minutes, done)` رد می‌شود و هیچ تماس شبکه‌ای انجام نمی‌شود. خروجی‌های `01_`/`02_` در هر حال تولید می‌شوند.

## ۲. پیکربندی job

کلید جدید `minutes` (اختیاری) در job JSON:

```json
{
  "minutes": {
    "enabled": true,
    "provider": "openai-compatible",
    "baseUrl": "https://api.example.com/v1",
    "model": "example-model",
    "apiKeyEnv": "MINUTEMATE_LLM_API_KEY",
    "temperature": 0.2,
    "maxOutputTokens": 4000,
    "timeoutSeconds": 120,
    "chunkSeconds": 900,
    "language": "fa",
    "template": "official-v1",
    "includeActionItems": true,
    "redact": false
  }
}
```

| کلید | نوع | پیش‌فرض | توضیح |
| :--- | :--- | :--- | :--- |
| `enabled` | bool | `false` | فعال‌سازی مرحله |
| `provider` | `none`\|`openai-compatible`\|`ollama` | `none` | `none` = بدون LLM |
| `baseUrl` | string | — | برای `openai-compatible` الزامی؛ برای `ollama` پیش‌فرض `http://127.0.0.1:11434` |
| `model` | string | — | نام مدل؛ برای providerهای شبکه‌ای الزامی |
| `apiKeyEnv` | string | `MINUTEMATE_LLM_API_KEY` | **نام** متغیر محیطی؛ مقدار کلید هرگز در job نیست |
| `temperature` | number | `0.2` | خلاقیت کم برای صورت‌جلسه |
| `maxOutputTokens` | int | `4000` | سقف هر فراخوانی |
| `timeoutSeconds` | int | `120` | مهلت هر فراخوانی |
| `chunkSeconds` | int | `900` | حداکثر طول هر قطعهٔ ورودی (۱۵ دقیقه) |
| `language` | string | `fa` | زبان خروجی |
| `template` | string | `official-v1` | نسخهٔ قالب/پرامپت |
| `includeActionItems` | bool | `true` | تولید `04_action_items.md` |
| `redact` | bool | `false` | حذف شماره/ایمیل/نام‌های حساس پیش از ارسال (اختیاری، M3b) |

### قواعد امنیتی

1. کلید فقط از `apiKeyEnv` یا credential store خوانده می‌شود؛ وجود کلید `apiKey` در job **خطای قرارداد** است (`input_error`).
2. کلید، هدر Authorization و بدنهٔ خام پاسخ در لاگ/رویداد/فایل نوشته نمی‌شود.
3. `baseUrl` باید `https` باشد، مگر `http://127.0.0.1`/`localhost` برای Ollama.
4. متن جلسه ممکن است حاوی دادهٔ شخصی باشد؛ ارسال آن به سرویس بیرونی نیازمند رضایت کاربر است. UI باید پیش از اولین اجرا هشدار دهد.

## ۳. خروجی ساختاریافته: `<stem>.minutes.json`

```json
{
  "schemaVersion": 1,
  "meeting": {
    "title": "جلسهٔ هفتگی تیم فنی",
    "date": "2026-10-19",
    "durationSeconds": 4250.85,
    "language": "fa"
  },
  "speakers": [
    { "speakerId": "spk0", "name": "مهدی", "role": "سرپرست فنی", "source": "speakerMap" },
    { "speakerId": "spk1", "name": "گوینده ۲", "role": "", "source": "auto" }
  ],
  "topics": [
    {
      "id": "t1",
      "title": "وضعیت انتشار نسخه",
      "summary": "…",
      "utteranceIds": ["u0001", "u0002"],
      "start": 61.152,
      "end": 214.0
    }
  ],
  "decisions": [
    {
      "id": "d1",
      "text": "انتشار نسخه به هفتهٔ آینده موکول شد.",
      "utteranceIds": ["u0012"],
      "needsReview": false
    }
  ],
  "actionItems": [
    {
      "id": "a1",
      "title": "آماده‌سازی فهرست تغییرات نسخه",
      "ownerSpeakerId": "spk0",
      "ownerName": "مهدی",
      "dueDate": "2026-10-27",
      "dueText": "تا هفتهٔ آینده",
      "priority": "high",
      "acceptanceCriteria": "فهرست تغییرات در مخزن ثبت و در جلسهٔ بعد مرور شود.",
      "utteranceIds": ["u0012", "u0015"],
      "status": "open",
      "needsReview": false
    }
  ],
  "openQuestions": [],
  "needsReview": [
    { "field": "actionItems[0].dueDate", "reason": "تاریخ صریح گفته نشده؛ از «هفتهٔ آینده» استنباط شده." }
  ],
  "source": {
    "provider": "openai-compatible",
    "model": "example-model",
    "promptVersion": "official-v1",
    "generatedAt": "2026-10-20T10:00:00Z",
    "chunkCount": 3,
    "transcriptSha256": "…"
  }
}
```

### قواعد داده

1. `speakerId` پایدار است (`spk0`, `spk1`, …) و از `speakers.json` می‌آید؛ نام نمایشی در `speakers[].name` است. **تغییر نام گوینده = ویرایش `speakers` + رندر دوباره؛ بدون فراخوانی دوبارهٔ LLM.**
2. `utteranceIds` باید به utteranceهای واقعی `_transcript.json` اشاره کنند؛ شناسهٔ پیشنهادی: `u0001` به ترتیب زمان.
3. هر `decision` و `actionItem` باید حداقل یک `utteranceId` شاهد داشته باشد. اگر شاهد پیدا نشد، مورد تولید نشود؛ اگر استنباطی است، `needsReview=true` و دلیل ثبت شود.
4. هیچ نام، عدد، تاریخ یا مسئولی که در متن نیست، اختراع نمی‌شود؛ `ownerSpeakerId` فقط از گویندگان موجود.
5. `dueDate` فقط وقتی ISO پر می‌شود که تاریخ صریح باشد؛ وگرنه `null` + `dueText` + `needsReview`.
6. ترتیب `topics`/`decisions`/`actionItems` زمانی است؛ ادغام قطعه‌ها باید ترتیب را حفظ کند.

## ۴. تولید و ادغام قطعه‌ها

- متن به قطعه‌های حداکثر `chunkSeconds` تقسیم می‌شود؛ مرزها روی مرز نوبت گوینده قرار می‌گیرند (و سقف ۴۰۰ utterance در هر قطعه).
- هر قطعه یک فراخوانی «استخراج» می‌دهد (topics/decisions/actions با `utteranceIds`).
- ادغام در M3a **محلی و قطعی** است: کلید dedupe متن نرمال‌شدهٔ مورد و اجتماع شاهدها با حفظ ترتیب زمانی؛ فراخوانی ادغام LLM اختیاری به M3b موکول شد (`build_merge_messages` آماده است اما استفاده نمی‌شود).
- اگر مدل پاسخ نامعتبر/ناقص داد: یک retry با پرامپت اصلاحی؛ بعد از آن `error` با `code=llm_bad_response` و نگه‌داشتن خروجی‌های قبلی.
- `transcriptSha256` برای تشخیص کهنه‌بودن صورت‌جلسه نسبت به رونویسی است.

## ۵. رندر Markdown

- `03_official_meeting_minutes.md`: سرصفحه (عنوان/تاریخ/مدت/حاضرین)، دستور جلسه، خلاصهٔ مدیریتی، موضوع‌ها، مصوبات، سؤالات باز، اقدامات.
- `04_action_items.md`: جدول اقدامات + RACI ساده؛ هر ردیف `ownerName`، مهلت، معیار پذیرش و شاهد.
- رندر از `minutes.json` انجام می‌شود؛ نام گوینده با `speakerMap` جاری حل می‌شود.
- اگر `includeActionItems=false`، فایل `04_` تولید نمی‌شود و `artifact` آن منتشر نمی‌شود.

## ۶. رویدادها و خطاها

```jsonl
{"type":"stage","stage":"minutes","status":"running","progress":0,"message":"تولید صورت‌جلسه"}
{"type":"stage","stage":"minutes","status":"running","progress":0.5}
{"type":"artifact","kind":"03_official_meeting_minutes.md","path":"…"}
{"type":"artifact","kind":"04_action_items.md","path":"…"}
{"type":"artifact","kind":"session.minutes.json","path":"…"}
{"type":"stage","stage":"minutes","status":"done","progress":1}
```

| code | معنا | رفتار |
| :--- | :--- | :--- |
| `llm_disabled` | provider=none | مرحله رد می‌شود؛ خطا نیست (`log` + `stage(minutes, done)`, پیام «غیرفعال»)؛ کد خطا منتشر نمی‌شود |
| `llm_auth_missing` | متغیر کلید نیست | `error`، خروجی‌های ۰۱/۰۲ حفظ می‌شوند |
| `llm_unavailable` | اتصال/سرویس در دسترس نیست | retry کوتاه، سپس `error` |
| `llm_timeout` | مهلت فراخوانی | retry یک‌بار، سپس `error` |
| `llm_bad_response` | JSON/ساختار نامعتبر | retry اصلاحی، سپس `error` |
| `minutes_parse_error` | دادهٔ ورودی رونویسی ناقص | `error` با `hint` |

## ۷. آستانهٔ سخت‌افزار و انتخاب provider

| سناریو | توصیه |
| :--- | :--- |
| GPU < 8GB VRAM یا RAM < 16GB | provider ابری/شبکه‌ای؛ مدل محلی ۷B قابل اتکا نیست |
| GPU ≥ 8GB و RAM ≥ 16GB | Ollama با مدل ۷B quantized ممکن است؛ کیفیت را با چک‌لیست بسنج |
| بدون اینترنت/حریم خصوصی سخت‌گیرانه | `provider=none` + تولید دستی با مهارت `persian-meeting-minutes` |

برای RTX 4050 Laptop 6GB فعلی، پیش‌فرض پیشنهادی `openai-compatible` است؛ مدل محلی فقط برای تست.

## ۸. پذیرش

- چک‌لیست انسانی `docs/05-quality/evaluation.md` روی ۳ جلسه (۲ نفرهٔ فنی، ۴ نفرهٔ مدیریتی، ۱ نفرهٔ گزارش‌دهی).
- هر مصوبه/اقدام شاهد utterance داشته باشد؛ نرخ ادعای بدون شاهد = ۰.
- تغییر نام گوینده بدون فراخوانی دوباره، در هر دو فایل Markdown منعکس شود.
- `--strict-truth`/CI بدون کلید شبکه اجرا شود و مرحله را رد کند.
