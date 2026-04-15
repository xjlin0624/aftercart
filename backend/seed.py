"""
Seed script — populates Neon with realistic fake data for development.

Usage (from repo root):
    python backend/seed.py

Or from backend/:
    python seed.py

Requires DATABASE_URL to be set in .env (repo root).
"""
import sys
from pathlib import Path

# Make sure app imports resolve when run from repo root or backend/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.core.security import hash_password
from app.models import (
    Alert, DeliveryEvent, Order, OrderItem, OutcomeLog,
    PriceSnapshot, User, UserPreferences,
)
from app.models.enums import (
    ActionTaken, AlertPriority, AlertStatus, AlertType,
    DeliveryEventType, EffortLevel, MessageTone, MonitoringStoppedReason,
    OrderStatus, RecommendedAction, SnapshotSource,
)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

settings = get_settings()
engine = create_engine(settings.database_url)

NOW = datetime.now(timezone.utc)
TODAY = date.today()

SEED_EMAILS = ["alice@example.com", "bob@example.com"]


def clear(session: Session) -> None:
    """Delete all seed users (cascades to all related data)."""
    for email in SEED_EMAILS:
        user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user:
            session.delete(user)
    session.commit()
    print("Cleared existing seed data.")


def run(reset: bool = False) -> None:
    with Session(engine) as session:
        if settings.app_env != "development":
            print(f"Refusing to seed: APP_ENV={settings.app_env} (only runs in development).")
            return

        existing = session.execute(select(User).where(User.email == "alice@example.com")).scalar_one_or_none()
        if existing:
            if not reset:
                print("Seed data already exists — use --reset to wipe and re-seed.")
                return
            clear(session)

        print("Seeding database...")

        # -------------------------------------------------------------------
        # Users
        # -------------------------------------------------------------------
        user1 = User(
            id=uuid4(),
            email="alice@example.com",
            password_hash=hash_password("password123"),
            display_name="Alice",
            is_active=True,
            is_verified=True,
        )
        user2 = User(
            id=uuid4(),
            email="bob@example.com",
            password_hash=hash_password("password123"),
            display_name="Bob",
            is_active=True,
            is_verified=True,
        )
        session.add_all([user1, user2])
        session.flush()
        print(f"  Created users: {user1.email}, {user2.email}")

        # -------------------------------------------------------------------
        # User Preferences
        # -------------------------------------------------------------------
        session.add_all([
            UserPreferences(
                id=uuid4(),
                user_id=user1.id,
                min_savings_threshold=10.0,
                notify_price_drop=True,
                notify_delivery_anomaly=True,
                push_notifications_enabled=False,
                preferred_message_tone=MessageTone.polite,
                monitored_retailers=["amazon", "nike"],
            ),
            UserPreferences(
                id=uuid4(),
                user_id=user2.id,
                min_savings_threshold=5.0,
                notify_price_drop=True,
                notify_delivery_anomaly=False,
                push_notifications_enabled=True,
                preferred_message_tone=MessageTone.firm,
                monitored_retailers=["amazon", "sephora", "target"],
            ),
        ])
        session.flush()
        print("  Created user preferences")

        # -------------------------------------------------------------------
        # Orders
        # -------------------------------------------------------------------
        order1 = Order(
            id=uuid4(),
            user_id=user1.id,
            retailer="amazon",
            retailer_order_id="113-1234567-8901234",
            order_status=OrderStatus.delivered,
            order_date=NOW - timedelta(days=20),
            subtotal=375.97,
            currency="USD",
            return_window_days=30,
            return_deadline=TODAY + timedelta(days=10),
            price_match_eligible=True,
            tracking_number="1Z999AA10123456784",
            carrier="UPS",
            estimated_delivery=TODAY - timedelta(days=5),
            delivered_at=NOW - timedelta(days=5),
            order_url="https://amazon.com/orders/113-1234567-8901234",
        )
        order2 = Order(
            id=uuid4(),
            user_id=user1.id,
            retailer="nike",
            retailer_order_id="NIKE-20240320-001",
            order_status=OrderStatus.in_transit,
            order_date=NOW - timedelta(days=5),
            subtotal=89.99,
            currency="USD",
            return_window_days=60,
            return_deadline=TODAY + timedelta(days=55),
            price_match_eligible=False,
            tracking_number="9400111899223397662958",
            carrier="USPS",
            estimated_delivery=TODAY + timedelta(days=2),
            order_url="https://nike.com/orders/NIKE-20240320-001",
        )
        order3 = Order(
            id=uuid4(),
            user_id=user2.id,
            retailer="amazon",
            retailer_order_id="113-9876543-2109876",
            order_status=OrderStatus.shipped,
            order_date=NOW - timedelta(days=3),
            subtotal=234.50,
            currency="USD",
            return_window_days=30,
            return_deadline=TODAY + timedelta(days=27),
            price_match_eligible=True,
            tracking_number="1Z999AA10123456785",
            carrier="UPS",
            estimated_delivery=TODAY + timedelta(days=4),
            order_url="https://amazon.com/orders/113-9876543-2109876",
        )
        session.add_all([order1, order2, order3])
        session.flush()
        print(f"  Created {3} orders")

        # -------------------------------------------------------------------
        # Order Items
        # -------------------------------------------------------------------
        item1 = OrderItem(
            id=uuid4(),
            order_id=order1.id,
            user_id=user1.id,
            product_name="Sony WH-1000XM5 Wireless Headphones",
            variant="Black",
            sku="WH1000XM5/B",
            product_url="https://amazon.com/dp/B09XS7JWHH",
            image_url="https://m.media-amazon.com/images/I/61kV6AMZD9L.jpg",
            quantity=1,
            paid_price=349.99,
            current_price=299.99,
            is_monitoring_active=True,
        )
        item2 = OrderItem(
            id=uuid4(),
            order_id=order1.id,
            user_id=user1.id,
            product_name="Anker USB-C Charging Cable 6ft",
            sku="A8186011",
            product_url="https://amazon.com/dp/B07ZVG3TQG",
            quantity=2,
            paid_price=12.99,
            current_price=12.99,
            is_monitoring_active=False,
            monitoring_stopped_reason=MonitoringStoppedReason.delivered_and_settled,
        )
        item3 = OrderItem(
            id=uuid4(),
            order_id=order2.id,
            user_id=user1.id,
            product_name="Nike Air Max 270",
            variant="White/Black, Size 10",
            sku="AH8050-100",
            product_url="https://nike.com/t/air-max-270-mens-shoes",
            quantity=1,
            paid_price=89.99,
            current_price=89.99,
            is_monitoring_active=True,
        )
        item4 = OrderItem(
            id=uuid4(),
            order_id=order3.id,
            user_id=user2.id,
            product_name="Apple AirPods Pro (2nd Generation)",
            variant="White",
            sku="MTJV3LL/A",
            product_url="https://amazon.com/dp/B0BDHWDR12",
            quantity=1,
            paid_price=249.00,
            current_price=219.00,
            is_monitoring_active=True,
        )
        session.add_all([item1, item2, item3, item4])
        session.flush()
        print(f"  Created {4} order items")

        # -------------------------------------------------------------------
        # Price Snapshots
        # -------------------------------------------------------------------
        session.add_all([
            PriceSnapshot(
                id=uuid4(),
                order_item_id=item1.id,
                scraped_price=349.99,
                original_paid_price=349.99,
                snapshot_source=SnapshotSource.extension_capture,
                scraped_at=NOW - timedelta(days=20),
            ),
            PriceSnapshot(
                id=uuid4(),
                order_item_id=item1.id,
                scraped_price=319.99,
                original_paid_price=349.99,
                snapshot_source=SnapshotSource.scheduled_job,
                scraped_at=NOW - timedelta(days=10),
            ),
            PriceSnapshot(
                id=uuid4(),
                order_item_id=item1.id,
                scraped_price=299.99,
                original_paid_price=349.99,
                snapshot_source=SnapshotSource.scheduled_job,
                scraped_at=NOW - timedelta(days=2),
            ),
            PriceSnapshot(
                id=uuid4(),
                order_item_id=item4.id,
                scraped_price=249.00,
                original_paid_price=249.00,
                snapshot_source=SnapshotSource.extension_capture,
                scraped_at=NOW - timedelta(days=3),
            ),
            PriceSnapshot(
                id=uuid4(),
                order_item_id=item4.id,
                scraped_price=219.00,
                original_paid_price=249.00,
                snapshot_source=SnapshotSource.scheduled_job,
                scraped_at=NOW - timedelta(days=1),
            ),
        ])
        session.flush()
        print("  Created price snapshots")

        # -------------------------------------------------------------------
        # Delivery Events
        # -------------------------------------------------------------------
        session.add_all([
            DeliveryEvent(
                id=uuid4(),
                order_id=order2.id,
                event_type=DeliveryEventType.status_changed,
                is_anomaly=False,
                scraped_at=NOW - timedelta(days=3),
                notes="Package picked up by USPS.",
            ),
            DeliveryEvent(
                id=uuid4(),
                order_id=order2.id,
                event_type=DeliveryEventType.eta_updated,
                previous_eta=TODAY + timedelta(days=1),
                new_eta=TODAY + timedelta(days=2),
                is_anomaly=True,
                scraped_at=NOW - timedelta(days=1),
                notes="ETA slipped from tomorrow to in 2 days.",
            ),
            DeliveryEvent(
                id=uuid4(),
                order_id=order3.id,
                event_type=DeliveryEventType.status_changed,
                is_anomaly=False,
                scraped_at=NOW - timedelta(days=2),
                notes="Package shipped from fulfillment center.",
            ),
        ])
        session.flush()
        print("  Created delivery events")

        # -------------------------------------------------------------------
        # Alerts
        # -------------------------------------------------------------------
        alert1 = Alert(
            id=uuid4(),
            user_id=user1.id,
            order_id=order1.id,
            order_item_id=item1.id,
            alert_type=AlertType.price_drop,
            status=AlertStatus.new,
            priority=AlertPriority.high,
            title="Price dropped on Sony WH-1000XM5",
            body="The Sony WH-1000XM5 you bought for $349.99 is now $299.99 — you could save $50.00.",
            recommended_action=RecommendedAction.price_match,
            estimated_savings=50.00,
            estimated_effort=EffortLevel.low,
            effort_steps_estimate=3,
            recommendation_rationale="Price dropped $50 within your 30-day return window.",
            days_remaining_return=(TODAY + timedelta(days=10) - TODAY).days,
            action_deadline=TODAY + timedelta(days=10),
            evidence={
                "paid_price": 349.99,
                "current_price": 299.99,
                "price_delta": 50.00,
                "snapshots": [299.99, 319.99],
            },
        )
        alert2 = Alert(
            id=uuid4(),
            user_id=user1.id,
            order_id=order2.id,
            alert_type=AlertType.delivery_anomaly,
            status=AlertStatus.new,
            priority=AlertPriority.medium,
            title="Delivery date slipped for Nike order",
            body="Your Nike Air Max 270 delivery moved from tomorrow to in 2 days.",
            evidence={
                "event_type": "eta_updated",
                "previous_eta": (TODAY + timedelta(days=1)).isoformat(),
                "new_eta": (TODAY + timedelta(days=2)).isoformat(),
            },
        )
        alert3 = Alert(
            id=uuid4(),
            user_id=user2.id,
            order_id=order3.id,
            order_item_id=item4.id,
            alert_type=AlertType.price_drop,
            status=AlertStatus.viewed,
            priority=AlertPriority.high,
            title="Price dropped on AirPods Pro",
            body="The AirPods Pro you bought for $249.00 is now $219.00 — you could save $30.00.",
            recommended_action=RecommendedAction.price_match,
            estimated_savings=30.00,
            estimated_effort=EffortLevel.low,
            effort_steps_estimate=2,
            days_remaining_return=27,
            action_deadline=TODAY + timedelta(days=27),
            evidence={
                "paid_price": 249.00,
                "current_price": 219.00,
                "price_delta": 30.00,
            },
        )
        session.add_all([alert1, alert2, alert3])
        session.flush()
        print(f"  Created {3} alerts")

        # -------------------------------------------------------------------
        # Outcome Logs
        # -------------------------------------------------------------------
        session.add_all([
            OutcomeLog(
                id=uuid4(),
                user_id=user1.id,
                alert_id=alert1.id,
                order_item_id=item1.id,
                action_taken=ActionTaken.price_matched,
                recovered_value=50.00,
                was_successful=True,
                notes="Called Amazon support, got $50 credit applied.",
            ),
        ])
        session.flush()
        print("  Created outcome logs")

        session.commit()
        print("\nDone! Seeded:")
        print("  2 users (alice@example.com / bob@example.com, password: password123)")
        print("  3 orders, 4 order items, 5 price snapshots")
        print("  3 delivery events, 3 alerts, 1 outcome log")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed development data into the database.")
    parser.add_argument("--reset", action="store_true", help="Wipe existing seed data and re-seed.")
    args = parser.parse_args()
    run(reset=args.reset)
