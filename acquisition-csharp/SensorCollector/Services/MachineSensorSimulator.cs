using System;
using SensorCollector.Models;

namespace SensorCollector.Services;

public sealed class MachineSensorSimulator
{
    private readonly MachineConfig _machine;
    private readonly SimulationSettings _simulation;
    private readonly Random _random;
    private double _operatingHours;
    private double _toolWear;
    private double _temperatureDrift;
    private double _lastMaintenanceDamping = 1.0;

    public MachineSensorSimulator(MachineConfig machine, SimulationSettings simulation)
    {
        _machine = machine;
        _simulation = simulation;
        _random = new Random(simulation.RandomSeed + StableSeed(machine.MachineId));
        _operatingHours = Math.Max(0, machine.InitialOperatingHours);
        _toolWear = Clamp(machine.InitialToolWear, 0, 100);
        _temperatureDrift = 0;
    }

    public SensorReading GenerateReading(DateTimeOffset timestamp)
    {
        var productionLoad = NextDouble(_simulation.ProductionLoadMin, _simulation.ProductionLoadMax);
        var ambientHumidity = NextDouble(38, 72);
        var airTemperature = NextDouble(24, 32) + Math.Max(0, productionLoad - 0.85) * 4.0;

        _operatingHours += _simulation.SimulatedHoursPerSample;
        _temperatureDrift += _simulation.TemperatureDriftPerSample + NextDouble(-0.010, 0.025);

        var highLoadPenalty = Math.Max(0, productionLoad - 0.80) * 0.08;
        var toolWearIncrease = _simulation.ToolWearBaseIncreasePerHour * _simulation.SimulatedHoursPerSample;
        toolWearIncrease += highLoadPenalty;
        _toolWear = Clamp(_toolWear + toolWearIncrease, 0, 100);

        ApplySimpleMaintenanceResetIfNeeded();

        // tool_wear high -> torque high
        var torque = _machine.BaseTorqueNm
                     + _toolWear * 0.28
                     + productionLoad * 5.5
                     + NextDouble(-1.2, 1.2);

        // torque high -> motor_current high
        var vibrationBase = 0.65 + _toolWear * 0.035 + Math.Max(0, torque - _machine.BaseTorqueNm) * 0.015;
        var vibrationRms = Math.Max(0.05, vibrationBase * _lastMaintenanceDamping + NextDouble(-0.08, 0.16));
        var vibrationPeak = vibrationRms * NextDouble(2.0, 3.7);
        var motorCurrent = 2.5 + torque * 0.16 + vibrationRms * 0.75 + NextDouble(-0.25, 0.35);

        // process_temperature drift grows gradually and is reduced by maintenance damping.
        var processTemperature = _machine.BaseProcessTemperatureC
                                 + _temperatureDrift
                                 + _toolWear * 0.18
                                 + productionLoad * 5.0
                                 + NextDouble(-1.0, 1.2);

        var rotationalSpeed = MachineTypeBaseSpeed(_machine.MachineType) + NextDouble(-90, 90) - _toolWear * 1.2;
        var pressure = 105 + productionLoad * 28 + NextDouble(-4, 5);
        var powerConsumption = motorCurrent * 0.22 * NextDouble(0.95, 1.08);

        _lastMaintenanceDamping = Math.Min(1.0, _lastMaintenanceDamping + 0.015);

        return new SensorReading
        {
            MachineId = _machine.MachineId,
            LineId = _machine.LineId,
            StationId = _machine.StationId,
            Timestamp = timestamp,
            AirTemperature = Round(airTemperature, 2),
            ProcessTemperature = Round(processTemperature, 2),
            VibrationRms = Round(vibrationRms, 4),
            VibrationPeak = Round(vibrationPeak, 4),
            Pressure = Round(pressure, 2),
            Torque = Round(torque, 3),
            RotationalSpeed = Round(rotationalSpeed, 1),
            MotorCurrent = Round(motorCurrent, 3),
            PowerConsumption = Round(powerConsumption, 3),
            ToolWear = Round(_toolWear, 3),
            OperatingHours = Round(_operatingHours, 3),
            ProductionLoad = Round(productionLoad, 3),
            AmbientHumidity = Round(ambientHumidity, 2)
        };
    }

    private void ApplySimpleMaintenanceResetIfNeeded()
    {
        var thresholdHit = _toolWear >= _simulation.MaintenanceToolWearThreshold;
        var randomMaintenance = _random.NextDouble() < _simulation.MaintenanceResetProbabilityPerSample;

        if (!thresholdHit && !randomMaintenance)
            return;

        // Simple maintenance reset effect:
        // tool wear drops, process temperature drift partially resets,
        // and vibration/current are damped for a short period.
        _toolWear = Clamp(_toolWear * _simulation.MaintenanceToolWearResetRatio, 0, 100);
        _temperatureDrift *= 0.45;
        _lastMaintenanceDamping = 0.55;

        Console.WriteLine($"[MAINTENANCE] {_machine.MachineId}/{_machine.StationId}: simple reset applied. tool_wear={_toolWear:F2}, temp_drift={_temperatureDrift:F2}");
    }

    private static double MachineTypeBaseSpeed(string machineType)
    {
        return machineType.Trim().ToLowerInvariant() switch
        {
            "micro_press" => 1800,
            "spindle_tester" => 3600,
            "thermal_chamber" => 900,
            "optical_inspection" => 1400,
            "milling_machine" => 2400,
            "assembly_cell" => 1200,
            _ => 1600
        };
    }

    private double NextDouble(double min, double max) => min + _random.NextDouble() * (max - min);

    private static double Clamp(double value, double min, double max) => Math.Min(max, Math.Max(min, value));

    private static double Round(double value, int decimals) => Math.Round(value, decimals, MidpointRounding.AwayFromZero);

    private static int StableSeed(string text)
    {
        unchecked
        {
            var hash = 23;
            foreach (var ch in text)
                hash = hash * 31 + ch;
            return Math.Abs(hash % 100_000);
        }
    }
}
