using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace SensorCollector.Models;

public sealed class CollectorSettings
{
    [JsonPropertyName("ApiSettings")]
    public ApiSettings ApiSettings { get; set; } = new();

    [JsonPropertyName("CollectionSettings")]
    public CollectionSettings CollectionSettings { get; set; } = new();

    [JsonPropertyName("SimulationSettings")]
    public SimulationSettings SimulationSettings { get; set; } = new();

    [JsonPropertyName("Machines")]
    public List<MachineConfig> Machines { get; set; } = new();

    public void Validate()
    {
        if (string.IsNullOrWhiteSpace(ApiSettings.BaseUrl))
            throw new InvalidOperationException("ApiSettings.BaseUrl is required.");

        if (Machines.Count == 0)
            throw new InvalidOperationException("At least one machine must be configured in Machines.");

        foreach (var machine in Machines)
        {
            if (string.IsNullOrWhiteSpace(machine.MachineId))
                throw new InvalidOperationException("MachineId is required for every machine.");
            if (string.IsNullOrWhiteSpace(machine.LineId))
                throw new InvalidOperationException($"LineId is required for machine {machine.MachineId}.");
            if (string.IsNullOrWhiteSpace(machine.StationId))
                throw new InvalidOperationException($"StationId is required for machine {machine.MachineId}.");
        }

        CollectionSettings.Mode = CollectionSettings.Mode.Trim().ToLowerInvariant();
        if (CollectionSettings.Mode != "realtime" && CollectionSettings.Mode != "batch")
            throw new InvalidOperationException("CollectionSettings.Mode must be either 'realtime' or 'batch'.");

        if (CollectionSettings.SampleIntervalMs < 100)
            throw new InvalidOperationException("CollectionSettings.SampleIntervalMs must be at least 100 ms.");

        if (CollectionSettings.BatchSize < 1)
            throw new InvalidOperationException("CollectionSettings.BatchSize must be at least 1.");
    }
}

public sealed class ApiSettings
{
    [JsonPropertyName("BaseUrl")]
    public string BaseUrl { get; set; } = "http://127.0.0.1:8000";

    [JsonPropertyName("HealthEndpoint")]
    public string HealthEndpoint { get; set; } = "/health";

    [JsonPropertyName("SensorEndpoint")]
    public string SensorEndpoint { get; set; } = "/ingest/sensor-reading";

    [JsonPropertyName("ProductionEndpoint")]
    public string ProductionEndpoint { get; set; } = "/ingest/production-event";

    [JsonPropertyName("RequestTimeoutSeconds")]
    public int RequestTimeoutSeconds { get; set; } = 10;
}

public sealed class CollectionSettings
{
    [JsonPropertyName("Mode")]
    public string Mode { get; set; } = "realtime";

    [JsonPropertyName("SampleIntervalMs")]
    public int SampleIntervalMs { get; set; } = 1000;

    [JsonPropertyName("BatchSize")]
    public int BatchSize { get; set; } = 25;

    [JsonPropertyName("BatchDelaySeconds")]
    public int BatchDelaySeconds { get; set; } = 10;

    [JsonPropertyName("RetryIntervalSeconds")]
    public int RetryIntervalSeconds { get; set; } = 15;

    [JsonPropertyName("BufferDirectory")]
    public string BufferDirectory { get; set; } = "local-buffer";

    [JsonPropertyName("RunMinutes")]
    public int RunMinutes { get; set; } = 0;

    [JsonPropertyName("FlushBufferOnStartup")]
    public bool FlushBufferOnStartup { get; set; } = true;
}

public sealed class SimulationSettings
{
    [JsonPropertyName("RandomSeed")]
    public int RandomSeed { get; set; } = 42;

    [JsonPropertyName("SimulatedHoursPerSample")]
    public double SimulatedHoursPerSample { get; set; } = 0.08;

    [JsonPropertyName("ProductionLoadMin")]
    public double ProductionLoadMin { get; set; } = 0.65;

    [JsonPropertyName("ProductionLoadMax")]
    public double ProductionLoadMax { get; set; } = 1.10;

    [JsonPropertyName("ToolWearBaseIncreasePerHour")]
    public double ToolWearBaseIncreasePerHour { get; set; } = 0.035;

    [JsonPropertyName("MaintenanceResetProbabilityPerSample")]
    public double MaintenanceResetProbabilityPerSample { get; set; } = 0.006;

    [JsonPropertyName("MaintenanceToolWearThreshold")]
    public double MaintenanceToolWearThreshold { get; set; } = 85.0;

    [JsonPropertyName("MaintenanceToolWearResetRatio")]
    public double MaintenanceToolWearResetRatio { get; set; } = 0.38;

    [JsonPropertyName("TemperatureDriftPerSample")]
    public double TemperatureDriftPerSample { get; set; } = 0.015;

    [JsonPropertyName("DefaultShift")]
    public string DefaultShift { get; set; } = "A";

    [JsonPropertyName("OperatorGroups")]
    public List<string> OperatorGroups { get; set; } = new() { "A", "B", "C" };
}
