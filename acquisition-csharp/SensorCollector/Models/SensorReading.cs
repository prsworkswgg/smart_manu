using System;
using System.Text.Json.Serialization;

namespace SensorCollector.Models;

public sealed class SensorReading
{
    [JsonPropertyName("machine_id")]
    public string MachineId { get; set; } = string.Empty;

    [JsonPropertyName("line_id")]
    public string LineId { get; set; } = string.Empty;

    [JsonPropertyName("station_id")]
    public string StationId { get; set; } = string.Empty;

    [JsonPropertyName("timestamp")]
    public DateTimeOffset Timestamp { get; set; }

    [JsonPropertyName("air_temperature")]
    public double AirTemperature { get; set; }

    [JsonPropertyName("process_temperature")]
    public double ProcessTemperature { get; set; }

    [JsonPropertyName("vibration_rms")]
    public double VibrationRms { get; set; }

    [JsonPropertyName("vibration_peak")]
    public double VibrationPeak { get; set; }

    [JsonPropertyName("pressure")]
    public double Pressure { get; set; }

    [JsonPropertyName("torque")]
    public double Torque { get; set; }

    [JsonPropertyName("rotational_speed")]
    public double RotationalSpeed { get; set; }

    [JsonPropertyName("motor_current")]
    public double MotorCurrent { get; set; }

    [JsonPropertyName("power_consumption")]
    public double PowerConsumption { get; set; }

    [JsonPropertyName("tool_wear")]
    public double ToolWear { get; set; }

    [JsonPropertyName("operating_hours")]
    public double OperatingHours { get; set; }

    [JsonPropertyName("production_load")]
    public double ProductionLoad { get; set; }

    [JsonPropertyName("ambient_humidity")]
    public double AmbientHumidity { get; set; }
}
