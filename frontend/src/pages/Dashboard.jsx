import { useEffect, useMemo, useState } from "react";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts";
import { Sparkle, TrendUp, CheckCircle, Timer, Target } from "@phosphor-icons/react";
import { Link } from "react-router-dom";

const dayNames = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];

export default function Dashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get("/evaluations/weekly")
      .then((res) => setSummary(res.data))
      .finally(() => setLoading(false));
  }, []);

  const chartData = useMemo(() => {
    if (!summary) return [];
    const start = new Date(summary.week_start);
    return Array.from({ length: 7 }).map((_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      const iso = d.toISOString().slice(0, 10);
      const dayData = summary.stats.by_day.find((x) => x.date === iso);
      return {
        day: dayNames[i],
        selesai: dayData?.selesai || 0,
        total: dayData?.total || 0,
        aktual: dayData?.aktual || 0,
      };
    });
  }, [summary]);

  if (loading) return <div className="p-10 text-sm text-zinc-500">Memuat dasbor…</div>;
  const s = summary?.stats;

  return (
    <div className="p-6 lg:p-10 max-w-[1400px]">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-zinc-900 pb-6">
        <div>
          <div className="overline">Dasbor · {summary.week_start} – {summary.week_end}</div>
          <h2 className="mt-2 font-display text-4xl sm:text-5xl font-black tracking-tighter">
            Halo, {user?.name?.split(" ")[0]}.
          </h2>
          <p className="mt-2 text-zinc-600 text-sm max-w-lg">
            Ini ringkasan performa kerja rutin minggu ini. Angka jujur menciptakan progres nyata.
          </p>
        </div>
        <Link
          to="/tugas" data-testid="dashboard-add-task-link"
          className="inline-flex items-center gap-2 px-5 py-3 bg-[#0A0A0A] text-white font-semibold text-xs uppercase tracking-[0.15em] hover:bg-[#002FA7] transition-colors"
        >
          Kelola Tugas →
        </Link>
      </div>

      {/* Metric strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-0 mt-8 border border-zinc-900 bg-white">
        <MetricCell
          icon={<CheckCircle size={20} weight="duotone" />}
          label="Tugas Selesai"
          value={`${s.selesai}/${s.total_tasks}`}
          sub={`${s.completion_rate}% penyelesaian`}
          testid="metric-selesai"
        />
        <MetricCell
          icon={<Timer size={20} weight="duotone" />}
          label="Durasi Aktual"
          value={`${s.total_actual_min}m`}
          sub={`Target: ${s.total_target_min}m`}
          testid="metric-durasi"
        />
        <MetricCell
          icon={<Target size={20} weight="duotone" />}
          label="Efisiensi"
          value={`${s.efficiency}%`}
          sub={s.efficiency <= 100 ? "Sesuai/di bawah target" : "Melebihi estimasi"}
          testid="metric-efisiensi"
        />
        <MetricCell
          icon={<TrendUp size={20} weight="duotone" />}
          label="Skor Performa"
          value={`${s.score}`}
          sub="dari 100"
          highlight
          testid="metric-skor"
        />
      </div>

      {/* Charts + AI Insight */}
      <div className="grid lg:grid-cols-3 gap-6 mt-8">
        <div className="lg:col-span-2 bg-white border border-zinc-200 p-6">
          <div className="flex items-baseline justify-between">
            <div>
              <div className="overline">Aktivitas Mingguan</div>
              <h3 className="font-display text-2xl font-bold tracking-tight mt-1">Distribusi Tugas Harian</h3>
            </div>
          </div>
          <div className="mt-6 h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="2 2" stroke="#E5E5E5" vertical={false} />
                <XAxis dataKey="day" tick={{ fill: "#525252", fontSize: 12 }} axisLine={{ stroke: "#0A0A0A" }} tickLine={false} />
                <YAxis tick={{ fill: "#525252", fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: "rgba(0,47,167,0.05)" }} contentStyle={{ border: "1px solid #0A0A0A", borderRadius: 0, fontFamily: "Space Grotesk" }} />
                <Bar dataKey="total" fill="#E5E5E5" name="Total" />
                <Bar dataKey="selesai" fill="#002FA7" name="Selesai" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white border border-zinc-200 p-6">
          <div className="overline">Kategori</div>
          <h3 className="font-display text-2xl font-bold tracking-tight mt-1">Rincian per Kategori</h3>
          <div className="mt-5 space-y-4">
            {s.by_category.length === 0 && <p className="text-sm text-zinc-500">Belum ada data.</p>}
            {s.by_category.map((c) => {
              const pct = c.total > 0 ? Math.round((c.selesai / c.total) * 100) : 0;
              return (
                <div key={c.category} data-testid={`cat-row-${c.category}`}>
                  <div className="flex justify-between text-sm">
                    <span className="font-medium capitalize">{c.category}</span>
                    <span className="font-mono-tech text-zinc-500">{c.selesai}/{c.total} · {pct}%</span>
                  </div>
                  <div className="mt-2 h-1.5 bg-zinc-100">
                    <div className="h-full bg-[#0A0A0A]" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* AI Insight teaser */}
      <div className="mt-8 relative overflow-hidden border border-zinc-900 bg-[#0A0A0A] text-white p-8 lg:p-10">
        <div className="absolute -right-16 -top-16 w-72 h-72 rounded-full border border-zinc-800" />
        <div className="absolute -right-4 -top-4 w-40 h-40 rounded-full border border-zinc-800" />
        <div className="relative max-w-2xl">
          <div className="overline text-zinc-400 flex items-center gap-2"><Sparkle size={14} weight="fill" /> Wawasan AI</div>
          <h3 className="mt-3 font-display text-3xl sm:text-4xl font-black tracking-tighter">
            Butuh analisis mendalam?
          </h3>
          <p className="mt-3 text-zinc-400 text-sm leading-relaxed">
            Dapatkan evaluasi personal & saran konkret dari Claude Sonnet 4.5 berdasarkan pola kerja rutin minggu ini.
          </p>
          <Link
            to="/evaluasi" data-testid="dashboard-ai-cta"
            className="mt-6 inline-flex items-center gap-2 px-5 py-3 bg-white text-[#0A0A0A] font-semibold text-xs uppercase tracking-[0.15em] hover:bg-[#4d78ff] hover:text-white transition-colors"
          >
            Buka Evaluasi Mingguan →
          </Link>
        </div>
      </div>
    </div>
  );
}

function MetricCell({ icon, label, value, sub, highlight, testid }) {
  return (
    <div
      data-testid={testid}
      className={`p-6 border-t border-l border-zinc-900 first:border-l-0 lg:[&:nth-child(-n+4)]:border-t-0 ${highlight ? "bg-[#002FA7] text-white" : ""}`}
    >
      <div className={`flex items-center gap-2 ${highlight ? "text-white/70" : "text-zinc-500"}`}>
        {icon}
        <span className="overline" style={{ color: "inherit" }}>{label}</span>
      </div>
      <div className={`mt-3 font-display text-4xl font-black tracking-tighter ${highlight ? "text-white" : "text-zinc-900"}`}>
        {value}
      </div>
      <div className={`mt-1 text-xs ${highlight ? "text-white/70" : "text-zinc-500"}`}>{sub}</div>
    </div>
  );
}
