import { useEffect, useMemo, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import axios from 'axios'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

function DashboardPage({
  datasets,
  selectedDatasetId,
  setSelectedDatasetId,
  question,
  setQuestion,
  generatedSql,
  queryResult,
  uploadFile,
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
            Upload data, pick a dataset, ask a question, and get SQL + results instantly.
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

  const [loginForm, setLoginForm] = useState({ email: '', password: '' })
  const [registerForm, setRegisterForm] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })

  const [datasets, setDatasets] = useState([])
  const [selectedDatasetId, setSelectedDatasetId] = useState('')
  const [question, setQuestion] = useState('')
  const [generatedSql, setGeneratedSql] = useState('')
  const [queryResult, setQueryResult] = useState(null)
  const [uploadFile, setUploadFile] = useState(null)

  const [loadingDatasets, setLoadingDatasets] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [querying, setQuerying] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  async function fetchDatasets() {
    setLoadingDatasets(true)
    setErrorMessage('')
    try {
      const res = await axios.get(`${API_BASE_URL}/datasets`)
      const items = Array.isArray(res.data) ? res.data : []
      setDatasets(items)
      if (!selectedDatasetId && items.length > 0) {
        setSelectedDatasetId(items[0].dataset_id)
      }
    } catch (error) {
      setErrorMessage(error.response?.data?.detail || 'Failed to load datasets.')
    } finally {
      setLoadingDatasets(false)
    }
  }

  useEffect(() => {
    fetchDatasets()
  }, [])

  function updateLoginForm(key, value) {
    setLoginForm((prev) => ({ ...prev, [key]: value }))
  }

  function updateRegisterForm(key, value) {
    setRegisterForm((prev) => ({ ...prev, [key]: value }))
  }

  function handleLogin(event) {
    event.preventDefault()
    setErrorMessage('')
    setSuccessMessage('')
    if (!loginForm.email.trim() || !loginForm.password.trim()) {
      setErrorMessage('Please enter email and password.')
      return
    }
    setSuccessMessage('Login successful.')
    navigate('/aida')
  }

  function handleRegister(event) {
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
    setSuccessMessage('Registration successful. Please login.')
    setLoginForm({ email: registerForm.email, password: '' })
    navigate('/login')
  }

  function handleLogout() {
    setQuestion('')
    setGeneratedSql('')
    setQueryResult(null)
    setSelectedDatasetId('')
    setSuccessMessage('')
    setErrorMessage('')
    navigate('/login')
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
      const res = await axios.post(`${API_BASE_URL}/datasets/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setSuccessMessage(`Uploaded successfully: ${res.data.table_name}`)
      setUploadFile(null)
      await fetchDatasets()
      if (res.data?.dataset_id) {
        setSelectedDatasetId(res.data.dataset_id)
      }
    } catch (error) {
      setErrorMessage(error.response?.data?.detail || 'CSV upload failed.')
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
      const res = await axios.post(`${API_BASE_URL}/query/nl-to-tables/execute`, payload)
      setGeneratedSql(res.data.generated_sql || '')
      setQueryResult({
        columns: res.data.columns || [],
        rows: res.data.rows || [],
        rowCount: res.data.row_count || 0,
      })
      setSuccessMessage('Query executed successfully.')
    } catch (error) {
      setErrorMessage(error.response?.data?.detail || 'Failed to generate/execute query.')
    } finally {
      setQuerying(false)
    }
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={
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
          />
        }
      />
      <Route
        path="/register"
        element={
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
          />
        }
      />
      <Route
        path="/aida"
        element={
          <DashboardPage
            datasets={datasets}
            selectedDatasetId={selectedDatasetId}
            setSelectedDatasetId={setSelectedDatasetId}
            question={question}
            setQuestion={setQuestion}
            generatedSql={generatedSql}
            queryResult={queryResult}
            uploadFile={uploadFile}
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
        }
      />
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default App
