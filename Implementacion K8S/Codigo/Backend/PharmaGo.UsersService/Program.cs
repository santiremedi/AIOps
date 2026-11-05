using PharmaGo.UsersService.Factory;
using PharmaGo.UsersService.Filters;
using System.Diagnostics.CodeAnalysis;
using Instrumentation;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

builder.Logging.SuppressEfAndSqlClientLogs();

builder.Services.AddHttpContextAccessor();
builder.Services.RegisterBusinessLogicServices(builder.Configuration);
builder.Services.RegisterDataAccessServices(builder.Configuration);
builder.Services.AddControllers(options => options.Filters.Add(typeof(ExceptionFilter)));

builder.Services.AddControllers();

builder.Services.AddHealthChecks()
    .AddDbContextCheck<DbContext>(tags: new[] { HealthCheckExtensions.ReadinessTag })
    .WithPharmaGoCheckTimeout();

builder.Services.AddPharmaGoOpenTelemetry("PharmaGo.UsersService");

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.AddCors(options =>
{
    options.AddPolicy("MyAllowedOrigins",
        policy =>
        {
            policy.WithOrigins("*")
                .AllowAnyHeader()
                .AllowAnyMethod();
        });
});

var app = builder.Build();

app.MigrateDatabase();
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors("MyAllowedOrigins");
app.UseServiceCorrelationScope();

app.UseAuthorization();

app.MapPharmaGoHealthChecks();
app.UseMetricsMiddleware();

app.MapControllers();

app.Run();

[ExcludeFromCodeCoverage]
public partial class Program { }

