using System.Text.Json.Serialization;

namespace SensorCollector.Models;

public sealed class MachineConfig
{
    [JsonPropertyName("MachineId")]
    public string MachineId { get; set; } = string.Empty;

    [JsonPropertyName("LineId")]
    public string LineId { get; set; } = string.Empty;

    [JsonPropertyName("StationId")]
    public string StationId { get; set; } = string.Empty;

    [JsonPropertyName("MachineType")]
    public string MachineType { get; set; } = "generic_machine";

    [JsonPropertyName("Criticality")]
    public string Criticality { get; set; } = "medium";

    [JsonPropertyName("InitialOperatingHours")]
    public double InitialOperatingHours { get; set; }

    [JsonPropertyName("InitialToolWear")]
    public double InitialToolWear { get; set; }

    [JsonPropertyName("TargetThroughputPerHour")]
    public int TargetThroughputPerHour { get; set; } = 600;

    [JsonPropertyName("BaseCycleTimeSeconds")]
    public double BaseCycleTimeSeconds { get; set; } = 6.0;

    [JsonPropertyName("BaseTorqueNm")]
    public double BaseTorqueNm { get; set; } = 18.0;

    [JsonPropertyName("BaseProcessTemperatureC")]
    public double BaseProcessTemperatureC { get; set; } = 52.0;
}
