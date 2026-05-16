using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using SensorCollector.Models;

namespace SensorCollector.Services;

public sealed class RetryQueue
{
    private readonly ApiPublisher _publisher;
    private readonly LocalBufferWriter _bufferWriter;
    private readonly JsonSerializerOptions _jsonOptions;
    private readonly CollectorStatus _status;

    public RetryQueue(
        ApiPublisher publisher,
        LocalBufferWriter bufferWriter,
        JsonSerializerOptions jsonOptions,
        CollectorStatus status)
    {
        _publisher = publisher;
        _bufferWriter = bufferWriter;
        _jsonOptions = jsonOptions;
        _status = status;
    }

    public async Task RetryBufferedRecordsAsync(CancellationToken cancellationToken)
    {
        await RetrySensorReadingsAsync(cancellationToken);
        await RetryProductionEventsAsync(cancellationToken);
    }

    private async Task RetrySensorReadingsAsync(CancellationToken cancellationToken)
    {
        var lines = await _bufferWriter.ReadAndClearAsync(BufferRecordType.SensorReading, cancellationToken);
        if (lines.Count == 0)
            return;

        Console.WriteLine($"[RETRY] Found {lines.Count} buffered sensor reading(s). path={_bufferWriter.GetPath(BufferRecordType.SensorReading)}");
        var remaining = new List<string>();

        foreach (var line in lines)
        {
            if (string.IsNullOrWhiteSpace(line))
                continue;

            try
            {
                var reading = JsonSerializer.Deserialize<SensorReading>(line, _jsonOptions);
                if (reading is null)
                {
                    remaining.Add(line);
                    continue;
                }

                if (await _publisher.PublishSensorReadingAsync(reading, cancellationToken))
                    _status.IncrementRetrySucceeded();
                else
                {
                    remaining.Add(line);
                    _status.IncrementRetryFailed();
                }
            }
            catch (JsonException ex)
            {
                Console.WriteLine($"[WARN] Bad sensor buffer JSON, keeping line. error={ex.Message}");
                remaining.Add(line);
            }
        }

        if (remaining.Count > 0)
            await _bufferWriter.RequeueRawLinesAsync(BufferRecordType.SensorReading, remaining, cancellationToken);
    }

    private async Task RetryProductionEventsAsync(CancellationToken cancellationToken)
    {
        var lines = await _bufferWriter.ReadAndClearAsync(BufferRecordType.ProductionEvent, cancellationToken);
        if (lines.Count == 0)
            return;

        Console.WriteLine($"[RETRY] Found {lines.Count} buffered production event(s). path={_bufferWriter.GetPath(BufferRecordType.ProductionEvent)}");
        var remaining = new List<string>();

        foreach (var line in lines)
        {
            if (string.IsNullOrWhiteSpace(line))
                continue;

            try
            {
                var productionEvent = JsonSerializer.Deserialize<ProductionEvent>(line, _jsonOptions);
                if (productionEvent is null)
                {
                    remaining.Add(line);
                    continue;
                }

                if (await _publisher.PublishProductionEventAsync(productionEvent, cancellationToken))
                    _status.IncrementRetrySucceeded();
                else
                {
                    remaining.Add(line);
                    _status.IncrementRetryFailed();
                }
            }
            catch (JsonException ex)
            {
                Console.WriteLine($"[WARN] Bad production buffer JSON, keeping line. error={ex.Message}");
                remaining.Add(line);
            }
        }

        if (remaining.Count > 0)
            await _bufferWriter.RequeueRawLinesAsync(BufferRecordType.ProductionEvent, remaining, cancellationToken);
    }
}
