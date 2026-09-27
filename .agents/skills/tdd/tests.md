# Good and Bad Tests

## Good Tests

**Integration-style**: Test through real interfaces, not mocks of internal parts.

```csharp
// GOOD: Tests observable behavior
[TestMethod]
public void UserCanPurchaseDrugWithStock()
{
    var purchase = _purchasesManager.CreatePurchase(PurchaseOf(drug, quantity: 2));

    Assert.AreEqual(PurchaseStatus.Confirmed, purchase.Status);
}
```

Characteristics:

- Tests behavior users/callers care about
- Uses public API only
- Survives internal refactors
- Describes WHAT, not HOW
- One logical assertion per test

## Bad Tests

**Implementation-detail tests**: Coupled to internal structure.

```csharp
// BAD: Tests implementation details
[TestMethod]
public void CreatePurchaseCallsStockManager()
{
    _purchasesManager.CreatePurchase(purchase);

    _stockManager.Verify(s => s.Decrease(drug.Id, 2), Times.Once);
}
```

Red flags:

- Mocking internal collaborators
- Testing private methods
- Asserting on call counts/order
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT
- Verifying through external means instead of interface

```csharp
// BAD: Bypasses interface to verify
[TestMethod]
public void CreateUserSavesToDatabase()
{
    _usersManager.CreateUser(new User { UserName = "alice" });

    Assert.IsNotNull(_context.Users.SingleOrDefault(u => u.UserName == "alice"));
}

// GOOD: Verifies through interface
[TestMethod]
public void CreatedUserIsRetrievable()
{
    var user = _usersManager.CreateUser(new User { UserName = "alice" });

    Assert.AreEqual("alice", _usersManager.GetUser(user.Id).UserName);
}
```

**Tautological tests**: Expected value restates the implementation, so the test passes by construction.

```csharp
// BAD: Expected value is recomputed the way the code computes it
[TestMethod]
public void TotalSumsLineItems()
{
    var lines = new[] { Line(price: 10), Line(price: 5) };
    var expected = lines.Sum(l => l.Price);

    Assert.AreEqual(expected, _purchasesManager.Total(lines));
}

// GOOD: Expected value is an independent, known literal
[TestMethod]
public void TotalSumsLineItems()
{
    Assert.AreEqual(15m, _purchasesManager.Total(new[] { Line(price: 10), Line(price: 5) }));
}
```
