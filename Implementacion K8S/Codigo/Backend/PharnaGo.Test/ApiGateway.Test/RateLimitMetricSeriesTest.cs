using AspNetCoreRateLimit;
using InstrumentationInterface;
using Moq;
using PharmaGo.ApiGateway.RateLimiting;

namespace PharmaGo.Test.ApiGateway.Test
{
    [TestClass]
    public class RateLimitMetricSeriesTest
    {
        private Mock<ICustomMetrics> _metricsMock;

        [TestInitialize]
        public void SetUp()
        {
            _metricsMock = new Mock<ICustomMetrics>();
        }

        [TestMethod]
        public void InitializesTheRejectedSeriesOfEachEndpointRule()
        {
            var options = OptionsWithRules("POST:/api/login", "get:/api/drug");

            RateLimitMetricSeries.Initialize(options, _metricsMock.Object);

            _metricsMock.Verify(m => m.InitializeHttpRequestSeries("/api/login", "POST", 429), Times.Once);
            _metricsMock.Verify(m => m.InitializeHttpRequestSeries("/api/drug", "GET", 429), Times.Once);
        }

        [TestMethod]
        public void SkipsWildcardRules()
        {
            var options = OptionsWithRules("*", "*:/api/pharmacy", "GET:/api/drug/*");

            RateLimitMetricSeries.Initialize(options, _metricsMock.Object);

            _metricsMock.Verify(m => m.InitializeHttpRequestSeries(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<int>()), Times.Never);
        }

        private static IpRateLimitOptions OptionsWithRules(params string[] endpoints)
        {
            return new IpRateLimitOptions
            {
                HttpStatusCode = 429,
                GeneralRules = endpoints
                    .Select(endpoint => new RateLimitRule { Endpoint = endpoint, Period = "1m", Limit = 10 })
                    .ToList()
            };
        }
    }
}
