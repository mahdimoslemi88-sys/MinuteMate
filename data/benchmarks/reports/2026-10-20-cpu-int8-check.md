# گزارش ارزیابی MinuteMate

- تاریخ: `2026-10-20 01:13:07`
- نسخهٔ موتور: `0.1.0`
- کامیت: `fa7f322`
- دستگاه/محاسبه: `cpu` / `int8`
- beam/threads: `1` / `6`
- مدل‌ها: whisper=`faster-whisper-large-v3-turbo` · speaker=`3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx, sherpa-onnx-pyannote-segmentation-3-0, wespeaker_en_voxceleb_resnet34_LM.onnx`
- نمونه‌ها: `1` (پیش‌نویس: `1`)

> هشدار: نمونه‌های با مرجع «draft» عدد رسمی نیستند؛ ابتدا متن/برچسب گوینده را انسانی اصلاح کن.

| نمونه | شرایط | مدت (ث) | مرجع | WER | CER | DER | JER | خطای تعداد گوینده | RTF | زمان (ث) |
| :--- | :--- | ---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mm19-0062 | far-field, single speaker, noisy meeting room | 30.02 | draft | 47.1% | 29.3% | 64.5% | 72.1% | 1 | 0.49 | 15.10 |

## mm19-0062 — برش ۶۲ تا ۹۲ ثانیه از جلسهٔ session_20261019

- شرایط: `far-field, single speaker, noisy meeting room` · وضعیت مرجع: `draft`
- منبع مرجع: ASR draft from faster-whisper large-v3-turbo, CPU int8, beam_size=5; not human-verified
- WER: **47.1%** (S=9, D=1, I=6, N=34)
- CER: **29.3%**
- DER: **64.5%** · JER: **72.1%** · گویندهٔ مرجع/فرضیه: 1/2
- نگاشت گویندگان: `{"spk0": "0"}`
- زمان مراحل: preprocess: 0.0s · diarization: 1.7s · transcription: 13.2s · merge: 0.0s · export: 0.0s
- فرضیه (برش): این شب نخواهیدم از پر این که میترسید اما در این میخواهم پاوشه یا بیدی این هم قرصه یا این اوپنکوزه یه لاشید این دیداره بوده اما اینترنت ها رو ریدن توش خودا وکیلی اصلا این رو از دیداره
- مرجع (برش): این شب نخوابیدم از پر این که میترسید من بوده الان میخوابم پامشن یا بیدی این هم قرصه یا این اوپن کوده یه لاشید اینترنت ها رو ریدن توش خودا وکیلی اصلا یه رزدی
- خروجی: `data/benchmarks/work/mm19-0062`
- ⚠️ متن مرجع «پیش‌نویس» است (ASR) و برای عدد رسمی باید توسط انسان اصلاح شود.
