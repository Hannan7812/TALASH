import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchCandidates } from "../services/api";

function Dashboard({ refreshKey }) {
  const [candidates, setCandidates] = useState([]);

  useEffect(() => {
    fetchCandidates().then(setCandidates).catch(() => setCandidates([]));
  }, [refreshKey]);

  const chartData = useMemo(() => {
    const total = candidates.length;
    const withEmail = candidates.filter((c) => c.email).length;
    const withSkills = candidates.filter((c) => c.skills_csv).length;
    return [
      { metric: "Total", value: total },
      { metric: "Email", value: withEmail },
      { metric: "Skills", value: withSkills },
    ];
  }, [candidates]);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-talashTeal">Prototype Dashboard</h2>
      <div className="mt-4 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="metric" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="value" fill="#0C4A6E" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export default Dashboard;
