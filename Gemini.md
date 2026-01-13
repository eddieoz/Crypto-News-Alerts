# Project Analysis: Crypto News Alert System

## Overview
The **Crypto News Alert System** is a real-time monitoring tool designed to aggregate cryptocurrency news and security alerts from various sources and deliver them via push notifications using [ntfy](https://ntfy.sh). It focuses on security breaches, regulatory updates, and protocol changes.

## Architecture
The system follows a standard aggregator pipeline:
1.  **Collection**: Fetching data from external sources (RSS, Nitter).
2.  **Filtering & Processing**: 
    -   **Deduplication**: Using Redis to prevent duplicate alerts (based on similarity).
    -   **Scoring**: Evaluating importance based on keyword matching (English and Portuguese).
3.  **Notification**: Dispatching alerts to specific `ntfy` topics based on category and score.

```mermaid
graph LR
    RSS[RSS Feeds] --> Collector
    Nitter[Nitter/X] --> Collector
    Collector --> Scorer[Priority Scorer]
    Scorer --> Dedup[Deduplicator (Redis)]
    Dedup --> Ntfy[Ntfy Client]
    Ntfy --> Users[End Users]
```

## Key Components

### 1. Collectors (`src/collectors`)
-   **RSSCollector**: Fetches updates from configured RSS feeds.
-   **NitterCollector**: Scrapes tweets from Nitter instances for configured handles.
-   **Missing Component**: The README and configuration mention **Nostr** support, but `NostrCollector` implementation is **missing** from `src/collectors` and is not initialized in `src/scheduler.py`.

### 2. Filters (`src/filters`)
-   **PriorityScorer**: Calculates a score for each item based on keywords defined in `config/filters.yaml`. 
    -   **Positive Scoring**: Boosts priority for critical terms (e.g., "hack", "exploit").
    -   **Negative Scoring**: Penalizes noise (e.g., "IPO", "ETF", "price prediction") to filter out irrelevant content.
    -   Supports multilingual keywords (en, pt-br).
-   **Deduplicator**: Uses Redis to store seen items and check for duplicates within a time window.

### 3. Notifiers (`src/notifiers`)
-   **NtfyClient**: Sends HTTP requests to a configured ntfy server with appropriate tags and priority levels.

### 4. Scheduler (`src/scheduler.py`)
-   Orchestrates the collectors using `asyncio`.
-   Manages the main event loop and task gathering.
-   **Note**: Currently only checks RSS and Nitter; Nostr config is loaded but ignored.

## Configuration structure
The project relies on YAML configuration files in `config/`:
-   `sources.yaml`: Defines RSS feeds, Nitter accounts, and (unused) Nostr accounts.
-   `filters.yaml`: Defines keywords, scores, and category mappings.
-   `ntfy.yaml`: Configures the ntfy server URL, topics, and UI tags.

## Observations & Issues
-   **Missing Feature**: Nostr integration is documented and configured but not implemented.
-   **Stack**: Python 3 (Asyncio), Redis, Docker.
-   **Localization**: Explicit support for Portuguese (Brazil) in configuration.
