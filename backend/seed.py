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

from sqlalchemy import create_engine, delete, select
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


def clear_all(session: Session) -> None:
    """Delete ALL users and their cascaded data."""
    session.execute(delete(User))
    session.commit()
    print("Cleared all users and related data.")


def run(reset: bool = False, wipe_all: bool = False) -> None:
    with Session(engine) as session:
        if settings.app_env != "development":
            print(f"Refusing to seed: APP_ENV={settings.app_env} (only runs in development).")
            return

        if wipe_all:
            clear_all(session)
        else:
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
                monitored_retailers=["nike", "sephora"],
            ),
            UserPreferences(
                id=uuid4(),
                user_id=user2.id,
                min_savings_threshold=5.0,
                notify_price_drop=True,
                notify_delivery_anomaly=False,
                push_notifications_enabled=True,
                preferred_message_tone=MessageTone.firm,
                monitored_retailers=["nike", "sephora"],
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
            retailer="sephora",
            retailer_order_id="SEPH-20260325-005",
            order_status=OrderStatus.delivered,
            order_date=NOW - timedelta(days=20),
            subtotal=362.98,
            currency="USD",
            return_window_days=30,
            return_deadline=TODAY + timedelta(days=10),
            price_match_eligible=True,
            tracking_number="1Z999AA10123456784",
            carrier="UPS",
            estimated_delivery=TODAY - timedelta(days=5),
            delivered_at=NOW - timedelta(days=5),
            order_url="https://sephora.com/orders/SEPH-20260325-005",
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
            retailer="nike",
            retailer_order_id="NIKE-20260412-007",
            order_status=OrderStatus.shipped,
            order_date=NOW - timedelta(days=3),
            subtotal=234.50,
            currency="USD",
            return_window_days=60,
            return_deadline=TODAY + timedelta(days=57),
            price_match_eligible=True,
            tracking_number="1Z999AA10123456785",
            carrier="UPS",
            estimated_delivery=TODAY + timedelta(days=4),
            order_url="https://nike.com/orders/NIKE-20260412-007",
        )
        # Nike + Sephora orders spread across past 6 months
        order4 = Order(
            id=uuid4(),
            user_id=user1.id,
            retailer="nike",
            retailer_order_id="NIKE-20251015-002",
            order_status=OrderStatus.delivered,
            order_date=NOW - timedelta(days=182),  # ~Oct 2025
            subtotal=110.00,
            currency="USD",
            return_window_days=60,
            return_deadline=TODAY - timedelta(days=122),
            price_match_eligible=True,
            tracking_number="9400111899223397662959",
            carrier="USPS",
            estimated_delivery=(NOW - timedelta(days=176)).date(),
            delivered_at=NOW - timedelta(days=176),
            order_url="https://nike.com/orders/NIKE-20251015-002",
        )
        order5 = Order(
            id=uuid4(),
            user_id=user1.id,
            retailer="sephora",
            retailer_order_id="SEPH-20251110-001",
            order_status=OrderStatus.delivered,
            order_date=NOW - timedelta(days=156),  # ~Nov 2025
            subtotal=34.00,
            currency="USD",
            return_window_days=30,
            return_deadline=TODAY - timedelta(days=126),
            price_match_eligible=True,
            order_url="https://sephora.com/orders/SEPH-20251110-001",
        )
        order6 = Order(
            id=uuid4(),
            user_id=user1.id,
            retailer="nike",
            retailer_order_id="NIKE-20251205-003",
            order_status=OrderStatus.delivered,
            order_date=NOW - timedelta(days=131),  # ~Dec 2025
            subtotal=160.00,
            currency="USD",
            return_window_days=60,
            return_deadline=TODAY - timedelta(days=71),
            price_match_eligible=True,
            tracking_number="9400111899223397662960",
            carrier="USPS",
            estimated_delivery=(NOW - timedelta(days=125)).date(),
            delivered_at=NOW - timedelta(days=125),
            order_url="https://nike.com/orders/NIKE-20251205-003",
        )
        order7 = Order(
            id=uuid4(),
            user_id=user1.id,
            retailer="sephora",
            retailer_order_id="SEPH-20251218-002",
            order_status=OrderStatus.delivered,
            order_date=NOW - timedelta(days=118),  # ~Dec 2025
            subtotal=68.00,
            currency="USD",
            return_window_days=30,
            return_deadline=TODAY - timedelta(days=88),
            price_match_eligible=True,
            order_url="https://sephora.com/orders/SEPH-20251218-002",
        )
        order8 = Order(
            id=uuid4(),
            user_id=user1.id,
            retailer="nike",
            retailer_order_id="NIKE-20260115-004",
            order_status=OrderStatus.delivered,
            order_date=NOW - timedelta(days=90),  # ~Jan 2026
            subtotal=35.00,
            currency="USD",
            return_window_days=60,
            return_deadline=TODAY - timedelta(days=30),
            price_match_eligible=False,
            tracking_number="9400111899223397662961",
            carrier="USPS",
            estimated_delivery=(NOW - timedelta(days=84)).date(),
            delivered_at=NOW - timedelta(days=84),
            order_url="https://nike.com/orders/NIKE-20260115-004",
        )
        order9 = Order(
            id=uuid4(),
            user_id=user1.id,
            retailer="nike",
            retailer_order_id="NIKE-20260210-005",
            order_status=OrderStatus.delivered,
            order_date=NOW - timedelta(days=64),  # ~Feb 2026
            subtotal=100.00,
            currency="USD",
            return_window_days=60,
            return_deadline=TODAY + timedelta(days=4),
            price_match_eligible=True,
            tracking_number="9400111899223397662962",
            carrier="USPS",
            estimated_delivery=(NOW - timedelta(days=58)).date(),
            delivered_at=NOW - timedelta(days=58),
            order_url="https://nike.com/orders/NIKE-20260210-005",
        )
        order10 = Order(
            id=uuid4(),
            user_id=user1.id,
            retailer="sephora",
            retailer_order_id="SEPH-20260220-003",
            order_status=OrderStatus.delivered,
            order_date=NOW - timedelta(days=54),  # ~Feb 2026
            subtotal=38.00,
            currency="USD",
            return_window_days=30,
            return_deadline=TODAY - timedelta(days=24),
            price_match_eligible=False,
            order_url="https://sephora.com/orders/SEPH-20260220-003",
        )
        order11 = Order(
            id=uuid4(),
            user_id=user2.id,
            retailer="sephora",
            retailer_order_id="SEPH-20251120-004",
            order_status=OrderStatus.delivered,
            order_date=NOW - timedelta(days=146),  # ~Nov 2025
            subtotal=40.00,
            currency="USD",
            return_window_days=30,
            return_deadline=TODAY - timedelta(days=116),
            price_match_eligible=True,
            order_url="https://sephora.com/orders/SEPH-20251120-004",
        )
        order12 = Order(
            id=uuid4(),
            user_id=user2.id,
            retailer="nike",
            retailer_order_id="NIKE-20260310-006",
            order_status=OrderStatus.delivered,
            order_date=NOW - timedelta(days=36),  # ~Mar 2026
            subtotal=130.00,
            currency="USD",
            return_window_days=60,
            return_deadline=TODAY + timedelta(days=24),
            price_match_eligible=True,
            tracking_number="9400111899223397662963",
            carrier="USPS",
            estimated_delivery=(NOW - timedelta(days=30)).date(),
            delivered_at=NOW - timedelta(days=30),
            order_url="https://nike.com/orders/NIKE-20260310-006",
        )

        session.add_all([order1, order2, order3, order4, order5, order6, order7, order8, order9, order10, order11, order12])
        session.flush()
        print(f"  Created {12} orders")

        # -------------------------------------------------------------------
        # Order Items
        # -------------------------------------------------------------------
        item1 = OrderItem(
            id=uuid4(),
            order_id=order1.id,
            user_id=user1.id,
            product_name="La Mer The Moisturizing Cream (3.4 oz)",
            variant="3.4 oz",
            sku="LMMC34",
            product_url="https://sephora.com/product/the-moisturizing-cream-P11454",
            quantity=1,
            paid_price=349.99,
            current_price=299.99,
            is_monitoring_active=True,
        )
        item2 = OrderItem(
            id=uuid4(),
            order_id=order1.id,
            user_id=user1.id,
            product_name="Fresh Rose Face Mask (30ml)",
            product_url="https://sephora.com/product/rose-face-mask-P229268",
            quantity=1,
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
            product_name="Nike Air Jordan 1 Retro High OG",
            variant="Chicago, Size 10",
            sku="555088-101",
            product_url="https://nike.com/t/air-jordan-1-retro-high-og-mens-shoes/555088-101",
            quantity=1,
            paid_price=234.50,
            current_price=209.00,
            is_monitoring_active=True,
        )
        item5 = OrderItem(
            id=uuid4(),
            order_id=order4.id,
            user_id=user1.id,
            product_name="Nike Air Force 1 '07",
            variant="White, Size 10",
            sku="CW2288-111",
            product_url="https://nike.com/t/air-force-1-07-mens-shoes",
            quantity=1,
            paid_price=110.00,
            current_price=90.00,
            is_monitoring_active=False,
            monitoring_stopped_reason=MonitoringStoppedReason.delivered_and_settled,
        )
        item6 = OrderItem(
            id=uuid4(),
            order_id=order5.id,
            user_id=user1.id,
            product_name="Charlotte Tilbury Matte Revolution Lipstick",
            variant="Pillow Talk",
            product_url="https://sephora.com/product/matte-revolution-lipstick",
            quantity=1,
            paid_price=34.00,
            current_price=34.00,
            is_monitoring_active=False,
            monitoring_stopped_reason=MonitoringStoppedReason.delivered_and_settled,
        )
        item7 = OrderItem(
            id=uuid4(),
            order_id=order6.id,
            user_id=user1.id,
            product_name="Nike React Infinity Run Flyknit 3",
            variant="Black/White, Size 10",
            sku="DH5392-001",
            product_url="https://nike.com/t/react-infinity-run-flyknit-3-mens-road-running-shoes",
            quantity=1,
            paid_price=160.00,
            current_price=130.00,
            is_monitoring_active=False,
            monitoring_stopped_reason=MonitoringStoppedReason.delivered_and_settled,
        )
        item8 = OrderItem(
            id=uuid4(),
            order_id=order7.id,
            user_id=user1.id,
            product_name="Drunk Elephant Protini Polypeptide Moisturizer",
            variant="50ml",
            product_url="https://sephora.com/product/protini-polypeptide-moisturizer",
            quantity=1,
            paid_price=68.00,
            current_price=58.00,
            is_monitoring_active=False,
            monitoring_stopped_reason=MonitoringStoppedReason.delivered_and_settled,
        )
        item9 = OrderItem(
            id=uuid4(),
            order_id=order8.id,
            user_id=user1.id,
            product_name="Nike Dri-FIT Training T-Shirt",
            variant="Navy, Size M",
            sku="AR6029-451",
            product_url="https://nike.com/t/dri-fit-training-t-shirt",
            quantity=1,
            paid_price=35.00,
            current_price=35.00,
            is_monitoring_active=False,
            monitoring_stopped_reason=MonitoringStoppedReason.delivered_and_settled,
        )
        item10 = OrderItem(
            id=uuid4(),
            order_id=order9.id,
            user_id=user1.id,
            product_name="Nike Blazer Mid '77 Vintage",
            variant="White/Black, Size 10",
            sku="BQ6806-100",
            product_url="https://nike.com/t/blazer-mid-77-vintage-mens-shoes",
            quantity=1,
            paid_price=100.00,
            current_price=85.00,
            is_monitoring_active=True,
        )
        item11 = OrderItem(
            id=uuid4(),
            order_id=order10.id,
            user_id=user1.id,
            product_name="Tatcha The Rice Wash Cleanser",
            variant="150ml",
            product_url="https://sephora.com/product/the-rice-wash-skin-softening-cleanser",
            quantity=1,
            paid_price=38.00,
            current_price=38.00,
            is_monitoring_active=False,
            monitoring_stopped_reason=MonitoringStoppedReason.delivered_and_settled,
        )
        item12 = OrderItem(
            id=uuid4(),
            order_id=order11.id,
            user_id=user2.id,
            product_name="Fenty Beauty Pro Filt'r Foundation",
            variant="Shade 260N",
            product_url="https://sephora.com/product/pro-filtr-soft-matte-longwear-foundation",
            quantity=1,
            paid_price=40.00,
            current_price=36.00,
            is_monitoring_active=False,
            monitoring_stopped_reason=MonitoringStoppedReason.delivered_and_settled,
        )
        item13 = OrderItem(
            id=uuid4(),
            order_id=order12.id,
            user_id=user2.id,
            product_name="Nike Air Zoom Pegasus 40",
            variant="Blue/White, Size 9",
            sku="DV3853-400",
            product_url="https://nike.com/t/air-zoom-pegasus-40-mens-road-running-shoes",
            quantity=1,
            paid_price=130.00,
            current_price=110.00,
            is_monitoring_active=True,
        )

        session.add_all([item1, item2, item3, item4, item5, item6, item7, item8, item9, item10, item11, item12, item13])
        session.flush()
        print(f"  Created {13} order items")

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
                scraped_price=234.50,
                original_paid_price=234.50,
                snapshot_source=SnapshotSource.extension_capture,
                scraped_at=NOW - timedelta(days=3),
            ),
            PriceSnapshot(
                id=uuid4(),
                order_item_id=item4.id,
                scraped_price=209.00,
                original_paid_price=234.50,
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
                notes="Package shipped from Nike warehouse.",
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
            title="Price dropped on La Mer Moisturizing Cream",
            body="The La Mer Moisturizing Cream you bought for $349.99 is now $299.99 — you could save $50.00.",
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
                "snapshots": [299.99, 324.99],
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
            title="Price dropped on Nike Air Jordan 1 Retro High OG",
            body="The Nike Air Jordan 1 you bought for $234.50 is now $209.00 — you could save $25.50.",
            recommended_action=RecommendedAction.price_match,
            estimated_savings=25.50,
            estimated_effort=EffortLevel.low,
            effort_steps_estimate=2,
            days_remaining_return=57,
            action_deadline=TODAY + timedelta(days=57),
            evidence={
                "paid_price": 234.50,
                "current_price": 209.00,
                "price_delta": 25.50,
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
                notes="Contacted Sephora support via chat, got $50 credit applied.",
                logged_at=NOW - timedelta(days=2),
            ),
            # Oct 2025 — Nike Air Force 1 price match
            OutcomeLog(
                id=uuid4(),
                user_id=user1.id,
                order_item_id=item5.id,
                action_taken=ActionTaken.price_matched,
                recovered_value=20.00,
                was_successful=True,
                notes="Nike price match granted via chat support.",
                logged_at=NOW - timedelta(days=170),
            ),
            # Nov 2025 — Sephora Charlotte Tilbury, no savings (price held)
            OutcomeLog(
                id=uuid4(),
                user_id=user1.id,
                order_item_id=item6.id,
                action_taken=ActionTaken.ignored,
                recovered_value=0.00,
                was_successful=False,
                notes="Price did not drop within return window.",
                logged_at=NOW - timedelta(days=140),
            ),
            # Dec 2025 — Nike React Infinity Run price match
            OutcomeLog(
                id=uuid4(),
                user_id=user1.id,
                order_item_id=item7.id,
                action_taken=ActionTaken.price_matched,
                recovered_value=30.00,
                was_successful=True,
                notes="Nike online price match applied successfully.",
                logged_at=NOW - timedelta(days=118),
            ),
            # Dec 2025 — Drunk Elephant price match
            OutcomeLog(
                id=uuid4(),
                user_id=user1.id,
                order_item_id=item8.id,
                action_taken=ActionTaken.price_matched,
                recovered_value=10.00,
                was_successful=True,
                notes="Sephora Beauty Insider price match via email.",
                logged_at=NOW - timedelta(days=105),
            ),
            # Feb 2026 — Nike Blazer Mid price match
            OutcomeLog(
                id=uuid4(),
                user_id=user1.id,
                order_item_id=item10.id,
                action_taken=ActionTaken.price_matched,
                recovered_value=15.00,
                was_successful=True,
                notes="Nike price match approved within return window.",
                logged_at=NOW - timedelta(days=50),
            ),
            # Nov 2025 — Fenty Beauty price match (bob)
            OutcomeLog(
                id=uuid4(),
                user_id=user2.id,
                order_item_id=item12.id,
                action_taken=ActionTaken.price_matched,
                recovered_value=4.00,
                was_successful=True,
                notes="Sephora matched sale price via app chat.",
                logged_at=NOW - timedelta(days=130),
            ),
            # Mar 2026 — Nike Pegasus price match pending (bob)
            OutcomeLog(
                id=uuid4(),
                user_id=user2.id,
                order_item_id=item13.id,
                action_taken=ActionTaken.price_matched,
                recovered_value=20.00,
                was_successful=True,
                notes="Nike price match confirmed by support team.",
                logged_at=NOW - timedelta(days=25),
            ),
        ])
        session.flush()
        print("  Created outcome logs")

        session.commit()
        print("\nDone! Seeded:")
        print("  2 users (alice@example.com / bob@example.com, password: password123)")
        print("  12 orders, 13 order items, 5 price snapshots")
        print("  3 delivery events, 3 alerts, 8 outcome logs")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed development data into the database.")
    parser.add_argument("--reset", action="store_true", help="Wipe existing seed data and re-seed.")
    parser.add_argument("--wipe-all", action="store_true", help="Delete ALL users (not just seed users) then re-seed.")
    args = parser.parse_args()
    run(reset=args.reset, wipe_all=args.wipe_all)
