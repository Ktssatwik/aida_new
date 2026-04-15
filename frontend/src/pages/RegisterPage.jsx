function RegisterPage({
  form,
  onChange,
  onSubmit,
  onGoLogin,
  errorMessage,
  successMessage,
}) {
  return (
    <main className="auth-shell">
      <section className="auth-card">
        <p className="kicker">AI Data Analyst</p>
        <h1>Register</h1>
        <p className="subtitle">Create your account UI first. Backend auth will come later.</p>

        <form onSubmit={onSubmit} className="stack">
          <input
            type="text"
            placeholder="Name"
            value={form.name}
            onChange={(e) => onChange("name", e.target.value)}
          />
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
          <input
            type="password"
            placeholder="Confirm Password"
            value={form.confirmPassword}
            onChange={(e) => onChange("confirmPassword", e.target.value)}
          />
          <button type="submit">Register</button>
        </form>

        <div className="auth-toggle">
          <button type="button" className="ghost-btn" onClick={onGoLogin}>
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
