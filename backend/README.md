# MarketMaker Backend

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org/)

MarketMaker is a real-time market signal ingestion and anomaly detection engine. It monitors various data sources (stocks, options, alternative data) to identify, score, and alert on unusual market activity.

## Core Features

- **Multi-Source Ingestion**: Pulls data from Yahoo Finance (stocks/options), Polymarket (prediction markets), and Quiver Quantitative (congressional/insider trading).
- **Hybrid Scoring Engine**: Combines unsupervised anomaly detection (Isolation Forest) to answer "Is this event weird?" with a heuristic classifier to answer "What kind of event is this?".
- **Real-time Alerting**: Generates alerts for signals that exceed a configurable anomaly threshold or match high-priority patterns (e.g., insider trades).
- **RESTful API**: Exposes a clean API built with FastAPI to query historical signals and alerts.
- **Persistent Storage**: Uses PostgreSQL to store all signals and alerts for historical analysis and model retraining.
- **Scheduled Jobs**: Employs `apscheduler` for periodic, non-blocking data fetching.

---

## Architecture Overview

The application operates on a scheduled loop, orchestrating several components to create a data processing pipeline.

1.  **Scheduler (`apscheduler`)**: The "heartbeat" of the application. Every `N` seconds, it triggers the main ingestion job.
2.  **Ingestion (`ingest.py`)**: The main workflow coordinator. It calls various service modules to fetch data.
3.  **Service Adapters (`services/`)**: Each service is a wrapper around an external API or library (e.g., `yfinance`, `quiverquant`). This isolates external dependencies.
4.  **Normalization (`normalize.py`)**: Raw data from any source is transformed into a standard `NormalizedSignal` object. This creates a canonical data model for the system.
5.  **Feature Extraction (`features.py`)**: The `NormalizedSignal` is processed to extract numerical features (e.g., Z-scores, returns, sentiment ratios).
6.  **Scoring Engine (`scoring.py`)**:
    -   **Anomaly Score**: An `IsolationForest` model scores the feature vector to determine how anomalous it is compared to historical data (0.0 = normal, 1.0 = highly anomalous).
    -   **Classification**: A `heuristic_label` function applies expert rules to categorize the signal (e.g., `price_volume_spike`, `bullish_options_skew`).
7.  **Persistence (`db.py`, `models.py`)**: The final, scored `Signal` is saved to the PostgreSQL database. If it meets alerting criteria, an `Alert` is also created.

---

## Getting Started

You can run the application using Docker (recommended for production) or locally in a Python virtual environment.

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (optional, but recommended for DB)
- Access to a PostgreSQL database

### 1. Configuration

The application is configured using environment variables.

```bash
# Create a .env file from the example
cp .env.example .env
```

Open `.env` and customize the variables, especially `QUIVER_API_TOKEN` if you have one.

### 2. Local Development Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Ensure you have a running PostgreSQL instance.
#    Update DATABASE_URL in .env to point to it.

# 4. Start the application
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. The `--reload` flag will automatically restart the server when you make code changes.

### 3. Docker Setup

If you have a `docker-compose.yml` (not included in this repo but standard for this stack):

```bash
docker-compose up --build -d
```

---

## API Endpoints

Once running, the API documentation is automatically generated and available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

Key endpoints include:

- `GET /health`: Health check endpoint.
- `GET /signals/`: Query historical signals with filtering and pagination.
- `GET /alerts/`: Query generated alerts.
- `POST /admin/refit`: Manually trigger the retraining of the anomaly detection model from the latest data in the database.

---

## Configuration Variables

| Variable                | Description                                                                                             | Default Value                                                 |
| ----------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `DATABASE_URL`          | The full connection string for the PostgreSQL database.                                                 | `postgresql+psycopg://marketmaker...`                         |
| `STOCK_WATCHLIST`       | A comma-separated string of stock tickers to monitor (e.g., "AAPL,TSLA,NVDA").                          | `"AAPL,GOOGL,AMD,AMZN,TSLA"`                                  |
| `POLYMARKET_QUERY`      | A keyword used to filter for relevant prediction markets on Polymarket.                                 | `"election"`                                                  |
| `QUIVER_API_TOKEN`      | **Optional**. Your API token for Quiver Quantitative. If left blank, this data source will be disabled. | `None`                                                        |
| `POLL_INTERVAL_SECONDS` | The time in seconds between each data fetching cycle.                                                   | `120`                                                         |
| `ANOMALY_THRESHOLD`     | The score (0.0-1.0) above which a signal is considered for an alert.                                    | `0.75`                                                        |
| `SEC_USER_AGENT`        | A user agent string required by the SEC EDGAR API, formatted as `"AppName email@example.com"`.          | `"MarketMaker ..."`                                           |

---

## Project Internals & Concepts

#### Adapter Pattern

Services like `QuiverAdapter` are designed to isolate third-party dependencies. If we ever need to switch data providers, we only need to modify the adapter; the rest of the application's core logic remains untouched. This also allows for "soft dependencies" like `quiverquant`, where the app can run even if the optional library isn't installed.

#### Hybrid Scoring

We use a two-pronged approach to evaluate signals:
1.  **Unsupervised Anomaly Detection**: The `IsoForestScorer` is trained on the mathematical distribution of historical features. It excels at finding "unknown unknowns"—patterns that are statistically unusual but don't fit a predefined rule.
2.  **Heuristic Classification**: The `heuristic_label` function uses a set of "if-then" rules based on financial domain knowledge (e.g., a high Call/Put ratio is bullish). This is great for identifying "known knowns" with high confidence.

#### Model Bootstrapping

On startup, the application runs `refit_models_from_db` to train the `IsolationForest` model on the most recent signals in the database. This ensures the model is always fresh and ready to score new data without requiring a manual training step after a restart.
