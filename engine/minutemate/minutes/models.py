"""Structured minutes document model (the source of truth for rendering)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = 1


@dataclass
class Speaker:
    speaker_id: str
    name: str
    role: str = ""
    source: str = "auto"


@dataclass
class Topic:
    id: str
    title: str
    summary: str = ""
    utterance_ids: list[str] = field(default_factory=list)
    start: float | None = None
    end: float | None = None


@dataclass
class Decision:
    id: str
    text: str
    utterance_ids: list[str] = field(default_factory=list)
    needs_review: bool = False


@dataclass
class ActionItem:
    id: str
    title: str
    owner_speaker_id: str | None = None
    owner_name: str = ""
    due_date: str | None = None
    due_text: str = ""
    priority: str = "medium"
    acceptance_criteria: str = ""
    utterance_ids: list[str] = field(default_factory=list)
    status: str = "open"
    needs_review: bool = False


@dataclass
class OpenQuestion:
    id: str
    text: str
    utterance_ids: list[str] = field(default_factory=list)


@dataclass
class NeedsReview:
    field: str
    reason: str


@dataclass
class Meeting:
    title: str
    date: str
    duration_seconds: float = 0.0
    language: str = "fa"
    summary: str = ""


@dataclass
class Source:
    provider: str
    model: str
    prompt_version: str
    generated_at: str
    chunk_count: int
    transcript_sha256: str


@dataclass
class MinutesDocument:
    meeting: Meeting
    speakers: list[Speaker] = field(default_factory=list)
    topics: list[Topic] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    open_questions: list[OpenQuestion] = field(default_factory=list)
    needs_review: list[NeedsReview] = field(default_factory=list)
    source: Source | None = None
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "meeting": {
                "title": self.meeting.title,
                "date": self.meeting.date,
                "durationSeconds": self.meeting.duration_seconds,
                "language": self.meeting.language,
                "summary": self.meeting.summary,
            },
            "speakers": [
                {
                    "speakerId": speaker.speaker_id,
                    "name": speaker.name,
                    "role": speaker.role,
                    "source": speaker.source,
                }
                for speaker in self.speakers
            ],
            "topics": [
                {
                    "id": topic.id,
                    "title": topic.title,
                    "summary": topic.summary,
                    "utteranceIds": topic.utterance_ids,
                    "start": topic.start,
                    "end": topic.end,
                }
                for topic in self.topics
            ],
            "decisions": [
                {
                    "id": decision.id,
                    "text": decision.text,
                    "utteranceIds": decision.utterance_ids,
                    "needsReview": decision.needs_review,
                }
                for decision in self.decisions
            ],
            "actionItems": [
                {
                    "id": item.id,
                    "title": item.title,
                    "ownerSpeakerId": item.owner_speaker_id,
                    "ownerName": item.owner_name,
                    "dueDate": item.due_date,
                    "dueText": item.due_text,
                    "priority": item.priority,
                    "acceptanceCriteria": item.acceptance_criteria,
                    "utteranceIds": item.utterance_ids,
                    "status": item.status,
                    "needsReview": item.needs_review,
                }
                for item in self.action_items
            ],
            "openQuestions": [
                {"id": question.id, "text": question.text, "utteranceIds": question.utterance_ids}
                for question in self.open_questions
            ],
            "needsReview": [asdict(item) for item in self.needs_review],
            "source": None
            if self.source is None
            else {
                "provider": self.source.provider,
                "model": self.source.model,
                "promptVersion": self.source.prompt_version,
                "generatedAt": self.source.generated_at,
                "chunkCount": self.source.chunk_count,
                "transcriptSha256": self.source.transcript_sha256,
            },
        }
