using System;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using SensorCollector.Models;

namespace SensorCollector.Services;

public sealed class HealthCheckClient
{
    private readonly HttpClient _httpClient;
    private readonly ApiSettings _apiSettings;

    public HealthCheckClient(HttpClient httpClient, ApiSettings apiSettings)
    {
        _httpClient = httpClient;
        _apiSettings = apiSettings;
    }

    public async Task<bool> IsHealthyAsync(CancellationToken cancellationToken)
    {
        try
        {
            using var response = await _httpClient.GetAsync(BuildUrl(_apiSettings.HealthEndpoint), cancellationToken);
            return response.IsSuccessStatusCode;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch
        {
            return false;
        }
    }

    private Uri BuildUrl(string endpoint)
    {
        var baseUrl = _apiSettings.BaseUrl.EndsWith('/') ? _apiSettings.BaseUrl : _apiSettings.BaseUrl + "/";
        return new Uri(new Uri(baseUrl), endpoint.TrimStart('/'));
    }
}
