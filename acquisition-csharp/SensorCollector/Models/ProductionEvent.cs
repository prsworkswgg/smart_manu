using System;
using System.Text.Json.Serialization;

namespace SensorCollector.Models;

public sealed class ProductionEvent
{
    [JsonPropertyName("line_id")]
    public string LineId { get; set; } = string.Empty;

    [JsonPropertyName("station_id")]
    public string StationId { get; set; } = string.Empty;

    [JsonPropertyName("batch_id")]
    public string BatchId { get; set; } = string.Empty;

    [JsonPropertyName("shift")]
    public string Shift { get; set; } = string.Empty;

    [JsonPropertyName("timestamp")]
    public DateTimeOffset Timestamp { get; set; }

    [JsonPropertyName("cycle_time_sec")]
    public double CycleTimeSec { get; set; }

    [JsonPropertyName("throughput_count")]
    public int ThroughputCount { get; set; }

    [JsonPropertyName("target_throughput")]
    public int TargetThroughput { get; set; }

    [JsonPropertyName("station_yield")]
    public double StationYield { get; set; }

    [JsonPropertyName("reject_count")]
    public int RejectCount { get; set; }

    [JsonPropertyName("rework_count")]
    public int ReworkCount { get; set; }

    [JsonPropertyName("defect_rate")]
    public double DefectRate { get; set; }

    [JsonPropertyName("micro_stop_count")]
    public int MicroStopCount { get; set; }

    [JsonPropertyName("downtime_minutes")]
    public double DowntimeMinutes { get; set; }

    [JsonPropertyName("wip_count")]
    public int WipCount { get; set; }

    [JsonPropertyName("queue_length")]
    public int QueueLength { get; set; }

    [JsonPropertyName("inspection_score_proxy")]
    public double InspectionScoreProxy { get; set; }

    [JsonPropertyName("process_stability_index")]
    public double ProcessStabilityIndex { get; set; }

    [JsonPropertyName("operator_group")]
    public string OperatorGroup { get; set; } = string.Empty;
}
