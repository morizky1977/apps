import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "@phosphor-icons/react";

export default function AuthPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login"); // login | register
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(form.email, form.password);
        toast.success("Berhasil masuk");
      } else {
        await register(form.name, form.email, form.password);
        toast.success("Akun berhasil dibuat");
      }
      navigate("/dasbor");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Terjadi kesalahan");
    } finally { setSubmitting(false); }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-[#F9F9F8]">
      {/* Left: brand panel */}
      <div className="hidden lg:flex flex-col justify-between p-12 bg-[#0A0A0A] text-white relative overflow-hidden">
        <div className="relative z-10">
          <div className="overline text-zinc-400">Ritme · Kerja Rutin</div>
          <h1 className="mt-8 font-display text-6xl font-black tracking-tighter leading-[0.9]">
            Catat<br/>ritmemu.<br/><span className="text-[#4d78ff]">Ukur</span> performamu.
          </h1>
          <p className="mt-6 text-zinc-400 max-w-md leading-relaxed">
            Sistem pencatatan kerja rutin harian dengan evaluasi mingguan bertenaga AI. Bangun kebiasaan, ukur kemajuan, dapatkan wawasan yang jujur.
          </p>
        </div>
        <div className="relative z-10 grid grid-cols-3 gap-6 border-t border-zinc-800 pt-8">
          {[
            { k: "01", v: "Catat harian" },
            { k: "02", v: "Analisa mingguan" },
            { k: "03", v: "Wawasan AI" },
          ].map((it) => (
            <div key={it.k}>
              <div className="font-mono-tech text-xs text-zinc-500">{it.k}</div>
              <div className="mt-2 font-display text-lg font-semibold">{it.v}</div>
            </div>
          ))}
        </div>
        {/* geometric decoration */}
        <div className="absolute -right-32 -bottom-32 w-[500px] h-[500px] rounded-full border border-zinc-800" />
        <div className="absolute -right-20 -bottom-20 w-[300px] h-[300px] rounded-full border border-zinc-800" />
      </div>

      {/* Right: form */}
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <div className="overline mb-3">{mode === "login" ? "Masuk" : "Buat Akun"}</div>
          <h2 className="font-display text-4xl font-black tracking-tighter">
            {mode === "login" ? "Selamat datang kembali." : "Mulai lacak ritme Anda."}
          </h2>
          <p className="mt-3 text-zinc-600 text-sm">
            {mode === "login" ? "Masukkan kredensial untuk melanjutkan." : "Hanya butuh 20 detik untuk memulai."}
          </p>

          <form onSubmit={submit} className="mt-8 space-y-5">
            {mode === "register" && (
              <div>
                <Label htmlFor="name" className="overline">Nama</Label>
                <Input
                  id="name" data-testid="auth-name-input"
                  required
                  className="mt-2 rounded-none border-zinc-900 border h-12"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </div>
            )}
            <div>
              <Label htmlFor="email" className="overline">Email</Label>
              <Input
                id="email" type="email" data-testid="auth-email-input" required
                className="mt-2 rounded-none border-zinc-900 border h-12"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="password" className="overline">Kata Sandi</Label>
              <Input
                id="password" type="password" data-testid="auth-password-input" required minLength={6}
                className="mt-2 rounded-none border-zinc-900 border h-12"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </div>

            <button
              type="submit" disabled={submitting} data-testid="auth-submit-btn"
              className="w-full h-12 bg-[#0A0A0A] text-white font-semibold text-sm uppercase tracking-[0.15em] inline-flex items-center justify-center gap-2 hover:bg-[#002FA7] transition-colors disabled:opacity-50"
            >
              {submitting ? "Memproses…" : (mode === "login" ? "Masuk" : "Daftar")}
              <ArrowRight size={16} weight="bold" />
            </button>
          </form>

          <div className="mt-6 text-sm text-zinc-600">
            {mode === "login" ? (
              <>Belum punya akun?{" "}
                <button data-testid="switch-to-register" onClick={() => setMode("register")} className="font-semibold text-[#002FA7] underline underline-offset-4">Daftar</button>
              </>
            ) : (
              <>Sudah punya akun?{" "}
                <button data-testid="switch-to-login" onClick={() => setMode("login")} className="font-semibold text-[#002FA7] underline underline-offset-4">Masuk</button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
