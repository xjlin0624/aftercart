import React from "react";
import { orders } from "../mockData";

export default function Orders() {
  return (
    <div>
      <h2>Orders</h2>
      {orders.map(o => <div key={o.id}>{o.name}</div>)}
    </div>
  );
}