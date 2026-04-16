import { useState } from "react"

function LoginPage({
  form,
  onChange,
  onSubmit,
  onGoRegister,
  errorMessage,
  successMessage,
  loading = false,
}) {
  const [showPassword, setShowPassword] = useState(false)

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="auth-header">
          <p className="kicker">AI Data Analyst</p>
          <h1>Welcome back</h1>
          <p className="subtitle">Access your private datasets and ask questions securely.</p>
        </div>

        <form onSubmit={onSubmit} className="stack">
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
                placeholder="Enter password"
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
          <button type="submit" disabled={loading}>
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>

        <div className="auth-toggle">
          <button type="button" className="ghost-btn" onClick={onGoRegister} disabled={loading}>
            Create new account
          </button>
        </div>

        {errorMessage && <div className="alert error">{errorMessage}</div>}
        {successMessage && <div className="alert success">{successMessage}</div>}
      </section>
    </main>
  )
}

export default LoginPage
