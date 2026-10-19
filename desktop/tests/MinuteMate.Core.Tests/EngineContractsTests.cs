using System.Text.Json;
using MinuteMate.Core.Contracts;
using MinuteMate.Core.Infrastructure;

namespace MinuteMate.Core.Tests;

public class EngineContractsTests
{
    [Fact]
    public void JobRequestSerializesWithCamelCaseAndStringEnums()
    {
        var request = new EngineJobRequest
        {
            AudioPath = "meeting.mp3",
            Device = ComputeDevice.Cuda
        };

        var json = JsonSerializer.Serialize(request, JsonDefaults.Engine);

        Assert.Contains("\"audioPath\":\"meeting.mp3\"", json);
        Assert.Contains("\"device\":\"cuda\"", json);
    }

    [Fact]
    public void StageEventDeserializes()
    {
        const string json = """
            {"type":"stage","stage":"transcription","status":"running","progress":0.42,"etaSeconds":310}
            """;

        var engineEvent = JsonSerializer.Deserialize<EngineEvent>(json, JsonDefaults.Engine);

        Assert.NotNull(engineEvent);
        Assert.Equal(EngineEventType.Stage, engineEvent!.Type);
        Assert.Equal(EngineStage.Transcription, engineEvent.Stage);
        Assert.Equal(0.42, engineEvent.Progress);
        Assert.Equal(310, engineEvent.EtaSeconds);
    }

    [Fact]
    public void ErrorEventDeserializesWithHint()
    {
        const string json = """
            {"type":"error","code":"CUDA_INIT","message":"failed","hint":"check driver"}
            """;

        var engineEvent = JsonSerializer.Deserialize<EngineEvent>(json, JsonDefaults.Engine);

        Assert.NotNull(engineEvent);
        Assert.Equal("CUDA_INIT", engineEvent!.Code);
        Assert.Equal("check driver", engineEvent.Hint);
    }
}
