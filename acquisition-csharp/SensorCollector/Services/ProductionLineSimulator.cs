using System;
using SensorCollector.Models;

namespace SensorCollector.Services;

public sealed class ProductionLineSimulator
{
    private readonly MachineConfig _machine;
    private readonly SimulationSettings _simulation;
    private readonly Random _random;
    private int _batchCounter;

    public ProductionLineSimulator(MachineConfig machine, SimulationSettings simulation)
    {
        _machine = machine;
        _simulation = simulation;
        _random = new Random(simulation.RandomSeed + StableSeed(machine.LineId + machine.StationId));
    }

    public ProductionEvent GenerateEvent(SensorReading reading)
    {
        _batchCounter++;

        // vibration high -> cycle_time increases
        var vibrationPenalty = Math.Max(0, reading.VibrationRms - 1.2) * 0.82;
        var wearPenalty = Math.Max(0, reading.ToolWear - 40.0) * 0.018;
        var queueLength = Math.Max(0, (int)Math.Round(NextDouble(3, 18) + vibrationPenalty * 4.0 + wearPenalty * 10.0));
        var queuePenalty = queueLength * 0.025;

        var cycleTime = _machine.BaseCycleTimeSeconds + vibrationPenalty + wearPenalty + queuePenalty + NextDouble(-0.25, 0.45);
        cycleTime = Math.Max(1.0, cycleTime);

        // cycle_time high -> micro_stop_count increases
        var microStopCount = Math.Max(0, (int)Math.Round(Math.Max(0, cycleTime - _machine.BaseCycleTimeSeconds) * 0.95 + NextDouble(0, 2)));

        var targetThroughputPerMinute = Math.Max(1, _machine.TargetThroughputPerHour / 60);
        var throughput = Math.Max(1, (int)Math.Round(targetThroughputPerMinute * (_machine.BaseCycleTimeSeconds / cycleTime) * NextDouble(0.90, 1.04)));

        // process_temperature drift -> process_stability_index decreases
        var temperatureDrift = Math.Max(0, reading.ProcessTemperature - _machine.BaseProcessTemperatureC);
        var processStabilityIndex = 1.0
                                    - temperatureDrift * 0.010
                                    - reading.VibrationRms * 0.020
                                    - microStopCount * 0.015;
        processStabilityIndex = Clamp(processStabilityIndex, 0.0, 1.0);

        var inspectionScoreProxy = 0.995
                                   - reading.VibrationRms * 0.018
                                   - temperatureDrift * 0.006
                                   - Math.Max(0, reading.ToolWear - 50.0) * 0.0018
                                   + NextDouble(-0.010, 0.006);
        inspectionScoreProxy = Clamp(inspectionScoreProxy, 0.50, 0.999);

        // defect_rate increases as inspection score decreases and as wear/vibration increase.
        var defectRate = 0.006
                         + (1.0 - inspectionScoreProxy) * 0.35
                         + Math.Max(0, reading.ToolWear - 65.0) * 0.0015
                         + Math.Max(0, reading.VibrationRms - 3.0) * 0.012;
        defectRate = Clamp(defectRate, 0.0, 0.45);

        // defect_rate increases -> station_yield decreases
        var stationYield = Clamp(1.0 - defectRate, 0.50, 0.999);
        var rejectCount = Math.Max(0, (int)Math.Round(throughput * defectRate));
        var reworkCount = Math.Max(0, (int)Math.Round(rejectCount * NextDouble(0.25, 0.65)));
        var downtimeMinutes = microStopCount == 0 ? 0.0 : Math.Round(microStopCount * NextDouble(0.15, 0.65), 2);
        var wipCount = Math.Max(0, (int)Math.Round(throughput * NextDouble(1.2, 3.8) + queueLength));

        return new ProductionEvent
        {
            LineId = _machine.LineId,
            StationId = _machine.StationId,
            BatchId = $"B{DateTimeOffset.UtcNow:yyyyMMddHH}-{_batchCounter:D5}",
            Shift = DetermineShift(DateTimeOffset.Now),
            Timestamp = reading.Timestamp,
            CycleTimeSec = Round(cycleTime, 3),
            ThroughputCount = throughput,
            TargetThroughput = targetThroughputPerMinute,
            StationYield = Round(stationYield, 5),
            RejectCount = rejectCount,
            ReworkCount = reworkCount,
            DefectRate = Round(defectRate, 5),
            MicroStopCount = microStopCount,
            DowntimeMinutes = downtimeMinutes,
            WipCount = wipCount,
            QueueLength = queueLength,
            InspectionScoreProxy = Round(inspectionScoreProxy, 5),
            ProcessStabilityIndex = Round(processStabilityIndex, 5),
            OperatorGroup = PickOperatorGroup()
        };
    }

    private string DetermineShift(DateTimeOffset localTime)
    {
        if (_simulation.OperatorGroups.Count == 0)
            return _simulation.DefaultShift;

        var hour = localTime.Hour;
        if (hour >= 6 && hour < 14) return _simulation.OperatorGroups[0];
        if (hour >= 14 && hour < 22) return _simulation.OperatorGroups.Count > 1 ? _simulation.OperatorGroups[1] : _simulation.DefaultShift;
        return _simulation.OperatorGroups.Count > 2 ? _simulation.OperatorGroups[2] : _simulation.DefaultShift;
    }

    private string PickOperatorGroup()
    {
        if (_simulation.OperatorGroups.Count == 0)
            return _simulation.DefaultShift;
        return _simulation.OperatorGroups[_random.Next(_simulation.OperatorGroups.Count)];
    }

    private double NextDouble(double min, double max) => min + _random.NextDouble() * (max - min);

    private static double Clamp(double value, double min, double max) => Math.Min(max, Math.Max(min, value));

    private static double Round(double value, int decimals) => Math.Round(value, decimals, MidpointRounding.AwayFromZero);

    private static int StableSeed(string text)
    {
        unchecked
        {
            var hash = 17;
            foreach (var ch in text)
                hash = hash * 31 + ch;
            return Math.Abs(hash % 100_000);
        }
    }
}
