using InstrumentationInterface;
using Microsoft.Extensions.Options;
using Yarp.ReverseProxy.Forwarder;

namespace PharmaGo.ApiGateway.Resilience;

public class CircuitBreakerForwarderHttpClientFactory : ForwarderHttpClientFactory
{
    private readonly CircuitBreakerOptions _options;
    private readonly ICustomMetrics _metrics;
    private readonly ILoggerFactory _loggerFactory;

    public CircuitBreakerForwarderHttpClientFactory(
        IOptions<CircuitBreakerOptions> options,
        ICustomMetrics metrics,
        ILoggerFactory loggerFactory)
        : base(loggerFactory.CreateLogger<ForwarderHttpClientFactory>())
    {
        _options = options.Value;
        _metrics = metrics;
        _loggerFactory = loggerFactory;
    }

    // YARP builds one client per cluster, so each cluster gets its own independent circuit.
    protected override HttpMessageHandler WrapHandler(ForwarderHttpClientContext context, HttpMessageHandler handler)
    {
        return new CircuitBreakerHandler(context.ClusterId, _options, _metrics, _loggerFactory.CreateLogger<CircuitBreakerHandler>())
        {
            InnerHandler = base.WrapHandler(context, handler)
        };
    }
}
