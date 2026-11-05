using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Diagnostics.HealthChecks;

namespace Instrumentation;

public static class HealthCheckExtensions
{
    public const string ReadinessTag = "ready";

    // Must stay below the readinessProbe timeout: an unreachable DB would otherwise keep each check running far beyond the probe.
    private static readonly TimeSpan CheckTimeout = TimeSpan.FromSeconds(2);

    public static IHealthChecksBuilder WithPharmaGoCheckTimeout(this IHealthChecksBuilder builder)
    {
        builder.Services.PostConfigure<HealthCheckServiceOptions>(options =>
        {
            foreach (var registration in options.Registrations)
            {
                registration.Timeout = CheckTimeout;
            }
        });
        return builder;
    }

    public static IEndpointRouteBuilder MapPharmaGoHealthChecks(this IEndpointRouteBuilder endpoints)
    {
        var readiness = new HealthCheckOptions { Predicate = check => check.Tags.Contains(ReadinessTag) };

        // Liveness must not depend on the database: if it did, a DB outage would make Kubernetes restart every replica.
        endpoints.MapHealthChecks("/health/live", new HealthCheckOptions { Predicate = _ => false });
        endpoints.MapHealthChecks("/health/ready", readiness);
        endpoints.MapHealthChecks("/health", readiness);

        return endpoints;
    }
}
