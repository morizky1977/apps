import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Plus, PencilSimple, Trash, CheckCircle, Circle, ClockCounterClockwise } from "@phosphor-icons/react";

const PRIORITIES = [
  { v: "rendah", label: "Rendah" },
  { v: "sedang", label: "Sedang" },
  { v: "tinggi", label: "Tinggi" },
];
const STATUS = [
  { v: "belum", label: "Belum", icon: Circle, color: "text-zinc-500" },
  { v: "proses", label: "Proses", icon: ClockCounterClockwise, color: "text-amber-600" },
  { v: "selesai", label: "Selesai", icon: CheckCircle, color: "text-emerald-600" },
];

const emptyForm = {
  title: "", category: "kerja", priority: "sedang",
  target_duration: 30, actual_duration: 0, status: "belum",
  notes: "", task_date: new Date().toISOString().slice(0, 10),
};

export default function Tasks() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [filterStatus, setFilterStatus] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get("/tasks");
      setTasks(res.data);
    } catch (e) { toast.error("Gagal memuat tugas"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openNew = () => { setEditing(null); setForm(emptyForm); setDialogOpen(true); };
  const openEdit = (t) => {
    setEditing(t);
    setForm({
      title: t.title, category: t.category, priority: t.priority,
      target_duration: t.target_duration, actual_duration: t.actual_duration,
      status: t.status, notes: t.notes, task_date: t.task_date,
    });
    setDialogOpen(true);
  };

  const save = async (e) => {
    e.preventDefault();
    try {
      if (editing) {
        await apiClient.patch(`/tasks/${editing.id}`, form);
        toast.success("Tugas diperbarui");
      } else {
        await apiClient.post("/tasks", form);
        toast.success("Tugas ditambahkan");
      }
      setDialogOpen(false);
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Gagal menyimpan");
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Hapus tugas ini?")) return;
    try {
      await apiClient.delete(`/tasks/${id}`);
      toast.success("Tugas dihapus");
      load();
    } catch { toast.error("Gagal menghapus"); }
  };

  const toggleStatus = async (t) => {
    const next = t.status === "selesai" ? "belum" : t.status === "belum" ? "proses" : "selesai";
    try {
      await apiClient.patch(`/tasks/${t.id}`, { status: next });
      load();
    } catch { toast.error("Gagal update"); }
  };

  const filtered = tasks.filter((t) => filterStatus === "all" || t.status === filterStatus);

  return (
    <div className="p-6 lg:p-10 max-w-[1400px]">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-zinc-900 pb-6">
        <div>
          <div className="overline">Daftar Tugas Rutin</div>
          <h2 className="mt-2 font-display text-4xl sm:text-5xl font-black tracking-tighter">Kelola Ritme.</h2>
          <p className="mt-2 text-zinc-600 text-sm">Catat kerja rutin harian dengan target durasi dan aktual. Semua rekaman akan dievaluasi mingguan.</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-[180px] rounded-none border-zinc-900" data-testid="filter-status">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Semua Status</SelectItem>
              {STATUS.map((s) => <SelectItem key={s.v} value={s.v}>{s.label}</SelectItem>)}
            </SelectContent>
          </Select>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <button onClick={openNew} data-testid="add-task-btn" className="inline-flex items-center gap-2 px-5 py-3 bg-[#0A0A0A] text-white font-semibold text-xs uppercase tracking-[0.15em] hover:bg-[#002FA7] transition-colors">
                <Plus size={14} weight="bold" /> Tugas Baru
              </button>
            </DialogTrigger>
            <DialogContent className="rounded-none border-zinc-900 max-w-lg" data-testid="task-dialog">
              <DialogHeader>
                <DialogTitle className="font-display text-2xl font-black tracking-tighter">
                  {editing ? "Ubah Tugas" : "Tugas Baru"}
                </DialogTitle>
                <DialogDescription className="text-sm text-zinc-500">
                  Isi detail tugas rutin. Semua field membantu perhitungan performa mingguan.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={save} className="space-y-4">
                <div>
                  <Label className="overline">Judul</Label>
                  <Input required data-testid="task-title-input" className="mt-1 rounded-none border-zinc-900" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="overline">Kategori</Label>
                    <Input data-testid="task-category-input" className="mt-1 rounded-none border-zinc-900" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
                  </div>
                  <div>
                    <Label className="overline">Tanggal</Label>
                    <Input type="date" required data-testid="task-date-input" className="mt-1 rounded-none border-zinc-900" value={form.task_date} onChange={(e) => setForm({ ...form, task_date: e.target.value })} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="overline">Prioritas</Label>
                    <Select value={form.priority} onValueChange={(v) => setForm({ ...form, priority: v })}>
                      <SelectTrigger className="mt-1 rounded-none border-zinc-900" data-testid="task-priority-select"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {PRIORITIES.map((p) => <SelectItem key={p.v} value={p.v}>{p.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="overline">Status</Label>
                    <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                      <SelectTrigger className="mt-1 rounded-none border-zinc-900" data-testid="task-status-select"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {STATUS.map((s) => <SelectItem key={s.v} value={s.v}>{s.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="overline">Target (menit)</Label>
                    <Input type="number" min={0} data-testid="task-target-input" className="mt-1 rounded-none border-zinc-900" value={form.target_duration} onChange={(e) => setForm({ ...form, target_duration: Number(e.target.value) })} />
                  </div>
                  <div>
                    <Label className="overline">Aktual (menit)</Label>
                    <Input type="number" min={0} data-testid="task-actual-input" className="mt-1 rounded-none border-zinc-900" value={form.actual_duration} onChange={(e) => setForm({ ...form, actual_duration: Number(e.target.value) })} />
                  </div>
                </div>
                <div>
                  <Label className="overline">Catatan</Label>
                  <Textarea rows={3} data-testid="task-notes-input" className="mt-1 rounded-none border-zinc-900" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                </div>
                <DialogFooter>
                  <button type="submit" data-testid="task-save-btn" className="px-5 py-3 bg-[#0A0A0A] text-white font-semibold text-xs uppercase tracking-[0.15em] hover:bg-[#002FA7] transition-colors">
                    {editing ? "Simpan Perubahan" : "Tambah"}
                  </button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Task table */}
      <div className="mt-8 bg-white border border-zinc-200">
        <div className="hidden md:grid grid-cols-[1fr_120px_100px_120px_120px_100px] gap-4 px-6 py-3 border-b border-zinc-900 overline">
          <div>Tugas</div>
          <div>Kategori</div>
          <div>Prioritas</div>
          <div>Target/Aktual</div>
          <div>Tanggal</div>
          <div>Aksi</div>
        </div>
        {loading && <div className="p-8 text-sm text-zinc-500">Memuat…</div>}
        {!loading && filtered.length === 0 && (
          <div className="p-10 text-center">
            <p className="text-zinc-500 text-sm">Belum ada tugas. Klik <strong>Tugas Baru</strong> untuk mulai mencatat.</p>
          </div>
        )}
        {filtered.map((t) => {
          const st = STATUS.find((s) => s.v === t.status);
          const Icon = st?.icon || Circle;
          return (
            <div key={t.id} data-testid={`task-row-${t.id}`} className="grid grid-cols-1 md:grid-cols-[1fr_120px_100px_120px_120px_100px] gap-4 px-6 py-4 border-b border-zinc-100 hover:bg-zinc-50 transition-colors items-center">
              <div className="flex items-start gap-3">
                <button data-testid={`task-toggle-${t.id}`} onClick={() => toggleStatus(t)} className={`mt-0.5 ${st?.color}`}>
                  <Icon size={20} weight="duotone" />
                </button>
                <div>
                  <div className={`font-medium ${t.status === "selesai" ? "line-through text-zinc-400" : "text-zinc-900"}`}>{t.title}</div>
                  {t.notes && <div className="text-xs text-zinc-500 mt-1">{t.notes}</div>}
                </div>
              </div>
              <div className="text-sm text-zinc-600 capitalize">{t.category}</div>
              <div>
                <span className={`inline-block px-2 py-0.5 text-[10px] uppercase tracking-[0.15em] font-bold border ${
                  t.priority === "tinggi" ? "border-red-600 text-red-600"
                  : t.priority === "sedang" ? "border-amber-600 text-amber-600"
                  : "border-zinc-400 text-zinc-500"
                }`}>{t.priority}</span>
              </div>
              <div className="text-sm font-mono-tech text-zinc-600">
                {t.actual_duration}m / <span className="text-zinc-400">{t.target_duration}m</span>
              </div>
              <div className="text-sm text-zinc-500">{t.task_date}</div>
              <div className="flex gap-2">
                <button data-testid={`task-edit-${t.id}`} onClick={() => openEdit(t)} className="p-2 hover:bg-zinc-100"><PencilSimple size={16} /></button>
                <button data-testid={`task-delete-${t.id}`} onClick={() => remove(t.id)} className="p-2 hover:bg-red-50 hover:text-red-600"><Trash size={16} /></button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
