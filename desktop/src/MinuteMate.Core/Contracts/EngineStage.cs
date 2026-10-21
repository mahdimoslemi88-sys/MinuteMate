namespace MinuteMate.Core.Contracts;

public enum EngineStage
{
    Models,
    Preprocess,
    Diarization,
    Transcription,
    Merge,
    Export,
    Minutes
}
