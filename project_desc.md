I want to build a full-stack AI-powered Data Analyst web application that allows users to interact with structured data using natural language and also generates predictive insights using machine learning.

--------------------------------------------------
PROJECT OVERVIEW
--------------------------------------------------
This project is an intelligent data analysis platform where users can upload datasets (CSV files) and ask questions in natural language. The system will convert these queries into SQL, execute them on a database, and return results along with visualizations and AI-generated explanations.

Additionally, the system will include a machine learning layer that can generate predictions, detect trends, and provide deeper insights beyond simple data retrieval.

The goal is to simulate a real-world “AI Data Analyst” that combines:
- SQL for structured data querying
- LLM for natural language understanding and reasoning
- ML for predictive analytics
- React for user interface

--------------------------------------------------
TECH STACK
--------------------------------------------------
Frontend:
- React (with chart libraries like Chart.js or Recharts)

Backend:
- FastAPI (Python)

Database:
- MySQL

Libraries:
- Pandas
- SQLAlchemy
- PyMySQL (MySQL connector)
- scikit-learn
- LangChain (LLM orchestration)

LLM:
- OpenAI API (or similar)

--------------------------------------------------
CORE SYSTEM ARCHITECTURE
--------------------------------------------------
User (React UI)
   ↓
FastAPI Backend
   ↓
LangChain (Natural Language → SQL)
   ↓
MySQL Database (execute query)
   ↓
Optional ML Layer (predictions/analysis)
   ↓
LLM (generate explanation)
   ↓
Frontend (tables + charts + insights)

--------------------------------------------------
FEATURES
--------------------------------------------------

1. CSV Upload & Data Storage
- User uploads CSV file
- Backend reads file using pandas
- Automatically creates a MySQL table dynamically
- Stores structured data in the database using SQLAlchemy

2. Natural Language Query (LLM Layer)
- User inputs queries like:
  “Top 5 customers by revenue”
- Use LangChain to convert query → SQL
- Execute SQL on MySQL
- Return structured results

3. Data Visualization
- Automatically generate charts based on result:
  - Bar chart (categorical data)
  - Line chart (time series)
  - Pie chart (distribution)

4. Explanation Layer (LLM)
- Convert raw query results into human-readable insights
- Example:
  “Revenue increased due to higher customer activity in Q3”

5. Machine Learning Layer (IMPORTANT)
This layer adds predictive and analytical capabilities.

ML Use Cases:

a) Regression (Numerical Prediction)
- Predict future values (e.g., sales forecast)
- Use Linear Regression or similar models
- Example:
  Input: historical sales data
  Output: predicted next value

b) Classification
- Predict categories (e.g., churn prediction)
- Example:
  Identify customers likely to churn

c) Clustering
- Group similar data points (e.g., customer segmentation)

d) Trend Analysis
- Detect patterns in time-series data
- Example:
  “Sales show an increasing trend over time”

ML Workflow:
- Extract relevant columns from query result
- Train lightweight model dynamically (or use simple pre-trained logic)
- Generate prediction or insight
- Send result to LLM for explanation

6. Conversational Queries
- Support follow-up questions:
  “Now show only last year”
- Maintain context using session memory

--------------------------------------------------
IMPORTANT DESIGN PRINCIPLES
--------------------------------------------------
- Modular architecture (separate services for LLM, ML, DB)
- Use SQLAlchemy for database abstraction with MySQL
- Avoid SQL injection (validate or restrict generated SQL)
- Use training-data-only preprocessing for ML
- Keep ML lightweight (no heavy models)
- Use API-based LLM (not local models)

--------------------------------------------------
EXPECTED OUTPUT
--------------------------------------------------
For each query, system should return:
- SQL result (table)
- Visualization (chart)
- Optional ML prediction
- Natural language explanation

--------------------------------------------------
WHAT I NEED FROM YOU
--------------------------------------------------
1. Step-by-step implementation plan
2. Backend code (FastAPI + MySQL + LangChain + ML integration)
3. CSV upload pipeline (CSV → MySQL)
4. Natural language to SQL implementation using LangChain
5. ML module (regression, classification examples)
6. Frontend structure (React components)
7. Integration of all components
8. Best practices and error handling

--------------------------------------------------
IMPLEMENTATION ORDER
--------------------------------------------------
Start with backend development:
1. CSV upload API
2. Store CSV data into MySQL
3. Basic SQL query execution API

Then gradually integrate:
4. LangChain (NL → SQL)
5. ML layer (predictions)
6. Explanation layer (LLM)