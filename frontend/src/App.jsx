import { useEffect, useMemo, useState } from 'react'
import { Navigate, Route, Routes, useNavigate, useSearchParams } from 'react-router-dom'
import axios from 'axios'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import VerifyOtpPage from './pages/VerifyOtpPage'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const ACCESS_TOKEN_KEY = 'aida_access_token'
const REFRESH_TOKEN_KEY = 'aida_refresh_token'

function getErrorMessage(error, fallbackMessage) {
  const data = error?.response?.data
  return data?.error?.message || data?.detail || fallbackMessage
}

function AuthLoadingScreen() {
  return (
    <main className="auth-shell">
      <section className="auth-card auth-loading-card">
        <p className="kicker">AI Data Analyst</p>
        <h1>Loading session</h1>
        <p className="subtitle">Checking your authentication status...</p>
      </section>
    </main>
  )
}

function ProtectedRoute({ isAuthenticated, authLoading, children }) {
  if (authLoading) return <AuthLoadingScreen />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

function PublicOnlyRoute({ isAuthenticated, authLoading, children }) {
  if (authLoading) return <AuthLoadingScreen />
  if (isAuthenticated) return <Navigate to="/aida" replace />
  return children
}

function DashboardPage({
  userEmail,
  datasets,
  selectedDatasetId,
  setSelectedDatasetId,
  question,
  setQuestion,
  generatedSql,
  queryResult,
  setUploadFile,
  loadingDatasets,
  uploading,
  querying,
  errorMessage,
  successMessage,
  fetchDatasets,
  handleUpload,
  handleAsk,
  handleLogout,
}) {
  const selectedDataset = useMemo(
    () => datasets.find((d) => d.dataset_id === selectedDatasetId) || null,
    [datasets, selectedDatasetId],
  )

  return (
    <main className="app-shell">
      <header className="hero">
        <div>
          <p className="kicker">AI Data Analyst</p>
          <h1>Ask your CSV in plain English</h1>
          <p className="subtitle">
            Signed in as <strong>{userEmail}</strong>. Your datasets are private to your account.
          </p>
        </div>
        <button type="button" onClick={handleLogout}>
          Logout
        </button>
      </header>

      <section className="card">
        <h2>1. Upload CSV</h2>
        <form onSubmit={handleUpload} className="stack">
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
          />
          <button type="submit" disabled={uploading}>
            {uploading ? 'Uploading...' : 'Upload Dataset'}
          </button>
        </form>
      </section>

      <section className="card">
        <h2>2. Choose Dataset</h2>
        <div className="stack">
          <button type="button" onClick={fetchDatasets} disabled={loadingDatasets}>
            {loadingDatasets ? 'Refreshing...' : 'Refresh Datasets'}
          </button>
          <select value={selectedDatasetId} onChange={(e) => setSelectedDatasetId(e.target.value)}>
            <option value="">Select dataset</option>
            {datasets.map((d) => (
              <option key={d.dataset_id} value={d.dataset_id}>
                {d.file_name} | {d.table_name} | {d.row_count} rows
              </option>
            ))}
          </select>
          {selectedDataset && (
            <p className="muted">
              Selected table: <code>{selectedDataset.table_name}</code>
            </p>
          )}
        </div>
      </section>

      <section className="card">
        <h2>3. Ask Question</h2>
        <form onSubmit={handleAsk} className="stack">
          <textarea
            rows={4}
            placeholder="Example: show top 10 rows where target is 1"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button type="submit" disabled={querying}>
            {querying ? 'Generating and Running...' : 'Run NL Query'}
          </button>
        </form>
      </section>

      {errorMessage && <div className="alert error">{errorMessage}</div>}
      {successMessage && <div className="alert success">{successMessage}</div>}

      <section className="card">
        <h2>Generated SQL</h2>
        <pre className="sql-box">{generatedSql || 'SQL will appear here after query execution.'}</pre>
      </section>

      <section className="card">
        <h2>Query Result</h2>
        {!queryResult ? (
          <p className="muted">Result rows will appear here.</p>
        ) : (
          <>
            <p className="muted">Rows returned: {queryResult.rowCount}</p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {queryResult.columns.map((col) => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {queryResult.rows.map((row, rowIndex) => (
                    <tr key={`r-${rowIndex}`}>
                      {row.map((cell, cellIndex) => (
                        <td key={`c-${rowIndex}-${cellIndex}`}>{String(cell)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </main>
  )
}

function App() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [loginForm, setLoginForm] = useState({ email: '', password: '' })
  const [registerForm, setRegisterForm] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [otpForm, setOtpForm] = useState({ email: '', otp: '' })

  const [authLoading, setAuthLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [currentUser, setCurrentUser] = useState(null)

  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(ACCESS_TOKEN_KEY) || '')
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem(REFRESH_TOKEN_KEY) || '')

  const [datasets, setDatasets] = useState([])
  const [selectedDatasetId, setSelectedDatasetId] = useState('')
  const [question, setQuestion] = useState('')
  const [generatedSql, setGeneratedSql] = useState('')
  const [queryResult, setQueryResult] = useState(null)
  const [uploadFile, setUploadFile] = useState(null)

  const [loadingDatasets, setLoadingDatasets] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [querying, setQuerying] = useState(false)

  const [loadingLogin, setLoadingLogin] = useState(false)
  const [loadingRegister, setLoadingRegister] = useState(false)
  const [loadingVerifyOtp, setLoadingVerifyOtp] = useState(false)
  const [loadingResendOtp, setLoadingResendOtp] = useState(false)

  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  function saveTokens(newAccessToken, newRefreshToken) {
    setAccessToken(newAccessToken)
    setRefreshToken(newRefreshToken)
    localStorage.setItem(ACCESS_TOKEN_KEY, newAccessToken)
    localStorage.setItem(REFRESH_TOKEN_KEY, newRefreshToken)
  }

  function clearSession() {
    setAccessToken('')
    setRefreshToken('')
    setIsAuthenticated(false)
    setCurrentUser(null)
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  }

  async function fetchCurrentUser(token) {
    const res = await axios.get(`${API_BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    return res.data
  }

  async function refreshSessionToken(tokenToUse = refreshToken) {
    if (!tokenToUse) {
      throw new Error('Missing refresh token')
    }
    const res = await axios.post(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: tokenToUse,
    })
    saveTokens(res.data.access_token, res.data.refresh_token)
    return res.data.access_token
  }

  async function runWithAuthRetry(requester) {
    try {
      return await requester(accessToken)
    } catch (error) {
      if (error?.response?.status === 401 && refreshToken) {
        const newAccessToken = await refreshSessionToken(refreshToken)
        return await requester(newAccessToken)
      }
      throw error
    }
  }

  function clearDashboardState() {
    setDatasets([])
    setSelectedDatasetId('')
    setQuestion('')
    setGeneratedSql('')
    setQueryResult(null)
    setUploadFile(null)
  }

  useEffect(() => {
    let isActive = true
    const bootstrapAuth = async () => {
      if (!accessToken && !refreshToken) {
        if (!isActive) return
        setAuthLoading(false)
        return
      }

      try {
        let token = accessToken
        if (!token && refreshToken) {
          token = await refreshSessionToken(refreshToken)
        }
        const me = await fetchCurrentUser(token)
        if (!isActive) return
        setCurrentUser(me)
        setIsAuthenticated(true)
      } catch {
        if (!isActive) return
        clearSession()
      } finally {
        if (isActive) setAuthLoading(false)
      }
    }

    bootstrapAuth()
    return () => {
      isActive = false
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (isAuthenticated) {
      fetchDatasets()
    } else {
      clearDashboardState()
    }
  }, [isAuthenticated]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const emailFromQuery = searchParams.get('email') || ''
    if (emailFromQuery) {
      setOtpForm((prev) => ({ ...prev, email: emailFromQuery }))
    }
  }, [searchParams])

  function updateLoginForm(key, value) {
    setLoginForm((prev) => ({ ...prev, [key]: value }))
  }

  function updateRegisterForm(key, value) {
    setRegisterForm((prev) => ({ ...prev, [key]: value }))
  }

  function updateOtp(value) {
    const onlyDigits = value.replace(/\D/g, '').slice(0, 4)
    setOtpForm((prev) => ({ ...prev, otp: onlyDigits }))
  }

  async function fetchDatasets() {
    setLoadingDatasets(true)
    setErrorMessage('')
    try {
      const res = await runWithAuthRetry((token) =>
        axios.get(`${API_BASE_URL}/datasets`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      )
      const items = Array.isArray(res.data) ? res.data : []
      setDatasets(items)
      if (items.length > 0) {
        const found = items.find((d) => d.dataset_id === selectedDatasetId)
        if (!found) {
          setSelectedDatasetId(items[0].dataset_id)
        }
      } else {
        setSelectedDatasetId('')
      }
    } catch (error) {
      if (error?.response?.status === 401) {
        clearSession()
        navigate('/login', { replace: true })
        setErrorMessage('Session expired. Please login again.')
      } else {
        setErrorMessage(getErrorMessage(error, 'Failed to load datasets.'))
      }
    } finally {
      setLoadingDatasets(false)
    }
  }

  async function handleLogin(event) {
    event.preventDefault()
    setErrorMessage('')
    setSuccessMessage('')
    if (!loginForm.email.trim() || !loginForm.password.trim()) {
      setErrorMessage('Please enter email and password.')
      return
    }

    setLoadingLogin(true)
    try {
      const res = await axios.post(`${API_BASE_URL}/auth/login`, {
        email: loginForm.email.trim(),
        password: loginForm.password,
      })
      saveTokens(res.data.access_token, res.data.refresh_token)
      const me = await fetchCurrentUser(res.data.access_token)
      setCurrentUser(me)
      setIsAuthenticated(true)
      setSuccessMessage('Login successful.')
      navigate('/aida', { replace: true })
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Login failed.'))
    } finally {
      setLoadingLogin(false)
    }
  }

  async function handleRegister(event) {
    event.preventDefault()
    setErrorMessage('')
    setSuccessMessage('')

    if (!registerForm.name.trim() || !registerForm.email.trim() || !registerForm.password.trim()) {
      setErrorMessage('Please fill all required fields.')
      return
    }
    if (registerForm.password !== registerForm.confirmPassword) {
      setErrorMessage('Password and confirm password do not match.')
      return
    }

    setLoadingRegister(true)
    try {
      await axios.post(`${API_BASE_URL}/auth/register`, {
        email: registerForm.email.trim(),
        password: registerForm.password,
      })
      setOtpForm({ email: registerForm.email.trim(), otp: '' })
      setSuccessMessage('OTP sent. Please verify your email.')
      navigate(`/verify-otp?email=${encodeURIComponent(registerForm.email.trim())}`, {
        replace: true,
      })
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Registration failed.'))
    } finally {
      setLoadingRegister(false)
    }
  }

  async function handleVerifyOtp(event) {
    event.preventDefault()
    setErrorMessage('')
    setSuccessMessage('')
    if (!otpForm.email.trim()) {
      setErrorMessage('Missing email. Please register again.')
      return
    }
    if (otpForm.otp.length !== 4) {
      setErrorMessage('Please enter a valid 4-digit OTP.')
      return
    }

    setLoadingVerifyOtp(true)
    try {
      await axios.post(`${API_BASE_URL}/auth/verify-otp`, {
        email: otpForm.email.trim(),
        otp: otpForm.otp,
      })
      setSuccessMessage('OTP verified. Please login.')
      setLoginForm((prev) => ({ ...prev, email: otpForm.email.trim(), password: '' }))
      navigate('/login', { replace: true })
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'OTP verification failed.'))
    } finally {
      setLoadingVerifyOtp(false)
    }
  }

  async function handleResendOtp() {
    setErrorMessage('')
    setSuccessMessage('')
    if (!otpForm.email.trim()) {
      setErrorMessage('Missing email. Please register again.')
      return
    }

    setLoadingResendOtp(true)
    try {
      await axios.post(`${API_BASE_URL}/auth/resend-otp`, {
        email: otpForm.email.trim(),
      })
      setSuccessMessage('A new OTP has been sent.')
    } catch (error) {
      setErrorMessage(getErrorMessage(error, 'Failed to resend OTP.'))
    } finally {
      setLoadingResendOtp(false)
    }
  }

  async function handleLogout() {
    setErrorMessage('')
    setSuccessMessage('')
    try {
      if (refreshToken) {
        await axios.post(`${API_BASE_URL}/auth/logout`, { refresh_token: refreshToken })
      }
    } catch {
      // Even if backend logout fails, clear local session for safety.
    } finally {
      clearSession()
      clearDashboardState()
      navigate('/login', { replace: true })
    }
  }

  async function handleUpload(event) {
    event.preventDefault()
    setErrorMessage('')
    setSuccessMessage('')

    if (!uploadFile) {
      setErrorMessage('Please choose a CSV file first.')
      return
    }

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)

      const res = await runWithAuthRetry((token) =>
        axios.post(`${API_BASE_URL}/datasets/upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
            Authorization: `Bearer ${token}`,
          },
        }),
      )

      setSuccessMessage(`Uploaded successfully: ${res.data.table_name}`)
      setUploadFile(null)
      await fetchDatasets()
      if (res.data?.dataset_id) {
        setSelectedDatasetId(res.data.dataset_id)
      }
    } catch (error) {
      if (error?.response?.status === 401) {
        clearSession()
        navigate('/login', { replace: true })
        setErrorMessage('Session expired. Please login again.')
      } else {
        setErrorMessage(getErrorMessage(error, 'CSV upload failed.'))
      }
    } finally {
      setUploading(false)
    }
  }

  async function handleAsk(event) {
    event.preventDefault()
    setErrorMessage('')
    setSuccessMessage('')
    setGeneratedSql('')
    setQueryResult(null)

    if (!selectedDatasetId) {
      setErrorMessage('Please select a dataset.')
      return
    }
    if (!question.trim()) {
      setErrorMessage('Please enter a question.')
      return
    }

    setQuerying(true)
    try {
      const payload = { dataset_id: selectedDatasetId, question: question.trim() }
      const res = await runWithAuthRetry((token) =>
        axios.post(`${API_BASE_URL}/query/nl-to-tables/execute`, payload, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      )

      setGeneratedSql(res.data.generated_sql || '')
      setQueryResult({
        columns: res.data.columns || [],
        rows: res.data.rows || [],
        rowCount: res.data.row_count || 0,
      })
      setSuccessMessage('Query executed successfully.')
    } catch (error) {
      if (error?.response?.status === 401) {
        clearSession()
        navigate('/login', { replace: true })
        setErrorMessage('Session expired. Please login again.')
      } else {
        setErrorMessage(getErrorMessage(error, 'Failed to generate/execute query.'))
      }
    } finally {
      setQuerying(false)
    }
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicOnlyRoute isAuthenticated={isAuthenticated} authLoading={authLoading}>
            <LoginPage
              form={loginForm}
              onChange={updateLoginForm}
              onSubmit={handleLogin}
              onGoRegister={() => {
                setErrorMessage('')
                setSuccessMessage('')
                navigate('/register')
              }}
              errorMessage={errorMessage}
              successMessage={successMessage}
              loading={loadingLogin}
            />
          </PublicOnlyRoute>
        }
      />

      <Route
        path="/register"
        element={
          <PublicOnlyRoute isAuthenticated={isAuthenticated} authLoading={authLoading}>
            <RegisterPage
              form={registerForm}
              onChange={updateRegisterForm}
              onSubmit={handleRegister}
              onGoLogin={() => {
                setErrorMessage('')
                setSuccessMessage('')
                navigate('/login')
              }}
              errorMessage={errorMessage}
              successMessage={successMessage}
              loading={loadingRegister}
            />
          </PublicOnlyRoute>
        }
      />

      <Route
        path="/verify-otp"
        element={
          <PublicOnlyRoute isAuthenticated={isAuthenticated} authLoading={authLoading}>
            <VerifyOtpPage
              email={otpForm.email}
              otp={otpForm.otp}
              onOtpChange={updateOtp}
              onVerify={handleVerifyOtp}
              onResend={handleResendOtp}
              onGoLogin={() => {
                setErrorMessage('')
                setSuccessMessage('')
                navigate('/login')
              }}
              errorMessage={errorMessage}
              successMessage={successMessage}
              loadingVerify={loadingVerifyOtp}
              loadingResend={loadingResendOtp}
            />
          </PublicOnlyRoute>
        }
      />

      <Route
        path="/aida"
        element={
          <ProtectedRoute isAuthenticated={isAuthenticated} authLoading={authLoading}>
            <DashboardPage
              userEmail={currentUser?.email || 'user'}
              datasets={datasets}
              selectedDatasetId={selectedDatasetId}
              setSelectedDatasetId={setSelectedDatasetId}
              question={question}
              setQuestion={setQuestion}
              generatedSql={generatedSql}
              queryResult={queryResult}
              setUploadFile={setUploadFile}
              loadingDatasets={loadingDatasets}
              uploading={uploading}
              querying={querying}
              errorMessage={errorMessage}
              successMessage={successMessage}
              fetchDatasets={fetchDatasets}
              handleUpload={handleUpload}
              handleAsk={handleAsk}
              handleLogout={handleLogout}
            />
          </ProtectedRoute>
        }
      />

      <Route
        path="/"
        element={<Navigate to={isAuthenticated ? '/aida' : '/login'} replace />}
      />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default App
