import { useState } from "react";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, ArrowLeft, Envelope, Key } from "@phosphor-icons/react";

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1 = email, 2 = otp + new pw
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const requestOtp = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await apiClient.post("/auth/forgot-password", { email });
      toast.success("Kode OTP dikirim jika email terdaftar");
      setStep(2);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Gagal mengirim OTP");
    } finally { setSubmitting(false); }
  };

  const submitReset = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error("Kata sandi dan konfirmasi tidak sama");
      return;
    }
    if (newPassword.length < 6) {
      toast.error("Kata sandi minimal 6 karakter");
      return;
    }
    setSubmitting(true);
    try {
      await apiClient.post("/auth/reset-password", {
        email, otp: otp.trim(), new_password: newPassword,
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
      await apiClient.post("/auth/forgot-password", { email });
      toast.success("Kode OTP baru dikirim");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Gagal mengirim ulang OTP");
    } finally { setSubmitting(false); }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-[#F9F9F8]">
      {/* Left brand panel */}
      <div className="hidden lg:flex flex-col justify-between p-12 bg-[#0A0A0A] text-white relative overflow-hidden">
        <div className="relative z-10">
          <div className="overline text-zinc-400">Ritme · Reset Kata Sandi</div>
          <h1 className="mt-8 font-display text-6xl font-black tracking-tighter leading-[0.9]">
            Lupa<br/>kata sandi?<br/><span className="text-[#4d78ff]">Tidak masalah.</span>
          </h1>
          <p className="mt-6 text-zinc-400 max-w-md leading-relaxed">
            Masukkan email Anda, kami kirim kode OTP untuk mereset kata sandi dalam hitungan detik.
          </p>
        </div>
        <div className="relative z-10 grid grid-cols-2 gap-6 border-t border-zinc-800 pt-8">
          <div>
            <div className="font-mono-tech text-xs text-zinc-500">01</div>
            <div className="mt-2 font-display text-lg font-semibold flex items-center gap-2">
              <Envelope size={18} /> Masukkan email
            </div>
          </div>
          <div>
            <div className="font-mono-tech text-xs text-zinc-500">02</div>
            <div className="mt-2 font-display text-lg font-semibold flex items-center gap-2">
              <Key size={18} /> Reset dengan OTP
            </div>
          </div>
        </div>
        <div className="absolute -right-32 -bottom-32 w-[500px] h-[500px] rounded-full border border-zinc-800" />
        <div className="absolute -right-20 -bottom-20 w-[300px] h-[300px] rounded-full border border-zinc-800" />
      </div>

      {/* Right form panel */}
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <Link to="/masuk" data-testid="back-to-login-link" className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.15em] text-zinc-500 hover:text-zinc-900">
            <ArrowLeft size={14} weight="bold" /> Kembali ke Masuk
          </Link>

          {step === 1 && (
            <>
              <div className="overline mt-6 mb-3">Langkah 1 dari 2</div>
              <h2 className="font-display text-4xl font-black tracking-tighter">Lupa kata sandi.</h2>
              <p className="mt-3 text-zinc-600 text-sm">
                Masukkan email akun Anda. Kami akan mengirim kode OTP 6-digit.
              </p>
              <form onSubmit={requestOtp} className="mt-8 space-y-5">
                <div>
                  <Label htmlFor="fp-email" className="overline">Email</Label>
                  <Input
                    id="fp-email" type="email" required data-testid="forgot-email-input"
                    className="mt-2 rounded-none border-zinc-900 border h-12"
                    value={email} onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
                <button
                  type="submit" disabled={submitting} data-testid="forgot-submit-btn"
                  className="w-full h-12 bg-[#0A0A0A] text-white font-semibold text-sm uppercase tracking-[0.15em] inline-flex items-center justify-center gap-2 hover:bg-[#002FA7] transition-colors disabled:opacity-50"
                >
                  {submitting ? "Mengirim…" : "Kirim Kode OTP"}
                  <ArrowRight size={16} weight="bold" />
                </button>
              </form>
            </>
          )}

          {step === 2 && (
            <>
              <div className="overline mt-6 mb-3">Langkah 2 dari 2</div>
              <h2 className="font-display text-4xl font-black tracking-tighter">Verifikasi OTP.</h2>
              <p className="mt-3 text-zinc-600 text-sm">
                Kami kirim kode 6-digit ke <strong>{email}</strong>. Berlaku 1 jam.
              </p>
              <form onSubmit={submitReset} className="mt-8 space-y-5">
                <div>
                  <Label htmlFor="fp-otp" className="overline">Kode OTP (6 digit)</Label>
                  <Input
                    id="fp-otp" type="text" required data-testid="reset-otp-input"
                    inputMode="numeric" maxLength={6}
                    className="mt-2 rounded-none border-zinc-900 border h-12 text-center text-2xl font-mono-tech tracking-[0.5em]"
                    value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                  />
                </div>
                <div>
                  <Label htmlFor="fp-newpw" className="overline">Kata Sandi Baru</Label>
                  <Input
                    id="fp-newpw" type="password" required minLength={6} data-testid="reset-newpw-input"
                    className="mt-2 rounded-none border-zinc-900 border h-12"
                    value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor="fp-confirmpw" className="overline">Konfirmasi Kata Sandi</Label>
                  <Input
                    id="fp-confirmpw" type="password" required minLength={6} data-testid="reset-confirmpw-input"
                    className="mt-2 rounded-none border-zinc-900 border h-12"
                    value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                </div>
                <button
                  type="submit" disabled={submitting} data-testid="reset-submit-btn"
                  className="w-full h-12 bg-[#0A0A0A] text-white font-semibold text-sm uppercase tracking-[0.15em] inline-flex items-center justify-center gap-2 hover:bg-[#002FA7] transition-colors disabled:opacity-50"
                >
                  {submitting ? "Memproses…" : "Reset Kata Sandi"}
                  <ArrowRight size={16} weight="bold" />
                </button>
              </form>
              <div className="mt-5 text-sm text-zinc-600 flex items-center justify-between">
                <button data-testid="resend-otp-btn" onClick={resendOtp} disabled={submitting} className="font-semibold text-[#002FA7] underline underline-offset-4 disabled:opacity-50">
                  Kirim ulang kode
                </button>
                <button data-testid="change-email-btn" onClick={() => { setStep(1); setOtp(""); setNewPassword(""); setConfirmPassword(""); }} className="text-zinc-500 hover:text-zinc-900">
                  Ubah email
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
