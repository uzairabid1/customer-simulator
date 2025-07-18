# Restaurant Review Simulation Research Project

This repository contains two distinct restaurant simulation experiments that study how different review presentation strategies and restaurant positioning affect customer decision-making behavior.

## Project Overview

The project consists of two simulation variants:

1. **Reviews Orientation Study** (`reviews_orientation/`) - Compares different review sorting policies
2. **Vertical Differentiation Study** (`vertical_differentiation/`) - Compares high-end vs. casual restaurant positioning

Both simulations use AI-powered customer agents to make restaurant choices based on reviews, menus, and customer characteristics.

## Simulation Variants

### 1. Reviews Orientation Study

**Research Question**: How do different review sorting policies affect customer decision-making?

**Experimental Design**:
- **Restaurant A**: Shows reviews sorted by highest rating first
- **Restaurant B**: Shows reviews sorted by most recent first
- Both restaurants share the same initial review dataset
- Customers see 5 initial reviews, with additional reviews shown if bias is detected

**Key Features**:
- Bias detection for overly positive or outdated reviews
- Dynamic review supplementation when needed
- Comprehensive logging of customer decisions and review exposure

### 2. Vertical Differentiation Study

**Research Question**: How does restaurant positioning (high-end vs. casual) affect customer preferences?

**Experimental Design**:
- **Restaurant A**: High-end restaurant (Michelin-style rating: 90)
- **Restaurant B**: Casual diner (Michelin-style rating: 60)
- Separate review datasets for each restaurant type
- Both use highest-rating-first review sorting

**Key Features**:
- Differentiated restaurant positioning
- Separate review datasets reflecting different customer expectations
- Same bias detection and review supplementation logic

## Project Structure

```
Latest/
├── reviews_orientation/          # Reviews sorting policy study
│   ├── main.py                  # Main simulation runner
│   ├── config.py                # Configuration settings
│   ├── requirements.txt         # Python dependencies
│   ├── simulation/              # Core simulation logic
│   │   ├── engine.py           # Main simulation engine
│   │   ├── models.py           # Data models (Customer, Restaurant, Review)
│   │   ├── llm.py              # AI interface for customer decisions
│   │   └── logger.py           # Simulation logging
│   └── data/                   # Input/output data
│       ├── inputs/
│       │   └── initial_reviews.json
│       └── outputs/
│           ├── customers.json
│           ├── restaurants.json
│           └── logs/
│               ├── decision_details.json
│               ├── review_exposure.json
│               └── simulation_logs.json
│
└── vertical_differentiation/     # Restaurant positioning study
    ├── main.py                  # Main simulation runner
    ├── config.py                # Configuration settings
    ├── requirements.txt         # Python dependencies
    ├── simulation/              # Core simulation logic
    │   ├── engine.py           # Main simulation engine
    │   ├── models.py           # Data models
    │   ├── llm.py              # AI interface
    │   └── logger.py           # Simulation logging
    └── data/                   # Input/output data
        ├── inputs/
        │   ├── initial_reviews_a.json
        │   └── initial_reviews_b.json
        └── outputs/
            ├── customers.json
            ├── restaurants.json
            └── logs/
                ├── decision_details.json
                ├── review_exposure.json
                └── simulation_logs.json
```

## Features

### AI-Powered Customer Simulation
- **Dynamic Customer Generation**: Each customer has unique characteristics including income, taste preferences, health consciousness, dietary restrictions, and personality
- **Intelligent Decision Making**: Uses OpenAI's GPT models to simulate realistic customer decision-making processes
- **Context-Aware Choices**: Customers consider reviews, menus, ratings, and their personal characteristics

### Review Management
- **Bias Detection**: Automatically identifies overly positive or outdated review sets
- **Dynamic Supplementation**: Provides additional reviews when bias is detected
- **Flexible Sorting**: Supports different review presentation policies (highest rating vs. most recent)

### Comprehensive Logging
- **Customer Arrivals**: Tracks when customers arrive and their characteristics
- **Review Exposure**: Records which reviews each customer sees
- **Decision Details**: Logs complete decision-making process and rationale
- **Simulation Metrics**: Tracks restaurant performance and customer behavior patterns

## Installation

### Prerequisites
- Python 3.8 or higher
- OpenAI API key

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Latest
   ```

2. **Set up environment variables**:
   Create a `.env` file in each simulation directory:
   ```bash
   # reviews_orientation/.env
   OPENAI_API_KEY=your_openai_api_key_here
   
   # vertical_differentiation/.env
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Install dependencies**:
   ```bash
   # For reviews orientation study
   cd reviews_orientation
   pip install -r requirements.txt
   
   # For vertical differentiation study
   cd ../vertical_differentiation
   pip install -r requirements.txt
   ```

## Usage

### Running the Reviews Orientation Study

```bash
cd reviews_orientation
python main.py
```

This will:
- Run a 2-day simulation with 4 customers per day
- Compare "highest rating first" vs. "most recent first" review sorting
- Generate detailed logs in `data/outputs/logs/`

### Running the Vertical Differentiation Study

```bash
cd vertical_differentiation
python main.py
```

This will:
- Run a 2-day simulation with 4 customers per day
- Compare high-end (rating 90) vs. casual (rating 60) restaurant positioning
- Generate detailed logs in `data/outputs/logs/`

## Configuration

Both simulations can be configured by modifying the `config.py` file:

```python
class Config:
    API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    MODEL = "gpt-4.1-mini"           # OpenAI model to use
    DAYS = 2                         # Number of simulation days
    CUSTOMERS_PER_DAY = 4            # Customers per day
    LOG_DIR = "data/outputs/logs"    # Logging directory
```

For the vertical differentiation study, additional configuration includes:
```python
    RESTAURANT_A_RATING = 90  # High-end restaurant rating
    RESTAURANT_B_RATING = 60  # Casual diner rating
```

## Output Analysis

### Generated Files

Each simulation generates several output files:

- **`customers.json`**: Customer profiles and characteristics
- **`restaurants.json`**: Restaurant performance metrics
- **`logs/decision_details.json`**: Detailed customer decision logs
- **`logs/review_exposure.json`**: Which reviews each customer saw
- **`logs/simulation_logs.json`**: Overall simulation metrics

### Key Metrics

The simulations track various metrics including:
- Customer choice distribution between restaurants
- Review exposure patterns
- Decision-making rationale
- Restaurant performance indicators
- Bias detection frequency

## Research Applications

This project is designed for research in:
- **Consumer Behavior**: How review presentation affects choices
- **Digital Marketing**: Impact of review sorting algorithms
- **Restaurant Management**: Effects of positioning and review strategies
- **AI Simulation**: Using LLMs to model human decision-making

## Technical Details

### AI Integration
- Uses OpenAI's GPT models for customer generation and decision-making
- Implements structured prompts for consistent behavior simulation
- Supports different model configurations for experimentation

### Data Models
- **Customer**: Represents individual customers with unique characteristics
- **Restaurant**: Manages menu, reviews, and performance metrics
- **Review**: Stores review data with metadata and sentiment

### Simulation Engine
- Day-by-day simulation with configurable parameters
- Real-time bias detection and review supplementation
- Comprehensive logging and metrics collection