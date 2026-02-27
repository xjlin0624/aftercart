import enum

class OrderStatus(str, enum.Enum):
    pending    = "pending"
    shipped    = "shipped"
    in_transit = "in_transit"
    delivered  = "delivered"
    cancelled  = "cancelled"
    returned   = "returned"

class AlertType(str, enum.Enum):
    price_drop             = "price_drop"
    delivery_anomaly       = "delivery_anomaly"
    subscription_detected  = "subscription_detected"
    return_window_expiring = "return_window_expiring"
    alternative_product    = "alternative_product"

class AlertStatus(str, enum.Enum):
    new       = "new"
    viewed    = "viewed"
    resolved  = "resolved"
    dismissed = "dismissed"
    expired   = "expired"

class AlertPriority(str, enum.Enum):
    high   = "high"
    medium = "medium"
    low    = "low"

class RecommendedAction(str, enum.Enum):
    price_match      = "price_match"
    return_and_rebuy = "return_and_rebuy"
    no_action        = "no_action"

class EffortLevel(str, enum.Enum):
    low    = "low"
    medium = "medium"
    high   = "high"

class MessageTone(str, enum.Enum):
    polite  = "polite"
    firm    = "firm"
    concise = "concise"

class SnapshotSource(str, enum.Enum):
    scheduled_job     = "scheduled_job"
    manual_refresh    = "manual_refresh"
    extension_capture = "extension_capture"

class MonitoringStoppedReason(str, enum.Enum):
    return_window_closed  = "return_window_closed"
    user_disabled         = "user_disabled"
    delivered_and_settled = "delivered_and_settled"
    item_unavailable      = "item_unavailable"

class DeliveryEventType(str, enum.Enum):
    eta_updated      = "eta_updated"
    status_changed   = "status_changed"
    tracking_stalled = "tracking_stalled"
    anomaly_detected = "anomaly_detected"
    delivered        = "delivered"

class SubscriptionStatus(str, enum.Enum):
    active     = "active"
    handled    = "handled"
    cancelled  = "cancelled"
    monitoring = "monitoring"

class DetectionMethod(str, enum.Enum):
    order_pattern              = "order_pattern"
    explicit_subscription_page = "explicit_subscription_page"

class ActionTaken(str, enum.Enum):
    price_matched         = "price_matched"
    returned_and_rebought = "returned_and_rebought"
    ignored               = "ignored"
    pending               = "pending"
