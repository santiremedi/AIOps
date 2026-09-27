# When to Mock

Mock at **system boundaries** only:

- External APIs (payment, email, etc.)
- Databases (sometimes - prefer test DB). In this repo: `IRepository<T>` with Moq, or EF Core InMemory
- Time/randomness
- File system (sometimes)

Don't mock:

- Your own classes/modules
- Internal collaborators
- Anything you control

## Designing for Mockability

At system boundaries, design interfaces that are easy to mock:

**1. Use dependency injection**

Pass external dependencies in rather than creating them internally:

```csharp
// Easy to mock
public class PaymentService
{
    private readonly IPaymentClient _client;

    public PaymentService(IPaymentClient client) => _client = client;

    public Receipt Pay(Order order) => _client.Charge(order.Total);
}

// Hard to mock
public class PaymentService
{
    public Receipt Pay(Order order)
    {
        var client = new StripeClient(Environment.GetEnvironmentVariable("STRIPE_KEY"));
        return client.Charge(order.Total);
    }
}
```

**2. Prefer SDK-style interfaces over generic fetchers**

Create specific methods for each external operation instead of one generic method with conditional logic:

```csharp
// GOOD: Each method is independently mockable
public interface IPharmacyApi
{
    User GetUser(int id);
    IEnumerable<Order> GetOrders(int userId);
    Order CreateOrder(OrderRequest request);
}

// BAD: Mocking requires conditional logic inside the mock
public interface IPharmacyApi
{
    HttpResponseMessage Send(string endpoint, HttpMethod method, object body);
}
```

The SDK approach means:

- Each mock returns one specific shape
- No conditional logic in test setup
- Easier to see which endpoints a test exercises
- Type safety per endpoint
