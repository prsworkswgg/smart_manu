using System;
using System.Threading;

namespace SensorCollector.Models;

public sealed class CollectorStatus
{
    private long _sensorGenerated;
    private long _productionGenerated;
    private long _sensorSent;
    private long _productionSent;
    private long _sensorBuffered;
    private long _productionBuffered;
    private long _retrySucceeded;
    private long _retryFailed;
    private long _apiFailures;

    public DateTimeOffset StartedAt { get; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? LastSuccessAt { get; private set; }
    public DateTimeOffset? LastFailureAt { get; private set; }

    public long SensorGenerated => Interlocked.Read(ref _sensorGenerated);
    public long ProductionGenerated => Interlocked.Read(ref _productionGenerated);
    public long SensorSent => Interlocked.Read(ref _sensorSent);
    public long ProductionSent => Interlocked.Read(ref _productionSent);
    public long SensorBuffered => Interlocked.Read(ref _sensorBuffered);
    public long ProductionBuffered => Interlocked.Read(ref _productionBuffered);
    public long RetrySucceeded => Interlocked.Read(ref _retrySucceeded);
    public long RetryFailed => Interlocked.Read(ref _retryFailed);
    public long ApiFailures => Interlocked.Read(ref _apiFailures);

    public void IncrementSensorGenerated() => Interlocked.Increment(ref _sensorGenerated);
    public void IncrementProductionGenerated() => Interlocked.Increment(ref _productionGenerated);

    public void IncrementSensorSent()
    {
        Interlocked.Increment(ref _sensorSent);
        LastSuccessAt = DateTimeOffset.UtcNow;
    }

    public void IncrementProductionSent()
    {
        Interlocked.Increment(ref _productionSent);
        LastSuccessAt = DateTimeOffset.UtcNow;
    }

    public void IncrementSensorBuffered() => Interlocked.Increment(ref _sensorBuffered);
    public void IncrementProductionBuffered() => Interlocked.Increment(ref _productionBuffered);

    public void IncrementRetrySucceeded()
    {
        Interlocked.Increment(ref _retrySucceeded);
        LastSuccessAt = DateTimeOffset.UtcNow;
    }

    public void IncrementRetryFailed()
    {
        Interlocked.Increment(ref _retryFailed);
        LastFailureAt = DateTimeOffset.UtcNow;
    }

    public void IncrementApiFailure()
    {
        Interlocked.Increment(ref _apiFailures);
        LastFailureAt = DateTimeOffset.UtcNow;
    }

    public string ToSummary()
    {
        var uptime = DateTimeOffset.UtcNow - StartedAt;
        return $"uptime={uptime:hh\\:mm\\:ss}, sensor_generated={SensorGenerated}, production_generated={ProductionGenerated}, " +
               $"sensor_sent={SensorSent}, production_sent={ProductionSent}, sensor_buffered={SensorBuffered}, " +
               $"production_buffered={ProductionBuffered}, retry_ok={RetrySucceeded}, retry_failed={RetryFailed}, api_failures={ApiFailures}";
    }
}
