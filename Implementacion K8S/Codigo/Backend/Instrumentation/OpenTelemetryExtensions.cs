using Microsoft.Extensions.DependencyInjection;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

namespace Instrumentation;

public static class OpenTelemetryExtensions
{
    public const string CustomMetricsMeterName = "PharmaGo.CustomMetrics";

    public static IServiceCollection AddPharmaGoOpenTelemetry(this IServiceCollection services, string serviceName)
    {
        services.AddOpenTelemetry()
            .ConfigureResource(resource => resource.AddService(serviceName))
            .WithMetrics(metrics => metrics
                .AddAspNetCoreInstrumentation()
                .AddHttpClientInstrumentation()
                .AddMeter(CustomMetricsMeterName)
                .AddPrometheusExporter()
                .AddOtlpExporter())
            .WithTracing(tracing => tracing
                .AddAspNetCoreInstrumentation()
                .AddHttpClientInstrumentation()
                .AddSqlClientInstrumentation()
                .AddOtlpExporter());

        return services;
    }
}
