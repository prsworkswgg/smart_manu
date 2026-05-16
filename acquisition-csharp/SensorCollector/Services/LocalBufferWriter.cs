using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using SensorCollector.Models;

namespace SensorCollector.Services;

public enum BufferRecordType
{
    SensorReading,
    ProductionEvent
}

public sealed class LocalBufferWriter
{
    private readonly string _bufferDirectory;
    private readonly JsonSerializerOptions _jsonOptions;
    private readonly SemaphoreSlim _gate = new(1, 1);

    public LocalBufferWriter(string bufferDirectory, JsonSerializerOptions jsonOptions)
    {
        _bufferDirectory = string.IsNullOrWhiteSpace(bufferDirectory) ? "local-buffer" : bufferDirectory;
        _jsonOptions = jsonOptions;
        Directory.CreateDirectory(_bufferDirectory);
    }

    public Task BufferSensorReadingAsync(SensorReading reading, CancellationToken cancellationToken)
    {
        return AppendRecordAsync(BufferRecordType.SensorReading, reading, cancellationToken);
    }

    public Task BufferProductionEventAsync(ProductionEvent productionEvent, CancellationToken cancellationToken)
    {
        return AppendRecordAsync(BufferRecordType.ProductionEvent, productionEvent, cancellationToken);
    }

    public async Task<IReadOnlyList<string>> ReadAndClearAsync(BufferRecordType recordType, CancellationToken cancellationToken)
    {
        var path = GetPath(recordType);
        await _gate.WaitAsync(cancellationToken);
        try
        {
            if (!File.Exists(path))
                return Array.Empty<string>();

            var lines = await File.ReadAllLinesAsync(path, cancellationToken);
            File.Delete(path);
            return lines;
        }
        finally
        {
            _gate.Release();
        }
    }

    public async Task RequeueRawLinesAsync(BufferRecordType recordType, IEnumerable<string> rawLines, CancellationToken cancellationToken)
    {
        var path = GetPath(recordType);
        await _gate.WaitAsync(cancellationToken);
        try
        {
            await File.AppendAllLinesAsync(path, rawLines, cancellationToken);
        }
        finally
        {
            _gate.Release();
        }
    }

    public string GetPath(BufferRecordType recordType)
    {
        var fileName = recordType == BufferRecordType.SensorReading
            ? "sensor_readings_buffer.jsonl"
            : "production_events_buffer.jsonl";

        return Path.Combine(_bufferDirectory, fileName);
    }

    private async Task AppendRecordAsync<T>(BufferRecordType recordType, T record, CancellationToken cancellationToken)
    {
        var path = GetPath(recordType);
        var json = JsonSerializer.Serialize(record, _jsonOptions);

        await _gate.WaitAsync(cancellationToken);
        try
        {
            await File.AppendAllTextAsync(path, json + Environment.NewLine, cancellationToken);
        }
        finally
        {
            _gate.Release();
        }
    }
}
