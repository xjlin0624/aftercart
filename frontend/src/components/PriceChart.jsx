import React from "react";
import { LineChart, Line, XAxis, YAxis } from "recharts";
import { priceData } from "../mockData";

export default function PriceChart() {
  return (
    <LineChart width={400} height={200} data={priceData}>
      <XAxis dataKey="day" />
      <YAxis />
      <Line dataKey="price" />
    </LineChart>
  );
}