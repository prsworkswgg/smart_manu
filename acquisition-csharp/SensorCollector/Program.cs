using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using SensorCollector.Models;
using SensorCollector.Services;

namespace SensorCollector;

internal static class Program
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        WriteIndented = false
    };

    public static async Task<int> Main(string[] args)
    {
        using var cancellation = new CancellationTokenSource();
        Console.CancelKeyPress += (_, eventArgs) =>
        {
            eventArgs.Cancel = true;
            Console.WriteLine("[SHUTDOWN] Ctrl+C received. Finishing current work and stopping...");
            cancellation.Cancel();
        };

        try
        {
            var settingsPath = ResolveSettingsPath(args);
            var settings = await LoadSettingsAsync(settingsPath, cancellation.Token);
            settings.Validate();

            Console.WriteLine("============================================================");
            Console.WriteLine(" Smart Manufacturing AI Operations Platform");
            Console.WriteLine(" C# Data Acquisition Service - Simulated Data Only");
            Console.WriteLine("============================================================");
            Console.WriteLine($"[CONFIG] appsettings={settingsPath}");
            Console.WriteLine($"[CONFIG] mode={settings.CollectionSettings.Mode}, api={settings.ApiSettings.BaseUrl}, machines={settings.Machines.Count}");
            Console.WriteLine("[DISCLAIMER] Simulated data only. No real Seagate or proprietary factory data.");

            using var httpClient = new HttpClient
            {
                Timeout = TimeSpan.FromSeconds(settings.ApiSettings.RequestTimeoutSeconds)
            };

            var status = new CollectorStatus();
            var healthClient = new HealthCheckClient(httpClient, settings.ApiSettings);
            var publisher = new ApiPublisher(httpClient, settings.ApiSettings, JsonOptions);
            var bufferWriter = new LocalBufferWriter(settings.CollectionSettings.BufferDirectory, JsonOptions);
            var retryQueue = new RetryQueue(publisher, bufferWriter, JsonOptions, status);

            var stations = BuildStationRuntimes(settings);
            Console.WriteLine($"[START] Station simulators initialized: {stations.Count}");

            if (settings.CollectionSettings.FlushBufferOnStartup)
            {
                Console.WriteLine("[STARTUP] Attempting to retry local buffer before new collection...");
                await retryQueue.RetryBufferedRecordsAsync(cancellation.Token);
            }

            using var runLimit = CreateRunLimit(settings, cancellation);
            var token = runLimit.Token;

            var retryTask = RunRetryLoopAsync(retryQueue, settings, token);
            var mainTask = settings.CollectionSettings.Mode == "batch"
                ? RunBatchModeAsync(stations, publisher, healthClient, bufferWriter, settings, status, token)
                : RunRealtimeModeAsync(stations, publisher, healthClient, bufferWriter, settings, status, token);

            await Task.WhenAll(mainTask, retryTask);
            return 0;
        }
        catch (OperationCanceledException)
        {
            Console.WriteLine("[SHUTDOWN] Collector stopped by cancellation.");
            return 0;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[FATAL] {ex.GetType().Name}: {ex.Message}");
            Console.WriteLine(ex.StackTrace);
            return 1;
        }
    }

    private static CancellationTokenSource CreateRunLimit(CollectorSettings settings, CancellationTokenSource parent)
    {
        if (settings.CollectionSettings.RunMinutes <= 0)
            return CancellationTokenSource.CreateLinkedTokenSource(parent.Token);

        var linked = CancellationTokenSource.CreateLinkedTokenSource(parent.Token);
        linked.CancelAfter(TimeSpan.FromMinutes(settings.CollectionSettings.RunMinutes));
        Console.WriteLine($"[CONFIG] Run limit enabled: {settings.CollectionSettings.RunMinutes} minute(s)");
        return linked;
    }

    private static async Task<CollectorSettings> LoadSettingsAsync(string settingsPath, CancellationToken cancellationToken)
    {
        if (!File.Exists(settingsPath))
            throw new FileNotFoundException("appsettings.json was not found.", settingsPath);

        var json = await File.ReadAllTextAsync(settingsPath, cancellationToken);
        var settings = JsonSerializer.Deserialize<CollectorSettings>(json, JsonOptions);
        return settings ?? throw new InvalidOperationException("appsettings.json could not be deserialized.");
    }

    private static string ResolveSettingsPath(string[] args)
    {
        if (args.Length >= 2 && args[0] == "--config")
            return Path.GetFullPath(args[1]);

        var currentDirPath = Path.Combine(Directory.GetCurrentDirectory(), "appsettings.json");
        if (File.Exists(currentDirPath))
            return currentDirPath;

        var baseDirPath = Path.Combine(AppContext.BaseDirectory, "appsettings.json");
        if (File.Exists(baseDirPath))
            return baseDirPath;

        return currentDirPath;
    }

    private static List<StationRuntime> BuildStationRuntimes(CollectorSettings settings)
    {
        var runtimes = new List<StationRuntime>();
        foreach (var machine in settings.Machines)
        {
            runtimes.Add(new StationRuntime(
                machine,
                new MachineSensorSimulator(machine, settings.SimulationSettings),
                new ProductionLineSimulator(machine, settings.SimulationSettings)));
        }
        return runtimes;
    }

    private static async Task RunRealtimeModeAsync(
        IReadOnlyList<StationRuntime> stations,
        ApiPublisher publisher,
        HealthCheckClient healthClient,
        LocalBufferWriter bufferWriter,
        CollectorSettings settings,
        CollectorStatus status,
        CancellationToken cancellationToken)
    {
        var delay = TimeSpan.FromMilliseconds(settings.CollectionSettings.SampleIntervalMs);
        Console.WriteLine($"[MODE] Realtime mode. sample_interval_ms={settings.CollectionSettings.SampleIntervalMs}");

        while (!cancellationToken.IsCancellationRequested)
        {
            foreach (var station in stations)
                await GenerateAndPublishOneAsync(station, publisher, healthClient, bufferWriter, status, cancellationToken);

            Console.WriteLine($"[STATUS] {status.ToSummary()}");
            await Task.Delay(delay, cancellationToken);
        }
    }

    private static async Task RunBatchModeAsync(
        IReadOnlyList<StationRuntime> stations,
        ApiPublisher publisher,
        HealthCheckClient healthClient,
        LocalBufferWriter bufferWriter,
        CollectorSettings settings,
        CollectorStatus status,
        CancellationToken cancellationToken)
    {
        var batchDelay = TimeSpan.FromSeconds(settings.CollectionSettings.BatchDelaySeconds);
        Console.WriteLine($"[MODE] Batch mode. batch_size={settings.CollectionSettings.BatchSize}, batch_delay_seconds={settings.CollectionSettings.BatchDelaySeconds}");

        while (!cancellationToken.IsCancellationRequested)
        {
            Console.WriteLine($"[BATCH] Generating batch of {settings.CollectionSettings.BatchSize} sample cycle(s)...");
            for (var i = 0; i < settings.CollectionSettings.BatchSize; i++)
            {
                foreach (var station in stations)
                    await GenerateAndPublishOneAsync(station, publisher, healthClient, bufferWriter, status, cancellationToken);
            }

            Console.WriteLine($"[STATUS] {status.ToSummary()}");
            await Task.Delay(batchDelay, cancellationToken);
        }
    }

    private static async Task GenerateAndPublishOneAsync(
        StationRuntime station,
        ApiPublisher publisher,
        HealthCheckClient healthClient,
        LocalBufferWriter bufferWriter,
        CollectorStatus status,
        CancellationToken cancellationToken)
    {
        var timestamp = DateTimeOffset.UtcNow;
        var sensorReading = station.SensorSimulator.GenerateReading(timestamp);
        var productionEvent = station.ProductionSimulator.GenerateEvent(sensorReading);
        status.IncrementSensorGenerated();
        status.IncrementProductionGenerated();

        var apiHealthy = await healthClient.IsHealthyAsync(cancellationToken);
        if (!apiHealthy)
        {
            status.IncrementApiFailure();
            await BufferBothAsync(bufferWriter, sensorReading, productionEvent, status, cancellationToken);
            Console.WriteLine($"[BUFFER] API unavailable. buffered sensor+production for {station.Machine.MachineId}/{station.Machine.StationId}");
            return;
        }

        var sensorSent = await publisher.PublishSensorReadingAsync(sensorReading, cancellationToken);
        if (sensorSent)
        {
            status.IncrementSensorSent();
            Console.WriteLine($"[SEND] sensor ok {sensorReading.MachineId}/{sensorReading.StationId} wear={sensorReading.ToolWear:F2} vib={sensorReading.VibrationRms:F3}");
        }
        else
        {
            status.IncrementApiFailure();
            status.IncrementSensorBuffered();
            await bufferWriter.BufferSensorReadingAsync(sensorReading, cancellationToken);
            Console.WriteLine($"[BUFFER] sensor {sensorReading.MachineId}/{sensorReading.StationId}");
        }

        var productionSent = await publisher.PublishProductionEventAsync(productionEvent, cancellationToken);
        if (productionSent)
        {
            status.IncrementProductionSent();
            Console.WriteLine($"[SEND] production ok {productionEvent.LineId}/{productionEvent.StationId} cycle={productionEvent.CycleTimeSec:F2}s yield={productionEvent.StationYield:F4}");
        }
        else
        {
            status.IncrementApiFailure();
            status.IncrementProductionBuffered();
            await bufferWriter.BufferProductionEventAsync(productionEvent, cancellationToken);
            Console.WriteLine($"[BUFFER] production {productionEvent.LineId}/{productionEvent.StationId}");
        }
    }

    private static async Task BufferBothAsync(
        LocalBufferWriter bufferWriter,
        SensorReading sensorReading,
        ProductionEvent productionEvent,
        CollectorStatus status,
        CancellationToken cancellationToken)
    {
        await bufferWriter.BufferSensorReadingAsync(sensorReading, cancellationToken);
        await bufferWriter.BufferProductionEventAsync(productionEvent, cancellationToken);
        status.IncrementSensorBuffered();
        status.IncrementProductionBuffered();
    }

    private static async Task RunRetryLoopAsync(
        RetryQueue retryQueue,
        CollectorSettings settings,
        CancellationToken cancellationToken)
    {
        var interval = TimeSpan.FromSeconds(settings.CollectionSettings.RetryIntervalSeconds);
        Console.WriteLine($"[RETRY] Retry loop enabled. interval_seconds={settings.CollectionSettings.RetryIntervalSeconds}");

        while (!cancellationToken.IsCancellationRequested)
        {
            await Task.Delay(interval, cancellationToken);
            await retryQueue.RetryBufferedRecordsAsync(cancellationToken);
        }
    }

    private sealed record StationRuntime(
        MachineConfig Machine,
        MachineSensorSimulator SensorSimulator,
        ProductionLineSimulator ProductionSimulator);
}
