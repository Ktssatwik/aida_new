function VerifyOtpPage({
  email,
  otp,
  onOtpChange,
  onVerify,
  onResend,
  onGoLogin,
  errorMessage,
  successMessage,
  loadingVerify = false,
  loadingResend = false,
}) {
  return (
    <main className="auth-shell">
      <section className="auth-card">
        <p className="kicker">AI Data Analyst</p>
        <h1>Verify OTP</h1>
        <p className="subtitle">
          Enter the 4-digit code sent to <strong>{email || "your email"}</strong>.
        </p>

        <form onSubmit={onVerify} className="stack">
          <input
            type="text"
            inputMode="numeric"
            maxLength={4}
            placeholder="4-digit OTP"
            value={otp}
            onChange={(e) => onOtpChange(e.target.value)}
            disabled={loadingVerify}
          />
          <button type="submit" disabled={loadingVerify}>
            {loadingVerify ? "Verifying..." : "Verify OTP"}
          </button>
        </form>

        <div className="otp-actions">
          <button type="button" className="ghost-btn" onClick={onResend} disabled={loadingResend}>
            {loadingResend ? "Resending..." : "Resend OTP"}
          </button>
          <button type="button" className="ghost-btn" onClick={onGoLogin} disabled={loadingVerify}>
            Back to login
          </button>
        </div>

        {errorMessage && <div className="alert error">{errorMessage}</div>}
        {successMessage && <div className="alert success">{successMessage}</div>}
      </section>
    </main>
  )
}

export default VerifyOtpPage
