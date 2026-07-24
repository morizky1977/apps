import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";
import { Sparkle, ArrowLeft, ArrowRight } from "@phosphor-icons/react";

function fmtDate(d) { return d.toISOString().slice(0, 10); }
function mondayOf(d) {
  const day = d.getDay() || 7;
  const m = new Date(d);
  m.setDate(d.getDate() - (day - 1));
  return m;
}

export default function Evaluation() {
  const [weekAnchor, setWeekAnchor] = useState(fmtDate(mondayOf(new Date())));
  const [summary, setSummary] = useState(null);
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const shiftWeek = (delta) => {
    const d = new Date(weekAnchor);
    d.setDate(d.getDate() + delta * 7);
    setWeekAnchor(fmtDate(d));
  };

  useEffect(() => {
    setLoading(true);
    setInsight(null);
    apiClient.get(`/evaluations/weekly?week=${weekAnchor}`)
      .then((res) => setSummary(res.data))
      .finally(() => setLoading(false));
  }, [weekAnchor]);

  const generateInsight = async () => {
    setGenerating(true);
    try {
      const res = await apiClient.post("/evaluations/weekly/insight", { week: weekAnchor });
      setInsight(res.data.insight);
      toast.success("Wawasan AI berhasil dibuat");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gagal membuat wawasan");
    } finally { setGenerating(false); }
  };

  if (loading) return <div className="p-10 text-sm text-zinc-500">Memuat evaluasi…</div>;
  const s = summary.stats;
  const scoreColor = s.score >= 80 ? "#10B981" : s.score >= 50 ? "#F59E0B" : "#E53935";

  return (
    <div className="p-6 lg:p-10 max-w-[1400px]">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-zinc-900 pb-6">
        <div>
          <div className="overline">Evaluasi Mingguan</div>
          <h2 className="mt-2 font-display text-4xl sm:text-5xl font-black tracking-tighter">Skor Ritme.</h2>
          <p className="mt-2 text-zinc-600 text-sm">Ukur performa mingguan dan dapatkan wawasan AI untuk perbaikan.</p>
        </div>
        <div className="flex items-center gap-2 border border-zinc-900">
          <button data-testid="prev-week-btn" onClick={() => shiftWeek(-1)} className="p-3 hover:bg-zinc-900 hover:text-white transition-colors"><ArrowLeft size={16} /></button>
          <div className="px-4 py-2 text-sm font-mono-tech" data-testid="week-range-label">
            {summary.week_start} → {summary.week_end}
          </div>
          <button data-testid="next-week-btn" onClick={() => shiftWeek(1)} className="p-3 hover:bg-zinc-900 hover:text-white transition-colors"><ArrowRight size={16} /></button>
        </div>
      </div>

      {/* Big score */}
      <div className="mt-8 grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 bg-white border border-zinc-900 p-8 relative overflow-hidden">
          <div className="overline">Skor Performa</div>
          <div className="mt-2 flex items-baseline gap-2">
            <div className="font-display text-7xl font-black tracking-tighter" style={{ color: scoreColor }} data-testid="performance-score">
              {s.score}
            </div>
            <div className="text-zinc-400 font-mono-tech">/100</div>
          </div>
          <div className="mt-4 h-2 bg-zinc-100">
            <div className="h-full" style={{ width: `${Math.min(s.score, 100)}%`, backgroundColor: scoreColor }} />
          </div>
          <p className="mt-4 text-sm text-zinc-600">
            {s.score >= 80 ? "Performa sangat baik minggu ini." : s.score >= 50 ? "Performa cukup, ada ruang perbaikan." : "Performa perlu ditingkatkan."}
          </p>
        </div>

        <div className="lg:col-span-2 grid grid-cols-2 sm:grid-cols-4 border border-zinc-200 bg-white">
          <Cell label="Total Tugas" value={s.total_tasks} testid="eval-total" />
          <Cell label="Selesai" value={`${s.selesai} (${s.completion_rate}%)`} testid="eval-selesai" />
          <Cell label="Total Aktual" value={`${s.total_actual_min}m`} testid="eval-aktual" />
          <Cell label="Efisiensi" value={`${s.efficiency}%`} testid="eval-efisiensi" />
        </div>
      </div>

      {/* AI Insight card */}
      <div className="mt-8 border border-zinc-900 bg-white">
        <div className="p-6 lg:p-8 bg-[#0A0A0A] text-white flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="overline text-zinc-400 flex items-center gap-2"><Sparkle size={14} weight="fill" /> Wawasan AI · Claude Sonnet 4.5</div>
            <h3 className="mt-1 font-display text-2xl sm:text-3xl font-bold tracking-tight">Evaluasi Personal Minggu Ini</h3>
          </div>
          <button
            data-testid="generate-insight-btn"
            onClick={generateInsight}
            disabled={generating || s.total_tasks === 0}
            className="px-5 py-3 bg-white text-[#0A0A0A] font-semibold text-xs uppercase tracking-[0.15em] hover:bg-[#4d78ff] hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {generating ? "Menganalisa…" : insight ? "Buat Ulang" : "Hasilkan Wawasan"}
          </button>
        </div>
        <div className="p-6 lg:p-8" data-testid="insight-content">
          {s.total_tasks === 0 && (
            <p className="text-zinc-500 text-sm">Belum ada tugas minggu ini. Tambahkan beberapa tugas terlebih dahulu untuk mendapatkan wawasan.</p>
          )}
          {s.total_tasks > 0 && !insight && !generating && (
            <p className="text-zinc-500 text-sm">Klik <strong>Hasilkan Wawasan</strong> untuk menerima analisa personal dari AI.</p>
          )}
          {generating && (
            <div className="space-y-3">
              <div className="h-3 bg-zinc-100 animate-pulse" />
              <div className="h-3 bg-zinc-100 animate-pulse w-4/5" />
              <div className="h-3 bg-zinc-100 animate-pulse w-3/5" />
            </div>
          )}
          {insight && <MarkdownLite text={insight} />}
        </div>
      </div>
    </div>
  );
}

function Cell({ label, value, testid }) {
  return (
    <div className="p-6 border-t border-l border-zinc-200 first:border-l-0" data-testid={testid}>
      <div className="overline">{label}</div>
      <div className="mt-2 font-display text-3xl font-black tracking-tighter">{value}</div>
    </div>
  );
}

// Very small markdown renderer: ## headings, - bullets, paragraphs, **bold**
function MarkdownLite({ text }) {
  const lines = text.split("\n");
  const blocks = [];
  let currentList = null;
  const flushList = () => { if (currentList) { blocks.push({ type: "ul", items: currentList }); currentList = null; } };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) { flushList(); continue; }
    if (line.startsWith("## ")) { flushList(); blocks.push({ type: "h", text: line.slice(3) }); continue; }
    if (line.startsWith("- ") || line.startsWith("* ")) {
      if (!currentList) currentList = [];
      currentList.push(line.slice(2));
      continue;
    }
    flushList();
    blocks.push({ type: "p", text: line });
  }
  flushList();

  const renderInline = (t) => {
    const parts = t.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((p, i) => p.startsWith("**") ? <strong key={i}>{p.slice(2, -2)}</strong> : <span key={i}>{p}</span>);
  };

  return (
    <div className="prose prose-zinc max-w-none">
      {blocks.map((b, i) => {
        if (b.type === "h") return <h4 key={i} className="font-display text-lg font-bold tracking-tight mt-6 first:mt-0 border-l-2 border-[#002FA7] pl-3">{b.text}</h4>;
        if (b.type === "ul") return (
          <ul key={i} className="mt-3 space-y-2">
            {b.items.map((it, j) => (
              <li key={j} className="flex gap-3 text-sm text-zinc-700 leading-relaxed">
                <span className="text-[#002FA7] font-bold mt-1">▸</span>
                <span>{renderInline(it)}</span>
              </li>
            ))}
          </ul>
        );
        return <p key={i} className="text-sm text-zinc-700 leading-relaxed mt-3">{renderInline(b.text)}</p>;
      })}
    </div>
  );
}
