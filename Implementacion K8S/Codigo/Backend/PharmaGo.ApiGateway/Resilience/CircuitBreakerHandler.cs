using System.Net;
using System.Net.Http.Headers;
using InstrumentationInterface;
using Polly;
using Polly.CircuitBreaker;
using Polly.Timeout;

namespace PharmaGo.ApiGateway.Resilience;

public class CircuitBreakerHandler : DelegatingHandler
{
    public const string CircuitStateHeader = "X-Circuit-Breaker";

    private readonly string _clusterId;
    private readonly CircuitBreakerOptions _options;
    private readonly ICustomMetrics _metrics;
    private readonly ILogger<CircuitBreakerHandler> _logger;
    private readonly IAsyncPolicy<HttpResponseMessage> _policy;

    public CircuitBreakerHandler(
        string clusterId,
        CircuitBreakerOptions options,
        ICustomMetrics metrics,
        ILogger<CircuitBreakerHandler> logger)
    {
        _clusterId = clusterId;
        _options = options;
        _metrics = metrics;
        _logger = logger;
        _policy = BuildCircuitBreaker().WrapAsync(Policy.TimeoutAsync<HttpResponseMessage>(options.RequestTimeout));
    }

    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        try
        {
            return await _policy.ExecuteAsync(token => base.SendAsync(request, token), cancellationToken);
        }
        catch (BrokenCircuitException)
        {
            return CircuitOpenResponse(request);
        }
        catch (TimeoutRejectedException)
        {
            return new HttpResponseMessage(HttpStatusCode.GatewayTimeout) { RequestMessage = request };
        }
    }

    // 4xx responses are client errors: counting them would let a caller sending invalid requests open the circuit for everyone.
    private AsyncCircuitBreakerPolicy<HttpResponseMessage> BuildCircuitBreaker()
    {
        return Policy<HttpResponseMessage>
            .Handle<HttpRequestException>()
            .Or<TimeoutRejectedException>()
            .OrResult(response => (int)response.StatusCode >= 500)
            .AdvancedCircuitBreakerAsync(
                failureThreshold: _options.FailureRatio,
                samplingDuration: _options.SamplingDuration,
                minimumThroughput: _options.MinimumThroughput,
                durationOfBreak: _options.DurationOfBreak,
                onBreak: OnBreak,
                onReset: () => OnTransition("closed"),
                onHalfOpen: () => OnTransition("half_open"));
    }

    private void OnBreak(DelegateResult<HttpResponseMessage> outcome, TimeSpan breakDuration)
    {
        var failure = outcome.Exception?.GetType().Name ?? $"HTTP {(int)outcome.Result.StatusCode}";
        _logger.LogWarning(
            "Circuit breaker opened for cluster {Cluster} during {BreakSeconds}s. Last failure: {Failure}",
            _clusterId, breakDuration.TotalSeconds, failure);
        _metrics.RecordCircuitBreakerTransition(_clusterId, "open");
    }

    private void OnTransition(string state)
    {
        _logger.LogInformation("Circuit breaker for cluster {Cluster} is now {State}", _clusterId, state);
        _metrics.RecordCircuitBreakerTransition(_clusterId, state);
    }

    private HttpResponseMessage CircuitOpenResponse(HttpRequestMessage request)
    {
        var response = new HttpResponseMessage(HttpStatusCode.ServiceUnavailable) { RequestMessage = request };
        response.Headers.RetryAfter = new RetryConditionHeaderValue(_options.DurationOfBreak);
        response.Headers.Add(CircuitStateHeader, "open");
        return response;
    }
}
