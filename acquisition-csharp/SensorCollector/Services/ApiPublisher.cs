using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using SensorCollector.Models;

namespace SensorCollector.Services;

public sealed class ApiPublisher
{
    private readonly HttpClient _httpClient;
    private readonly ApiSettings _apiSettings;
    private readonly JsonSerializerOptions _jsonOptions;

    public ApiPublisher(HttpClient httpClient, ApiSettings apiSettings, JsonSerializerOptions jsonOptions)
    {
        _httpClient = httpClient;
        _apiSettings = apiSettings;
        _jsonOptions = jsonOptions;
    }

    public Task<bool> PublishSensorReadingAsync(SensorReading reading, CancellationToken cancellationToken)
    {
        return PostJsonAsync(_apiSettings.SensorEndpoint, reading, "sensor-reading", cancellationToken);
    }

    public Task<bool> PublishProductionEventAsync(ProductionEvent productionEvent, CancellationToken cancellationToken)
    {
        return PostJsonAsync(_apiSettings.ProductionEndpoint, productionEvent, "production-event", cancellationToken);
    }

    private async Task<bool> PostJsonAsync<T>(string endpoint, T payload, string label, CancellationToken cancellationToken)
    {
        try
        {
            var url = BuildUrl(endpoint);
            var json = JsonSerializer.Serialize(payload, _jsonOptions);
            using var content = new StringContent(json, Encoding.UTF8, "application/json");
            using var response = await _httpClient.PostAsync(url, content, cancellationToken);

            if (response.IsSuccessStatusCode)
                return true;

            var responseBody = await response.Content.ReadAsStringAsync(cancellationToken);
            Console.WriteLine($"[WARN] API rejected {label}. status={(int)response.StatusCode} body={TrimForLog(responseBody)}");
            return false;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[WARN] Failed to publish {label}: {ex.Message}");
            return false;
        }
    }

    private Uri BuildUrl(string endpoint)
    {
        var baseUrl = _apiSettings.BaseUrl.EndsWith('/') ? _apiSettings.BaseUrl : _apiSettings.BaseUrl + "/";
        return new Uri(new Uri(baseUrl), endpoint.TrimStart('/'));
    }

    private static string TrimForLog(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return "<empty>";
        value = value.Replace(Environment.NewLine, " ").Trim();
        return value.Length <= 240 ? value : value[..240] + "...";
    }
}
