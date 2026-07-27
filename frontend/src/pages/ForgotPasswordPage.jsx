import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, ArrowLeft, Envelope, Key, ShieldCheck } from "@phosphor-icons/react";

const METHODS = [
  { id: "email", label: "OTP via Email", icon: Envelope, testid: "method-tab-email" },
  { id: "security", label: "Pertanyaan Keamanan", icon: ShieldCheck, testid: "method-tab-security" },
];

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [method, setMethod] = useState("email");
  const [step, setStep] = useState(1); // for email flow: 1=email, 2=otp+pw
  const [securityQuestion, setSecurityQuestion] = useState("");
  const [form, setForm] = useState({
    email: "", otp: "",
    newPassword: "", confirmPassword: "",
    security_answer: "",
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    apiClient.get("/auth/security-question")
      .then((res) => setSecurityQuestion(res.data.question))
      .catch(() => {});
  }, []);

  const switchMethod = (m) => {
    setMethod(m);
    setStep(1);
    setForm((f) => ({ ...f, otp: "", newPassword: "", confirmPassword: "", security_answer: "" }));
  };

  const validateNewPassword = () => {
    if (form.newPassword !== form.confirmPassword) {
      toast.error("Kata sandi dan konfirmasi tidak sama");
      return false;
    }
    if (form.newPassword.length < 6) {
      toast.error("Kata sandi minimal 6 karakter");
      return false;
    }
    return true;
  };

  const requestOtp = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await apiClient.post("/auth/forgot-password", { email: form.email });
      toast.success("Kode OTP dikirim jika email terdaftar");
      setStep(2);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Gagal mengirim OTP");
    } finally { setSubmitting(false); }
  };

  const submitResetOtp = async (e) => {
    e.preventDefault();
    if (!validateNewPassword()) return;
    setSubmitting(true);
    try {
      await apiClient.post("/auth/reset-password", {
        email: form.email, otp: form.otp.trim(), new_password: form.newPassword,
      });
      toast.success("Kata sandi berhasil direset. Silakan masuk.");
      navigate("/masuk");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Gagal mereset kata sandi");
    } finally { setSubmitting(false); }
  };

  const submitResetSecurity = async (e) => {
    e.preventDefault();
    if (!validateNewPassword()) return;
    setSubmitting(true);
    try {
      await apiClient.post("/auth/reset-password-security", {
        email: form.email,
        security_answer: form.security_answer,
        new_password: form.newPassword,
      });
      toast.success("Kata sandi berhasil direset. Silakan masuk.");
      navigate("/masuk");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Gagal mereset kata sandi");
    } finally { setSubmitting(false); }
  };

  const resendOtp = async () => {
    setSubmitting(true);
    try {
      await apiClient.post("/auth/forgot-password", { email: form.email });
      toast.success("Kode OTP baru dikirim");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Gagal mengirim ulang OTP");
    } finally { setSubmitting(false); }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-[#F9F9F8]">
      {/* Left panel */}
      <div className="hidden lg:flex flex-col justify-between p-12 bg-[#0A0A0A] text-white relative overflow-hidden">
        <div className="relative z-10">
          <div className="overline text-zinc-400">Ritme · Reset Kata Sandi</div>
          <h1 className="mt-8 font-display text-6xl font-black tracking-tighter leading-[0.9]">
            Pilih<br/>metodemu.<br/><span className="text-[#4d78ff]">Kembali</span> masuk.
          </h1>
          <p className="mt-6 text-zinc-400 max-w-md leading-relaxed">
            Reset kata sandi via email OTP atau lewat pertanyaan keamanan yang Anda atur saat mendaftar.
          </p>
        </div>
        <div className="relative z-10 grid grid-cols-2 gap-6 border-t border-zinc-800 pt-8">
          <div>
            <div className="font-mono-tech text-xs text-zinc-500">Metode 1</div>
            <div className="mt-2 font-display text-lg font-semibold flex items-center gap-2">
              <Envelope size={18} /> Email OTP
            </div>
          </div>
          <div>
            <div className="font-mono-tech text-xs text-zinc-500">Metode 2</div>
            <div className="mt-2 font-display text-lg font-semibold flex items-center gap-2">
              <ShieldCheck size={18} /> Pertanyaan Keamanan
            </div>
          </div>
        </div>
        <div className="absolute -right-32 -bottom-32 w-[500px] h-[500px] rounded-full border border-zinc-800" />
        <div className="absolute -right-20 -bottom-20 w-[300px] h-[300px] rounded-full border border-zinc-800" />
      </div>

      {/* Right form */}
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <Link to="/masuk" data-testid="back-to-login-link" className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.15em] text-zinc-500 hover:text-zinc-900">
            <ArrowLeft size={14} weight="bold" /> Kembali ke Masuk
          </Link>

          <div className="overline mt-6 mb-3">Pilih Metode Reset</div>

          {/* Method tabs */}
          <div className="grid grid-cols-2 border border-zinc-900">
            {METHODS.map((m) => {
              const active = method === m.id;
              const Icon = m.icon;
              return (
                <button
                  key={m.id}
                  data-testid={m.testid}
                  onClick={() => switchMethod(m.id)}
                  className={`flex items-center justify-center gap-2 px-3 py-3 text-xs font-semibold uppercase tracking-[0.15em] transition-colors ${
                    active ? "bg-[#0A0A0A] text-white" : "bg-white text-zinc-600 hover:text-zinc-900"
                  }`}
                >
                  <Icon size={14} weight="bold" /> {m.label}
                </button>
              );
            })}
          </div>

          {/* Email OTP flow */}
          {method === "email" && step === 1 && (
            <div className="mt-6">
              <h2 className="font-display text-3xl font-black tracking-tighter">Kirim kode ke email.</h2>
              <p className="mt-3 text-zinc-600 text-sm">Kami akan mengirim OTP 6-digit yang berlaku 1 jam.</p>
              <form onSubmit={requestOtp} className="mt-6 space-y-5">
                <div>
                  <Label className="overline">Email</Label>
                  <Input
                    type="email" required data-testid="forgot-email-input"
                    className="mt-2 rounded-none border-zinc-900 border h-12"
                    value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                  />
                </div>
                <button
                  type="submit" disabled={submitting} data-testid="forgot-submit-btn"
                  className="w-full h-12 bg-[#0A0A0A] text-white font-semibold text-sm uppercase tracking-[0.15em] inline-flex items-center justify-center gap-2 hover:bg-[#002FA7] transition-colors disabled:opacity-50"
                >
                  {submitting ? "Mengirim…" : "Kirim Kode OTP"} <ArrowRight size={16} weight="bold" />
                </button>
              </form>
            </div>
          )}

          {method === "email" && step === 2 && (
            <div className="mt-6">
              <h2 className="font-display text-3xl font-black tracking-tighter">Verifikasi OTP.</h2>
              <p className="mt-3 text-zinc-600 text-sm">
                Kode 6-digit dikirim ke <strong>{form.email}</strong>.
              </p>
              <form onSubmit={submitResetOtp} className="mt-6 space-y-5">
                <div>
                  <Label className="overline">Kode OTP</Label>
                  <Input
                    type="text" required data-testid="reset-otp-input"
                    inputMode="numeric" maxLength={6}
                    className="mt-2 rounded-none border-zinc-900 border h-12 text-center text-2xl font-mono-tech tracking-[0.5em]"
                    value={form.otp} onChange={(e) => setForm({ ...form, otp: e.target.value.replace(/\D/g, "") })}
                  />
                </div>
                <PasswordFields form={form} setForm={setForm} />
                <button
                  type="submit" disabled={submitting} data-testid="reset-submit-btn"
                  className="w-full h-12 bg-[#0A0A0A] text-white font-semibold text-sm uppercase tracking-[0.15em] inline-flex items-center justify-center gap-2 hover:bg-[#002FA7] transition-colors disabled:opacity-50"
                >
                  {submitting ? "Memproses…" : "Reset Kata Sandi"} <ArrowRight size={16} weight="bold" />
                </button>
              </form>
              <div className="mt-5 text-sm text-zinc-600 flex items-center justify-between">
                <button data-testid="resend-otp-btn" onClick={resendOtp} disabled={submitting} className="font-semibold text-[#002FA7] underline underline-offset-4 disabled:opacity-50">
                  Kirim ulang kode
                </button>
                <button data-testid="change-email-btn" onClick={() => setStep(1)} className="text-zinc-500 hover:text-zinc-900">
                  Ubah email
                </button>
              </div>
            </div>
          )}

          {/* Security question flow */}
          {method === "security" && (
            <div className="mt-6">
              <h2 className="font-display text-3xl font-black tracking-tighter">Jawab pertanyaan keamanan.</h2>
              <p className="mt-3 text-zinc-600 text-sm">Ideal jika Anda tidak dapat mengakses email.</p>
              <form onSubmit={submitResetSecurity} className="mt-6 space-y-5">
                <div>
                  <Label className="overline">Email</Label>
                  <Input
                    type="email" required data-testid="security-email-input"
                    className="mt-2 rounded-none border-zinc-900 border h-12"
                    value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                  />
                </div>
                <div className="border border-zinc-200 bg-zinc-50 p-4">
                  <Label className="overline">Pertanyaan</Label>
                  <p className="mt-2 text-sm text-zinc-700 leading-snug" data-testid="security-question-text">
                    {securityQuestion || "Memuat pertanyaan…"}
                  </p>
                  <Input
                    type="text" required data-testid="security-answer-input"
                    className="mt-3 rounded-none border-zinc-900 border h-12 bg-white"
                    placeholder="Jawaban Anda"
                    value={form.security_answer}
                    onChange={(e) => setForm({ ...form, security_answer: e.target.value })}
                  />
                </div>
                <PasswordFields form={form} setForm={setForm} />
                <button
                  type="submit" disabled={submitting} data-testid="security-reset-submit-btn"
                  className="w-full h-12 bg-[#0A0A0A] text-white font-semibold text-sm uppercase tracking-[0.15em] inline-flex items-center justify-center gap-2 hover:bg-[#002FA7] transition-colors disabled:opacity-50"
                >
                  {submitting ? "Memproses…" : "Reset Kata Sandi"} <ArrowRight size={16} weight="bold" />
                </button>
              </form>
              <p className="mt-4 text-xs text-zinc-500">
                <strong>Catatan:</strong> Metode ini hanya berlaku jika Anda telah menyetel jawaban pertanyaan keamanan saat mendaftar atau di pengaturan akun.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PasswordFields({ form, setForm }) {
  return (
    <>
      <div>
        <Label className="overline">Kata Sandi Baru</Label>
        <Input
          type="password" required minLength={6} data-testid="reset-newpw-input"
          className="mt-2 rounded-none border-zinc-900 border h-12"
          value={form.newPassword} onChange={(e) => setForm({ ...form, newPassword: e.target.value })}
        />
      </div>
      <div>
        <Label className="overline">Konfirmasi Kata Sandi</Label>
        <Input
          type="password" required minLength={6} data-testid="reset-confirmpw-input"
          className="mt-2 rounded-none border-zinc-900 border h-12"
          value={form.confirmPassword} onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
        />
      </div>
    </>
  );
}
