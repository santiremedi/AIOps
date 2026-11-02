using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.AspNetCore.Routing;

namespace Instrumentation;

public static class HealthCheckExtensions
{
    public const string ReadinessTag = "ready";

    /// <summary>
    /// Maps /health/live (process only, used by the liveness probe) and /health/ready (checks tagged as readiness).
    /// /health stays as an alias of readiness for existing consumers.
    /// </summary>
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
