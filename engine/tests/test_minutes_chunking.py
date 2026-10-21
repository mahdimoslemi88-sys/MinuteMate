from minutemate.minutes import chunking


def _utterances():
    return [
        {"speaker": 0, "start": 0.0, "end": 2.0, "text": "سلام"},
        {"speaker": 1, "start": 2.0, "end": 4.0, "text": "  "},
        {"speaker": 1, "start": 4.0, "end": 6.0, "text": "خوبی؟"},
    ]


def test_build_transcript_assigns_ids_and_drops_empty():
    items = chunking.build_transcript(_utterances())
    assert [item["id"] for item in items] == ["u0001", "u0003"]
    assert [item["speakerId"] for item in items] == ["spk0", "spk1"]


def test_chunk_transcript_splits_on_duration():
    items = chunking.build_transcript(
        [
            {"speaker": 0, "start": 0.0, "end": 5.0, "text": "یک"},
            {"speaker": 0, "start": 5.0, "end": 15.0, "text": "دو"},
            {"speaker": 0, "start": 15.0, "end": 25.0, "text": "سه"},
        ]
    )
    chunks = chunking.chunk_transcript(items, chunk_seconds=20)
    assert len(chunks) == 2
    assert [item["text"] for item in chunks[0]] == ["یک", "دو"]


def test_chunk_transcript_respects_max_utterances():
    items = chunking.build_transcript(
        [{"speaker": 0, "start": i, "end": i + 0.5, "text": f"m{i}"} for i in range(5)]
    )
    chunks = chunking.chunk_transcript(items, chunk_seconds=999, max_utterances=2)
    assert [len(chunk) for chunk in chunks] == [2, 2, 1]


def test_transcript_text_labels_speakers():
    items = chunking.build_transcript(_utterances())
    text = chunking.transcript_text(items, {"spk0": "مهدی"})
    assert text.splitlines()[0] == "[u0001] مهدی: سلام"


def test_transcript_sha_is_stable():
    items = chunking.build_transcript(_utterances())
    assert chunking.transcript_sha256(items) == chunking.transcript_sha256(items)
