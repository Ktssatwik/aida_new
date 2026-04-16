import { useState } from "react"

function RegisterPage({
  form,
  onChange,
  onSubmit,
  onGoLogin,
  errorMessage,
  successMessage,
  loading = false,
}) {
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="auth-header">
          <p className="kicker">AI Data Analyst</p>
          <h1>Create account</h1>
          <p className="subtitle">Create your account and verify OTP to continue.</p>
        </div>

        <form onSubmit={onSubmit} className="stack">
          <label className="field-wrap">
            <span>Name</span>
            <input
              type="text"
              placeholder="Your full name"
              value={form.name}
              onChange={(e) => onChange("name", e.target.value)}
              disabled={loading}
            />
          </label>
          <label className="field-wrap">
            <span>Email</span>
            <input
              type="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={(e) => onChange("email", e.target.value)}
              disabled={loading}
            />
          </label>
          <label className="field-wrap">
            <span>Password</span>
            <div className="password-field">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Create password"
                value={form.password}
                onChange={(e) => onChange("password", e.target.value)}
                disabled={loading}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((prev) => !prev)}
                disabled={loading}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </label>
          <label className="field-wrap">
            <span>Confirm password</span>
            <div className="password-field">
              <input
                type={showConfirmPassword ? "text" : "password"}
                placeholder="Repeat password"
                value={form.confirmPassword}
                onChange={(e) => onChange("confirmPassword", e.target.value)}
                disabled={loading}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowConfirmPassword((prev) => !prev)}
                disabled={loading}
              >
                {showConfirmPassword ? "Hide" : "Show"}
              </button>
            </div>
          </label>
          <button type="submit" disabled={loading}>
            {loading ? "Registering..." : "Register"}
          </button>
        </form>

        <div className="auth-toggle">
          <button type="button" className="ghost-btn" onClick={onGoLogin} disabled={loading}>
            Back to login
          </button>
        </div>

        {errorMessage && <div className="alert error">{errorMessage}</div>}
        {successMessage && <div className="alert success">{successMessage}</div>}
      </section>
    </main>
  )
}

export default RegisterPage
