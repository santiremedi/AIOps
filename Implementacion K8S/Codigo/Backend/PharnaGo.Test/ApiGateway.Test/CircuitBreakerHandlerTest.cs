using System.Net;
using InstrumentationInterface;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using PharmaGo.ApiGateway.Resilience;

namespace PharmaGo.Test.ApiGateway.Test
{
    [TestClass]
    public class CircuitBreakerHandlerTest
    {
        private const string ClusterId = "pharmacy-cluster";
        private const int MinimumThroughput = 2;

        private StubBackendHandler _backend;
        private Mock<ICustomMetrics> _metricsMock;
        private CircuitBreakerOptions _options;

        [TestInitialize]
        public void SetUp()
        {
            _backend = new StubBackendHandler();
            _metricsMock = new Mock<ICustomMetrics>();
            _options = new CircuitBreakerOptions
            {
                FailureRatio = 0.5,
                SamplingDuration = TimeSpan.FromSeconds(10),
                MinimumThroughput = MinimumThroughput,
                DurationOfBreak = TimeSpan.FromMilliseconds(200),
                RequestTimeout = TimeSpan.FromSeconds(5)
            };
        }

        [TestMethod]
        public async Task ServerErrorsOpenTheCircuitAndNextRequestFailsFast()
        {
            var client = CreateClient();
            _backend.RespondWith(HttpStatusCode.InternalServerError);

            await SendRequests(client, MinimumThroughput);
            var response = await client.SendAsync(NewRequest(), CancellationToken.None);

            Assert.AreEqual(HttpStatusCode.ServiceUnavailable, response.StatusCode);
            Assert.AreEqual("open", response.Headers.GetValues(CircuitBreakerHandler.CircuitStateHeader).Single());
            Assert.IsNotNull(response.Headers.RetryAfter);
            Assert.AreEqual(MinimumThroughput, _backend.Calls);
            _metricsMock.Verify(m => m.RecordCircuitBreakerTransition(ClusterId, "open"), Times.Once);
        }

        [TestMethod]
        public async Task ClientErrorsDoNotOpenTheCircuit()
        {
            var client = CreateClient();
            _backend.RespondWith(HttpStatusCode.BadRequest);

            var responses = await SendRequests(client, MinimumThroughput * 3);

            Assert.IsTrue(responses.All(r => r.StatusCode == HttpStatusCode.BadRequest));
            Assert.AreEqual(MinimumThroughput * 3, _backend.Calls);
            _metricsMock.Verify(m => m.RecordCircuitBreakerTransition(It.IsAny<string>(), It.IsAny<string>()), Times.Never);
        }

        [TestMethod]
        public async Task ConnectionFailuresOpenTheCircuit()
        {
            var client = CreateClient();
            _backend.Respond = _ => throw new HttpRequestException("Connection refused");

            for (var i = 0; i < MinimumThroughput; i++)
            {
                await Assert.ThrowsExceptionAsync<HttpRequestException>(() => client.SendAsync(NewRequest(), CancellationToken.None));
            }
            var response = await client.SendAsync(NewRequest(), CancellationToken.None);

            Assert.AreEqual(HttpStatusCode.ServiceUnavailable, response.StatusCode);
            Assert.AreEqual(MinimumThroughput, _backend.Calls);
        }

        [TestMethod]
        public async Task CircuitClosesAfterBreakWhenTrialRequestSucceeds()
        {
            var client = CreateClient();
            _backend.RespondWith(HttpStatusCode.InternalServerError);
            await SendRequests(client, MinimumThroughput);

            await Task.Delay(_options.DurationOfBreak * 2);
            _backend.RespondWith(HttpStatusCode.OK);
            var responses = await SendRequests(client, 2);

            Assert.IsTrue(responses.All(r => r.StatusCode == HttpStatusCode.OK));
            _metricsMock.Verify(m => m.RecordCircuitBreakerTransition(ClusterId, "half_open"), Times.Once);
            _metricsMock.Verify(m => m.RecordCircuitBreakerTransition(ClusterId, "closed"), Times.Once);
        }

        [TestMethod]
        public async Task SlowBackendReturnsGatewayTimeout()
        {
            _options.RequestTimeout = TimeSpan.FromMilliseconds(50);
            var client = CreateClient();
            _backend.Respond = async token =>
            {
                await Task.Delay(TimeSpan.FromSeconds(5), token);
                return new HttpResponseMessage(HttpStatusCode.OK);
            };

            var response = await client.SendAsync(NewRequest(), CancellationToken.None);

            Assert.AreEqual(HttpStatusCode.GatewayTimeout, response.StatusCode);
        }

        private HttpMessageInvoker CreateClient()
        {
            var handler = new CircuitBreakerHandler(ClusterId, _options, _metricsMock.Object, NullLogger<CircuitBreakerHandler>.Instance)
            {
                InnerHandler = _backend
            };
            return new HttpMessageInvoker(handler);
        }

        private static async Task<List<HttpResponseMessage>> SendRequests(HttpMessageInvoker client, int count)
        {
            var responses = new List<HttpResponseMessage>();
            for (var i = 0; i < count; i++)
            {
                responses.Add(await client.SendAsync(NewRequest(), CancellationToken.None));
            }
            return responses;
        }

        private static HttpRequestMessage NewRequest()
        {
            return new HttpRequestMessage(HttpMethod.Get, "http://pharmago-pharmacy-service/api/drug");
        }

        private sealed class StubBackendHandler : HttpMessageHandler
        {
            public Func<CancellationToken, Task<HttpResponseMessage>> Respond { get; set; } =
                _ => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK));

            public int Calls { get; private set; }

            public void RespondWith(HttpStatusCode statusCode)
            {
                Respond = _ => Task.FromResult(new HttpResponseMessage(statusCode));
            }

            protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
            {
                Calls++;
                return Respond(cancellationToken);
            }
        }
    }
}
