namespace PharmaGo.ApiGateway.Resilience;

public class CircuitBreakerOptions
{
    public const string SectionName = "CircuitBreaker";

    public double FailureRatio { get; set; } = 0.5;
    public TimeSpan SamplingDuration { get; set; } = TimeSpan.FromSeconds(30);
    public int MinimumThroughput { get; set; } = 10;
    public TimeSpan DurationOfBreak { get; set; } = TimeSpan.FromSeconds(30);
    public TimeSpan RequestTimeout { get; set; } = TimeSpan.FromSeconds(10);
}
