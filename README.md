# Options Tracker

A stock options research and paper-trading application that helps users find, score, and track options opportunities based on their selected risk level.

This app does **not** promise guaranteed profits or “sure bets.” Options trading is risky, and all signals should be treated as research ideas, not financial advice.

## Overview

Options Tracker allows users to:

- Create a stock watchlist
- Fetch stock price and options-chain data
- Pull relevant stock news
- Analyze options opportunities
- Score trades based on risk, liquidity, volatility, and news sentiment
- Choose a risk level: low, medium, or high
- Backtest strategies
- Paper trade before considering live execution
- Track open and closed trades

## Risk Levels

The app supports three risk profiles:

### Low Risk

Focuses on defined-risk or asset-backed strategies such as:

- Covered calls
- Cash-secured puts
- Conservative spreads
- Higher-liquidity contracts
- Lower max loss per trade

### Medium Risk

Allows more directional exposure and moderate risk, such as:

- Debit spreads
- Credit spreads
- Earnings-aware trades
- Moderate expiration windows
- Medium position sizing

### High Risk

Allows more aggressive trades, such as:

- Long calls
- Long puts
- Shorter expiration contracts
- Higher volatility opportunities
- Larger potential reward with higher probability of loss

High-risk mode should still avoid unlimited-risk strategies like naked short calls.

## Core Features

### Watchlist

Users can add stocks they want the app to monitor.

### Market Data

The app can source data from free or low-cost APIs such as:

- Alpha Vantage
- yfinance
- Finnhub
- MarketAux
- Alpaca
- Tradier Sandbox

### News Analysis

The app collects relevant financial news for watchlist symbols and can use sentiment scoring to determine whether the news appears bullish, bearish, or neutral.

### Options Analysis

The app analyzes options using:

- Bid/ask spread
- Volume
- Open interest
- Implied volatility
- Historical volatility
- Greeks
- Expiration date
- Strike price
- Max profit
- Max loss
- Breakeven price

### Signal Scoring

Each opportunity receives a score based on:

- Liquidity
- Risk/reward ratio
- Probability estimate
- News sentiment
- Volatility profile
- Event risk
- User risk level

### Paper Trading

The first version of the app should support paper trading only.

Paper trading allows users to test strategies without risking real money.

## Suggested Tech Stack

### Backend

- Python
- Flask or FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Celery or RQ

### Frontend

- React, Next.js, or simple server-rendered templates
- Tailwind CSS or Bootstrap

### Data / Analysis

- pandas
- numpy
- scipy
- yfinance
- QuantLib
- Backtrader or VectorBT
- FinBERT or another finance sentiment model

### Deployment

- Docker
- AWS Elastic Beanstalk or ECS
- AWS RDS PostgreSQL
- AWS ElastiCache Redis
- AWS Secrets Manager
- AWS CloudWatch

## Example Project Structure

```text
options-tracker/
  app/
    api/
    core/
    data_sources/
    models/
    news/
    options/
    risk/
    strategies/
    trading/
    backtesting/
    workers/
  frontend/
  tests/
  scripts/
  docker-compose.yml
  README.md
  .env.example
