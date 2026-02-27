# Data Models

> **Stack:** PostgreSQL (primary) · Redis (cache/queue)  
> **ORM:** SQLAlchemy 2.0+ · **Migrations:** Alembic

---

## Table of Contents
1. [User](#1-user)
2. [UserPreferences](#2-userpreferences)
3. [Order](#3-order)
4. [OrderItem](#4-orderitem)
5. [PriceSnapshot](#5-pricesnapshot)
6. [Alert](#6-alert)
7. [DeliveryEvent](#7-deliveryevent)
8. [Subscription](#8-subscription)
9. [OutcomeLog](#9-outcomelog)
10. [Relationships Diagram](#10-relationships-diagram)
11. [Key Enums](#11-key-enums)

---

## 1. User

Stores authentication credentials and account-level metadata.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK, default `gen_random_uuid()` | Primary key |
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL | Login email |
| `password_hash` | `VARCHAR(255)` | NOT NULL | Bcrypt hash |
| `display_name` | `VARCHAR(100)` | NULLABLE | Optional display name |
| `is_active` | `BOOLEAN` | default `true` | Account enabled flag |
| `is_verified` | `BOOLEAN` | default `false` | Email verification status |
| `refresh_token_hash` | `VARCHAR(255)` | NULLABLE | Hashed current refresh token (rotation) |
| `created_at` | `TIMESTAMPTZ` | default `now()` | Account creation time |
| `updated_at` | `TIMESTAMPTZ` | auto-update | Last modified time |

**Relations:** one-to-one → `UserPreferences`; one-to-many → `Order`, `Alert`, `Subscription`, `OutcomeLog`

---

## 2. UserPreferences

Per-user configuration for alerts, notifications, and monitoring behavior. (FR-2)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | Primary key |
| `user_id` | `UUID` | FK → `users.id`, UNIQUE, NOT NULL | Owning user |
| `min_savings_threshold` | `NUMERIC(8,2)` | default `10.00` | Minimum USD savings to trigger an alert |
| `notify_price_drop` | `BOOLEAN` | default `true` | Enable price drop alerts |
| `notify_delivery_anomaly` | `BOOLEAN` | default `true` | Enable delivery anomaly alerts |
| `notify_subscription` | `BOOLEAN` | default `true` | Enable subscription/recurring spend alerts |
| `push_notifications_enabled` | `BOOLEAN` | default `false` | Browser push opt-in |
| `preferred_message_tone` | `ENUM('polite','firm','concise')` | default `'polite'` | Default tone for generated messages |
| `monitored_retailers` | `TEXT[]` | default `'{}'` | List of retailer slugs the user has enabled |
| `updated_at` | `TIMESTAMPTZ` | auto-update | Last modified time |

---

## 3. Order

A single order imported from a retailer, captured by the browser extension. (FR-3, FR-4, FR-5)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | Primary key |
| `user_id` | `UUID` | FK → `users.id`, NOT NULL | Owning user |
| `retailer` | `VARCHAR(50)` | NOT NULL | Retailer slug, e.g. `"nike"`, `"sephora"` |
| `retailer_order_id` | `VARCHAR(255)` | NOT NULL | Retailer's own order identifier |
| `order_status` | `ENUM('pending','shipped','in_transit','delivered','cancelled','returned')` | NOT NULL | Current fulfillment status |
| `order_date` | `TIMESTAMPTZ` | NOT NULL | Date of purchase |
| `subtotal` | `NUMERIC(10,2)` | NOT NULL | Pre-tax/shipping total paid |
| `currency` | `CHAR(3)` | default `'USD'` | ISO 4217 currency code |
| `return_window_days` | `INTEGER` | NULLABLE | Return eligibility window in days from order date |
| `return_deadline` | `DATE` | NULLABLE | Computed absolute deadline for returns |
| `price_match_eligible` | `BOOLEAN` | default `false` | Whether retailer supports post-purchase price match |
| `tracking_number` | `VARCHAR(100)` | NULLABLE | Carrier tracking number |
| `carrier` | `VARCHAR(50)` | NULLABLE | Carrier name, e.g. `"UPS"`, `"FedEx"` |
| `estimated_delivery` | `DATE` | NULLABLE | Current ETA from retailer |
| `delivered_at` | `TIMESTAMPTZ` | NULLABLE | Actual delivery timestamp |
| `order_url` | `TEXT` | NULLABLE | Direct URL to order details page |
| `raw_capture` | `JSONB` | NULLABLE | Raw DOM-extracted data for debugging/auditing |
| `created_at` | `TIMESTAMPTZ` | default `now()` | Record creation time |
| `updated_at` | `TIMESTAMPTZ` | auto-update | Last modified time |

**Unique constraint:** `(user_id, retailer, retailer_order_id)` — enforces FR-4 de-duplication.

**Relations:** one-to-many → `OrderItem`, `DeliveryEvent`, `Alert`

---

## 4. OrderItem

An individual line item within an order. Each item is tracked independently for price monitoring.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | Primary key |
| `order_id` | `UUID` | FK → `orders.id`, NOT NULL | Parent order |
| `user_id` | `UUID` | FK → `users.id`, NOT NULL | Denormalized for query convenience |
| `product_name` | `VARCHAR(500)` | NOT NULL | Full product name |
| `variant` | `VARCHAR(255)` | NULLABLE | Size, color, or other variant descriptor |
| `sku` | `VARCHAR(100)` | NULLABLE | Retailer SKU or product ID |
| `product_url` | `TEXT` | NOT NULL | Canonical product page URL (used for scraping) |
| `image_url` | `TEXT` | NULLABLE | Product thumbnail |
| `quantity` | `INTEGER` | NOT NULL, default `1` | Units purchased |
| `paid_price` | `NUMERIC(10,2)` | NOT NULL | Unit price at time of purchase |
| `current_price` | `NUMERIC(10,2)` | NULLABLE | Most recently scraped price |
| `is_monitoring_active` | `BOOLEAN` | default `true` | Whether price monitoring is still running |
| `monitoring_stopped_reason` | `ENUM('return_window_closed','user_disabled','delivered_and_settled','item_unavailable')` | NULLABLE | Reason monitoring was halted |
| `created_at` | `TIMESTAMPTZ` | default `now()` | — |
| `updated_at` | `TIMESTAMPTZ` | auto-update | — |

**Relations:** one-to-many → `PriceSnapshot`, `Alert`

---

## 5. PriceSnapshot

Append-only time-series price observations for a tracked item. Powers price history charts. (FR-6, FR-7)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | Primary key |
| `order_item_id` | `UUID` | FK → `order_items.id`, NOT NULL | Tracked item |
| `scraped_price` | `NUMERIC(10,2)` | NOT NULL | Observed price at snapshot time |
| `original_paid_price` | `NUMERIC(10,2)` | NOT NULL | Captured at snapshot for quick delta calc |
| `price_delta` | `NUMERIC(10,2)` | GENERATED | `original_paid_price - scraped_price` (positive = drop) |
| `currency` | `CHAR(3)` | default `'USD'` | — |
| `is_available` | `BOOLEAN` | default `true` | Whether item was in-stock at scrape time |
| `snapshot_source` | `ENUM('scheduled_job','manual_refresh','extension_capture')` | NOT NULL | What triggered this snapshot |
| `scraped_at` | `TIMESTAMPTZ` | NOT NULL, default `now()` | When the scrape occurred |

**Index:** `(order_item_id, scraped_at DESC)` for efficient time-series queries.

---

## 6. Alert

An actionable notification generated when a monitored condition is met. (FR-7, FR-9, FR-10, FR-11, FR-12, FR-17, FR-18)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | Primary key |
| `user_id` | `UUID` | FK → `users.id`, NOT NULL | Target user |
| `order_id` | `UUID` | FK → `orders.id`, NULLABLE | Associated order |
| `order_item_id` | `UUID` | FK → `order_items.id`, NULLABLE | Associated item (for price alerts) |
| `alert_type` | `ENUM('price_drop','delivery_anomaly','subscription_detected','return_window_expiring','alternative_product')` | NOT NULL | Category of alert |
| `status` | `ENUM('new','viewed','resolved','dismissed','expired')` | NOT NULL, default `'new'` | Lifecycle state |
| `priority` | `ENUM('high','medium','low')` | NOT NULL, default `'medium'` | Determines push notification eligibility |
| `title` | `VARCHAR(255)` | NOT NULL | Short alert headline, e.g. `"Save $25 on your Nike order"` |
| `body` | `TEXT` | NOT NULL | Human-readable explanation |
| `recommended_action` | `ENUM('price_match','return_and_rebuy','no_action')` | NULLABLE | System's top recommendation |
| `estimated_savings` | `NUMERIC(10,2)` | NULLABLE | Expected financial benefit in USD |
| `estimated_effort` | `ENUM('low','medium','high')` | NULLABLE | User effort level for the recommended action |
| `effort_steps_estimate` | `INTEGER` | NULLABLE | Approximate number of steps required |
| `recommendation_rationale` | `TEXT` | NULLABLE | Explanation of why this action was chosen (FR-10) |
| `days_remaining_return` | `INTEGER` | NULLABLE | Days until return window closes at alert creation time |
| `action_deadline` | `DATE` | NULLABLE | Last date the recommended action is viable |
| `alternative_product_url` | `TEXT` | NULLABLE | URL of a suggested alternative item (FR-8) |
| `alternative_product_price` | `NUMERIC(10,2)` | NULLABLE | Price of suggested alternative |
| **Evidence** | | | |
| `evidence` | `JSONB` | NULLABLE | Evidence payload: `{ price_at_purchase, price_now, product_url, order_confirmation_url, screenshot_urls[], retailer_policy_url, price_snapshot_ids[] }` |
| **Generated Messages** | | | |
| `generated_messages` | `JSONB` | NULLABLE | Keyed by tone: `{ polite: { subject, body }, firm: { subject, body }, concise: { subject, body }, generated_by, model_used, prompt_version }` |
| **Metadata** | | | |
| `push_sent_at` | `TIMESTAMPTZ` | NULLABLE | When browser push was dispatched |
| `resolved_at` | `TIMESTAMPTZ` | NULLABLE | When status changed to resolved/dismissed |
| `created_at` | `TIMESTAMPTZ` | default `now()` | — |
| `updated_at` | `TIMESTAMPTZ` | auto-update | — |

**`evidence` JSONB shape:**
```json
{
  "price_at_purchase": 120.00,
  "price_now": 95.00,
  "product_url": "https://...",
  "order_confirmation_url": "https://...",
  "screenshot_urls": ["https://..."],
  "retailer_policy_url": "https://...",
  "price_snapshot_ids": ["uuid1", "uuid2"]
}
```

**`generated_messages` JSONB shape:**
```json
{
  "generated_by": "ai",
  "model_used": "claude-sonnet-4-6",
  "prompt_version": "v1.2",
  "polite":   { "subject": "Price Match Request – Order #12345", "body": "..." },
  "firm":     { "subject": "Price Match Request – Order #12345", "body": "..." },
  "concise":  { "subject": "Price Match Request – Order #12345", "body": "..." }
}
```

---

## 7. DeliveryEvent

Append-only log of delivery status changes for an order. Enables anomaly detection. (FR-13, FR-14)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | Primary key |
| `order_id` | `UUID` | FK → `orders.id`, NOT NULL | Parent order |
| `event_type` | `ENUM('eta_updated','status_changed','tracking_stalled','anomaly_detected','delivered')` | NOT NULL | Type of delivery event |
| `previous_eta` | `DATE` | NULLABLE | ETA before this event |
| `new_eta` | `DATE` | NULLABLE | ETA after this event |
| `eta_slippage_days` | `INTEGER` | GENERATED | `new_eta - previous_eta` (positive = delay) |
| `carrier_status_raw` | `VARCHAR(255)` | NULLABLE | Raw status string from carrier/retailer |
| `is_anomaly` | `BOOLEAN` | default `false` | Whether this event triggered an anomaly alert |
| `scraped_at` | `TIMESTAMPTZ` | NOT NULL, default `now()` | When this status was observed |
| `notes` | `TEXT` | NULLABLE | Internal notes or scraper debug info |

---

## 8. Subscription

A detected recurring purchase or subscription service, inferred from order patterns. (FR-15, FR-16)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | Primary key |
| `user_id` | `UUID` | FK → `users.id`, NOT NULL | Owning user |
| `retailer` | `VARCHAR(50)` | NOT NULL | Retailer where recurrence was detected |
| `product_name` | `VARCHAR(500)` | NOT NULL | Name of the recurring product/service |
| `product_url` | `TEXT` | NULLABLE | Product page URL |
| `detection_method` | `ENUM('order_pattern','explicit_subscription_page')` | NOT NULL | How this subscription was identified |
| `recurrence_interval_days` | `INTEGER` | NULLABLE | Estimated days between charges |
| `estimated_monthly_cost` | `NUMERIC(10,2)` | NULLABLE | Projected monthly spend in USD |
| `last_charged_at` | `DATE` | NULLABLE | Most recent detected charge date |
| `next_expected_charge` | `DATE` | NULLABLE | Estimated next charge date |
| `status` | `ENUM('active','handled','cancelled','monitoring')` | NOT NULL, default `'monitoring'` | User-managed lifecycle state |
| `cancellation_url` | `TEXT` | NULLABLE | Direct link to cancel/pause page |
| `cancellation_steps` | `TEXT` | NULLABLE | Human-readable cancellation instructions |
| `source_order_ids` | `UUID[]` | NULLABLE | Order IDs used to infer this subscription |
| `created_at` | `TIMESTAMPTZ` | default `now()` | — |
| `updated_at` | `TIMESTAMPTZ` | auto-update | — |

---

## 9. OutcomeLog

User-reported result of acting on an alert. Feeds the cumulative savings dashboard. (FR-19, FR-20)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | Primary key |
| `user_id` | `UUID` | FK → `users.id`, NOT NULL | Owning user |
| `alert_id` | `UUID` | FK → `alerts.id`, NULLABLE | Source alert (nullable if manually logged) |
| `order_item_id` | `UUID` | FK → `order_items.id`, NULLABLE | Related item |
| `action_taken` | `ENUM('price_matched','returned_and_rebought','ignored','pending')` | NOT NULL | What the user actually did |
| `recovered_value` | `NUMERIC(10,2)` | NULLABLE | Actual USD savings realized |
| `was_successful` | `BOOLEAN` | NULLABLE | Whether the attempt succeeded |
| `failure_reason` | `TEXT` | NULLABLE | Free-text reason if unsuccessful |
| `notes` | `TEXT` | NULLABLE | Optional user notes |
| `logged_at` | `TIMESTAMPTZ` | NOT NULL, default `now()` | When the outcome was recorded |

---

## 10. Relationships Diagram

```
User (1) ──────────────────────────────── (1) UserPreferences
  │
  ├── (many) Order
  │     ├── (many) OrderItem
  │     │     ├── (many) PriceSnapshot
  │     │     └── (many) Alert
  │     │              [recommendation + evidence + messages inline]
  │     └── (many) DeliveryEvent
  │
  ├── (many) Subscription
  └── (many) OutcomeLog ──── (1, nullable) Alert
```

---

## 11. Key Enums

| Enum | Values |
|---|---|
| `order_status` | `pending`, `shipped`, `in_transit`, `delivered`, `cancelled`, `returned` |
| `alert_type` | `price_drop`, `delivery_anomaly`, `subscription_detected`, `return_window_expiring`, `alternative_product` |
| `alert_status` | `new`, `viewed`, `resolved`, `dismissed`, `expired` |
| `recommended_action` | `price_match`, `return_and_rebuy`, `no_action` |
| `estimated_effort` | `low`, `medium`, `high` |
| `message_tone` | `polite`, `firm`, `concise` |
| `action_taken` | `price_matched`, `returned_and_rebought`, `ignored`, `pending` |
| `subscription_status` | `active`, `handled`, `cancelled`, `monitoring` |
| `delivery_event_type` | `eta_updated`, `status_changed`, `tracking_stalled`, `anomaly_detected`, `delivered` |
| `monitoring_stopped_reason` | `return_window_closed`, `user_disabled`, `delivered_and_settled`, `item_unavailable` |
| `snapshot_source` | `scheduled_job`, `manual_refresh`, `extension_capture` |