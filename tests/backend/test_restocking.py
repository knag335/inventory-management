"""
Tests for restocking API endpoints (recommendations and submitted orders).
"""
from datetime import datetime, timedelta

import pytest

import main


@pytest.fixture(autouse=True)
def reset_restocking_orders():
    """Submitted orders are module-level state; clear them so tests stay independent."""
    main.restocking_orders.clear()
    yield
    main.restocking_orders.clear()


class TestRestockingRecommendations:
    """Test suite for GET /api/restocking/recommendations."""

    def test_demand_forecasts_include_pricing(self, client):
        """Test that every forecast has the unit cost and lead time the feature relies on."""
        data = client.get("/api/demand").json()
        for forecast in data:
            assert isinstance(forecast["unit_cost"], (int, float))
            assert forecast["unit_cost"] > 0
            assert isinstance(forecast["lead_time_days"], int)
            assert forecast["lead_time_days"] > 0

    def test_get_recommendations_structure(self, client):
        """Test the response shape of the recommendations endpoint."""
        response = client.get("/api/restocking/recommendations?budget=5000")
        assert response.status_code == 200

        data = response.json()
        for key in ["budget", "total_cost", "remaining_budget", "recommendations"]:
            assert key in data
        assert len(data["recommendations"]) > 0

        rec = data["recommendations"][0]
        for key in ["item_sku", "item_name", "trend", "demand_gap", "quantity",
                    "unit_cost", "line_total", "lead_time_days", "partial"]:
            assert key in rec

    def test_recommendations_zero_budget(self, client):
        """Test that a zero budget recommends nothing."""
        data = client.get("/api/restocking/recommendations?budget=0").json()
        assert data["recommendations"] == []
        assert data["total_cost"] == 0

    def test_recommendations_never_exceed_budget(self, client):
        """Test that total cost stays within budget for a range of budgets."""
        for budget in [1, 50, 500, 1999.99, 2500, 3000, 10000]:
            data = client.get(f"/api/restocking/recommendations?budget={budget}").json()
            assert data["total_cost"] <= budget + 0.01
            assert abs(data["remaining_budget"] - (budget - data["total_cost"])) < 0.01

    def test_recommendations_line_total_calculation(self, client):
        """Test that each line total is quantity times unit cost."""
        data = client.get("/api/restocking/recommendations?budget=10000").json()
        for rec in data["recommendations"]:
            assert abs(rec["line_total"] - rec["quantity"] * rec["unit_cost"]) < 0.01
        total = sum(r["line_total"] for r in data["recommendations"])
        assert abs(data["total_cost"] - total) < 0.01

    def test_recommendations_exclude_items_without_shortfall(self, client):
        """Test that items whose forecast is below current demand are skipped."""
        forecasts = client.get("/api/demand").json()
        no_gap = {f["item_sku"] for f in forecasts
                  if f["forecasted_demand"] <= f["current_demand"]}
        assert no_gap  # MTR-304 is decreasing in the sample data

        data = client.get("/api/restocking/recommendations?budget=100000").json()
        recommended = {r["item_sku"] for r in data["recommendations"]}
        assert recommended.isdisjoint(no_gap)

    def test_recommendations_large_budget_fills_every_gap(self, client):
        """Test that an ample budget buys the full gap of every eligible item."""
        data = client.get("/api/restocking/recommendations?budget=100000").json()
        for rec in data["recommendations"]:
            assert rec["partial"] is False
            assert rec["quantity"] == rec["demand_gap"]

    def test_recommendations_priority_order(self, client):
        """Test that increasing-trend items come first, then larger gaps."""
        recs = client.get("/api/restocking/recommendations?budget=100000").json()["recommendations"]
        rank = {"increasing": 0, "stable": 1, "decreasing": 2}
        keys = [(rank[r["trend"].lower()], -r["demand_gap"]) for r in recs]
        assert keys == sorted(keys)

    def test_recommendations_partial_fill_calculation(self, client):
        """Test the greedy cut-off: full first item, partial second, then stop.

        WDG-001 needs 150 units at $12.50 ($1,875). That leaves $125, which buys
        20 units of FLT-405 at $6.20 ($124). Allocation stops after the partial item.
        """
        data = client.get("/api/restocking/recommendations?budget=2000").json()
        recs = data["recommendations"]
        assert [r["item_sku"] for r in recs] == ["WDG-001", "FLT-405"]
        assert recs[0]["quantity"] == 150 and recs[0]["partial"] is False
        assert recs[1]["quantity"] == 20 and recs[1]["partial"] is True
        assert abs(data["total_cost"] - 1999.0) < 0.01

    def test_recommendations_missing_budget(self, client):
        """Test that budget is a required query parameter."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 422

    def test_recommendations_negative_budget(self, client):
        """Test that a negative budget is rejected."""
        response = client.get("/api/restocking/recommendations?budget=-10")
        assert response.status_code == 422


class TestRestockingOrders:
    """Test suite for /api/restocking-orders."""

    def test_get_restocking_orders_initially_empty(self, client):
        """Test that no orders exist before any are submitted."""
        response = client.get("/api/restocking-orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_restocking_order(self, client):
        """Test submitting an order returns the stored order with computed fields."""
        payload = {"budget": 2000, "items": [
            {"item_sku": "WDG-001", "quantity": 10},
            {"item_sku": "GSK-203", "quantity": 5},
        ]}
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["order_number"].startswith("RST-")
        assert abs(order["total_cost"] - (10 * 12.50 + 5 * 2.40)) < 0.01
        assert len(order["items"]) == 2
        assert order["items"][0]["item_name"] == "Industrial Widget Type A"

    def test_create_restocking_order_lead_time_calculation(self, client):
        """Test that order lead time is the slowest item's lead time."""
        payload = {"budget": 5000, "items": [
            {"item_sku": "GSK-203", "quantity": 1},   # 5 days
            {"item_sku": "CTL-330", "quantity": 1},   # 18 days
            {"item_sku": "WDG-001", "quantity": 1},   # 10 days
        ]}
        order = client.post("/api/restocking-orders", json=payload).json()
        assert order["lead_time_days"] == 18

        created = datetime.fromisoformat(order["created_date"])
        expected = datetime.fromisoformat(order["expected_delivery"])
        assert expected - created == timedelta(days=18)

    def test_create_restocking_order_ignores_client_price(self, client):
        """Test that the server uses its own unit cost, not one sent by the client."""
        payload = {"budget": 1000, "items": [
            {"item_sku": "WDG-001", "quantity": 2, "unit_cost": 0.01},
        ]}
        order = client.post("/api/restocking-orders", json=payload).json()
        assert order["items"][0]["unit_cost"] == 12.50
        assert abs(order["total_cost"] - 25.0) < 0.01

    def test_submitted_order_appears_in_list(self, client):
        """Test that orders are listed newest first after submission."""
        first = client.post("/api/restocking-orders", json={
            "budget": 100, "items": [{"item_sku": "GSK-203", "quantity": 1}]}).json()
        second = client.post("/api/restocking-orders", json={
            "budget": 100, "items": [{"item_sku": "FLT-405", "quantity": 1}]}).json()

        data = client.get("/api/restocking-orders").json()
        assert [o["id"] for o in data] == [second["id"], first["id"]]

    def test_create_restocking_order_unknown_sku(self, client):
        """Test that an unknown SKU is rejected."""
        response = client.post("/api/restocking-orders", json={
            "budget": 100, "items": [{"item_sku": "NOPE-999", "quantity": 1}]})
        assert response.status_code == 400
        assert "NOPE-999" in response.json()["detail"]

    def test_create_restocking_order_over_budget(self, client):
        """Test that an order costing more than its budget is rejected and not stored."""
        response = client.post("/api/restocking-orders", json={
            "budget": 10, "items": [{"item_sku": "CTL-330", "quantity": 1}]})
        assert response.status_code == 400
        assert "exceeds budget" in response.json()["detail"]
        assert client.get("/api/restocking-orders").json() == []

    def test_create_restocking_order_invalid_quantity(self, client):
        """Test that zero or negative quantities fail validation."""
        response = client.post("/api/restocking-orders", json={
            "budget": 100, "items": [{"item_sku": "GSK-203", "quantity": 0}]})
        assert response.status_code == 422

    def test_create_restocking_order_empty_items(self, client):
        """Test that an order must contain at least one item."""
        response = client.post("/api/restocking-orders", json={"budget": 100, "items": []})
        assert response.status_code == 422
