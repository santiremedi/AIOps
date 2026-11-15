using AspNetCoreRateLimit;
using InstrumentationInterface;

namespace PharmaGo.ApiGateway.RateLimiting;

public static class RateLimitMetricSeries
{
    private const char MethodSeparator = ':';
    private const string Wildcard = "*";

    // Prometheus' rate() ignores the jump of a counter that is born with a value, so a burst
    // of rejections would never show up unless the series already exists at zero.
    public static void Initialize(IpRateLimitOptions options, ICustomMetrics metrics)
    {
        foreach (var rule in options.GeneralRules.Where(IsSpecificEndpoint))
        {
            var (method, path) = SplitEndpoint(rule.Endpoint);
            metrics.InitializeHttpRequestSeries(path, method, options.HttpStatusCode);
        }
    }

    private static bool IsSpecificEndpoint(RateLimitRule rule)
    {
        return rule.Endpoint.Contains(MethodSeparator) && !rule.Endpoint.Contains(Wildcard);
    }

    private static (string Method, string Path) SplitEndpoint(string endpoint)
    {
        var parts = endpoint.Split(MethodSeparator, 2);
        return (parts[0].ToUpperInvariant(), parts[1]);
    }
}
