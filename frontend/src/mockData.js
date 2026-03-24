export const dashboardStats = [
  {
    title: "Total Saved",
    value: "$1,284.50",
    trend: "+12% from last month",
    positive: true,
  },
  {
    title: "Alerts Triggered",
    value: "24",
    trend: "+4 new today",
    positive: true,
  },
  {
    title: "Active Orders",
    value: "12",
    trend: "-2 compared to Jan",
    positive: false,
  },
];

export const priceHistory = [
  { day: "Mon", price: 118 },
  { day: "Tue", price: 114 },
  { day: "Wed", price: 123 },
  { day: "Thu", price: 109 },
  { day: "Fri", price: 105 },
  { day: "Sat", price: 107 },
  { day: "Sun", price: 102 },
];

export const smartAlerts = [
  {
    id: 1,
    title: "Price Drop Alert",
    desc: "Bose Headphones dropped $40 at Amazon.",
    action: "View Details",
  },
  {
    id: 2,
    title: "New Policy Update",
    desc: "Best Buy extended return window for your order.",
    action: "View Details",
  },
  {
    id: 3,
    title: "Price Increase",
    desc: "The Sony Camera you watched just went up $15.",
    action: "View Details",
  },
];

export const recentPurchases = [
  {
    store: "Amazon",
    product: "Bose QuietComfort Ultra",
    price: "$329.00",
    status: "DELIVERED",
    date: "Feb 18, 2026",
  },
  {
    store: "Best Buy",
    product: "Apple MacBook Air M3",
    price: "$999.00",
    status: "SHIPPED",
    date: "Feb 19, 2026",
  },
  {
    store: "Nike",
    product: "Air Force 1 '07",
    price: "$115.00",
    status: "DELAYED",
    date: "Feb 15, 2026",
  },
];

export const orders = [
  {
    id: "ORD-2024-001",
    store: "Amazon",
    item: "Sony WH-1000XM5 Headphones",
    pricePaid: "$349.99",
    currentPrice: "$329.99",
    savings: "$20.00",
    status: "Tracking",
  },
  {
    id: "ORD-2024-002",
    store: "Best Buy",
    item: "Apple AirPods Pro 2",
    pricePaid: "$249.99",
    currentPrice: "$249.99",
    savings: "$0.00",
    status: "No Change",
  },
  {
    id: "ORD-2024-003",
    store: "Target",
    item: "Dyson V15 Vacuum",
    pricePaid: "$649.99",
    currentPrice: "$599.99",
    savings: "$50.00",
    status: "Alert",
  },
  {
    id: "ORD-2024-004",
    store: "Walmart",
    item: 'Samsung 55" QLED TV',
    pricePaid: "$897.00",
    currentPrice: "$897.00",
    savings: "$0.00",
    status: "Tracking",
  },
  {
    id: "ORD-2024-005",
    store: "Amazon",
    item: "Ninja Air Fryer",
    pricePaid: "$119.99",
    currentPrice: "$99.99",
    savings: "$20.00",
    status: "Alert",
  },
  {
    id: "ORD-2024-006",
    store: "Best Buy",
    item: "iPad Air 5th Gen",
    pricePaid: "$599.99",
    currentPrice: "$579.99",
    savings: "$20.00",
    status: "Alert",
  },
];

export const ordersSummary = {
  totalOrders: 6,
  activeAlerts: 3,
  totalSpent: "$2,866.94",
  potentialSavings: "$110.00",
  quickStats: [
    { label: "Price Drops", value: 3 },
    { label: "No Changes", value: 1 },
    { label: "Tracking", value: 2 },
  ],
};

export const alertsCards = [
  {
    icon: "🎧",
    product: "Sony WH-1000XM5",
    store: "Amazon",
    targetPrice: "$299.99",
    currentPrice: "$329.99",
    active: true,
  },
  {
    icon: "📱",
    product: "iPad Air 5th Gen",
    store: "Best Buy",
    targetPrice: "$549.99",
    currentPrice: "$579.99",
    active: true,
  },
  {
    icon: "🧹",
    product: "Dyson V15 Vacuum",
    store: "Target",
    targetPrice: "$549.99",
    currentPrice: "$599.99",
    active: true,
  },
];

export const savingsStats = [
  {
    title: "Total Saved",
    value: "$1,284.50",
    trend: "+12% from last month",
    positive: true,
  },
  {
    title: "Pending Refunds",
    value: "$320.00",
    trend: "3 pending requests",
    positive: true,
  },
  {
    title: "Average Savings",
    value: "$53.52",
    trend: "Per transaction",
    positive: true,
  },
];

export const savingsByMonth = [
  { month: "Jan", amount: 140 },
  { month: "Feb", amount: 220 },
  { month: "Mar", amount: 185 },
  { month: "Apr", amount: 305 },
  { month: "May", amount: 265 },
  { month: "Jun", amount: 420 },
];

export const savingsHistory = [
  {
    date: "Feb 24, 2026",
    store: "Amazon",
    item: "Sony WH-1000XM5",
    savedAmount: "$20.00",
    type: "Price Drop",
  },
  {
    date: "Feb 22, 2026",
    store: "Best Buy",
    item: "Apple AirPods Pro 2",
    savedAmount: "$50.00",
    type: "Price Match",
  },
  {
    date: "Feb 20, 2026",
    store: "Target",
    item: "Dyson V15 Vacuum",
    savedAmount: "$50.00",
    type: "Price Drop",
  },
  {
    date: "Feb 18, 2026",
    store: "Walmart",
    item: "Ninja Air Fryer",
    savedAmount: "$20.00",
    type: "Price Drop",
  },
];

export const subscriptionPlans = {
  free: {
    title: "Free Plan",
    price: "$0",
    badge: "Current",
    buttonText: "Current Plan",
    features: [
      { text: "Track up to 5 orders", included: true },
      { text: "Basic price alerts", included: true },
      { text: "Email notifications", included: true },
      { text: "Automatic refund requests", included: false },
      { text: "Priority support", included: false },
      { text: "Advanced analytics", included: false },
    ],
  },
  premium: {
    title: "Premium Plan",
    price: "$9.99",
    badge: "Most Popular",
    subtitle: "Cancel anytime",
    buttonText: "Upgrade to Premium",
    features: [
      { text: "Unlimited order tracking", included: true },
      { text: "Automatic refund requests", included: true },
      { text: "Priority customer support", included: true },
      { text: "Advanced savings analytics", included: true },
      { text: "Browser extension access", included: true },
      { text: "Custom price drop thresholds", included: true },
    ],
  },
};

export const billingHistory = [
  {
    date: "Jan 26, 2026",
    plan: "Premium Plan",
    amount: "$9.99",
    status: "Paid",
    action: "Download",
  },
  {
    date: "Dec 26, 2025",
    plan: "Premium Plan",
    amount: "$9.99",
    status: "Paid",
    action: "Download",
  },
  {
    date: "Nov 26, 2025",
    plan: "Premium Plan",
    amount: "$9.99",
    status: "Paid",
    action: "Download",
  },
  {
    date: "Oct 26, 2025",
    plan: "Free Plan",
    amount: "$0.00",
    status: "Free",
    action: "-",
  },
];

export const settingsAccount = {
  firstName: "Alex",
  lastName: "Johnson",
  email: "alex.johnson@email.com",
};