function LoginPage({ form, onChange, onSubmit, onGoRegister, errorMessage, successMessage }) {
  return (
    <main className="auth-shell">
      <section className="auth-card">
        <p className="kicker">AI Data Analyst</p>
        <h1>Login</h1>
        <p className="subtitle">Frontend-only login page for now (no backend auth).</p>

        <form onSubmit={onSubmit} className="stack">
          <input
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={(e) => onChange("email", e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={(e) => onChange("password", e.target.value)}
          />
          <button type="submit">Login</button>
        </form>

        <div className="auth-toggle">
          <button type="button" className="ghost-btn" onClick={onGoRegister}>
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
