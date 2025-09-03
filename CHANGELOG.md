# Changelog

## 9/3/2025 - 9th September 2025

### 🎯 Major Features Added

#### Simulation Metadata Tracking
- **Added comprehensive metadata saving** for both `reviews_orientation` and `vertical_differentiation` projects
- Metadata now includes:
  - Simulation run timestamp
  - Configuration parameters (days, customers per day, model used)
  - Restaurant setup details (ratings, policies, menus)
  - Final simulation results (ratings, review counts, revenue)
- Metadata is saved as `simulation_metadata.json` in each test output folder

#### Review Policy Configuration (Vertical Differentiation)
- **Added configurable review policies** to vertical differentiation project
- Users can now set different review policies for Restaurant A and Restaurant B:
  - `highest_rating`: Shows highest-rated reviews first (mimics reviews_orientation Restaurant A behavior)
  - `latest`: Shows most recent reviews first (mimics reviews_orientation Restaurant B behavior)
- Configuration is set directly in config.py file
- Review policies are captured in simulation metadata

#### Menu Configuration System
- **Centralized menu configuration** in config files for both projects
- **Reviews Orientation**: Single shared menu in `Config.RESTAURANT_MENU`
- **Vertical Differentiation**: Separate menus for each restaurant:
  - `Config.RESTAURANT_A_MENU`: High-end restaurant (Italian/French fine dining, $80-120 items)
  - `Config.RESTAURANT_B_MENU`: Restaurant B (Asian fusion, $80-120 items)
- Menus are now easily customizable without modifying model code

### 📝 Detailed Changes

#### Reviews Orientation Project

**`reviews_orientation/config.py`**
- Added `RESTAURANT_MENU` configuration with 22 menu items and prices
- Centralized menu definition for easy customization

**`reviews_orientation/simulation/engine.py`**
- Added `_save_metadata()` method to capture simulation details
- Enhanced `_save_results()` to include metadata saving
- Metadata includes:
  - Simulation type: "reviews_orientation"
  - Configuration parameters
  - Restaurant setup with review policies
  - Final simulation results

**`reviews_orientation/simulation/models.py`**
- Updated `Restaurant.__init__()` to use menu from config
- Removed hardcoded menu definition

#### Vertical Differentiation Project

**`vertical_differentiation/config.py`**
- Added review policy configuration:
  - `RESTAURANT_A_REVIEW_POLICY` (default: "highest_rating")
  - `RESTAURANT_B_REVIEW_POLICY` (default: "highest_rating")
- Added separate menu configurations:
  - `RESTAURANT_A_MENU`: High-end items ($80-120)
  - `RESTAURANT_B_MENU`: Asian fusion items ($80-120)

**`vertical_differentiation/simulation/models.py`**
- Added `review_policy` attribute to Restaurant class
- Updated `get_sorted_reviews()` to respect review policy setting
- Updated `Restaurant.__init__()` to use menus from config
- Removed hardcoded menu definitions

**`vertical_differentiation/simulation/engine.py`**
- Updated `_get_combined_reviews()` to use restaurant review policies
- Added `_save_metadata()` method with vertical differentiation specific details
- Enhanced metadata to include:
  - Quality ratings for both restaurants
  - Review policies for both restaurants
  - Menu and pricing information
- Enhanced `_save_results()` to include metadata saving

**`vertical_differentiation/main.py`**
- Updated `main()` to display current review policy settings from config
- Removed interactive policy configuration (policies are now set directly in config.py)

### 🎨 Metadata Structure

#### Reviews Orientation Metadata
```json
{
  "simulation_info": {
    "simulation_type": "reviews_orientation",
    "timestamp": "2024-XX-XXTXX:XX:XX",
    "output_folder": "folder_name"
  },
  "configuration": {
    "days": 2,
    "customers_per_day": 4,
    "model": "gpt-4.1-mini"
  },
  "restaurant_setup": {
    "restaurant_a": {
      "review_policy": "highest_rating",
      "menu": {...},
      "initial_reviews_count": X,
      "initial_avg_rating": X.X
    },
    "restaurant_b": {
      "review_policy": "latest",
      "menu": {...},
      "initial_reviews_count": X,
      "initial_avg_rating": X.X
    }
  },
  "simulation_results": {
    "total_customers": X,
    "final_ratings": {...},
    "total_revenue": {...}
  }
}
```

#### Vertical Differentiation Metadata
```json
{
  "simulation_info": {
    "simulation_type": "vertical_differentiation",
    "timestamp": "2024-XX-XXTXX:XX:XX",
    "output_folder": "folder_name"
  },
  "configuration": {
    "days": 3,
    "customers_per_day": 6,
    "restaurant_a_rating": 90,
    "restaurant_b_rating": 45,
    "restaurant_a_review_policy": "highest_rating",
    "restaurant_b_review_policy": "highest_rating"
  },
  "restaurant_setup": {
    "restaurant_a": {
      "type": "High-end restaurant",
      "quality_rating": 90,
      "review_policy": "highest_rating",
      "average_price": XX.XX
    },
    "restaurant_b": {
      "type": "Basic diner", 
      "quality_rating": 45,
      "review_policy": "highest_rating",
      "average_price": XX.XX
    }
  }
}
```

### 🔧 Configuration Examples

#### Customizing Review Policies
```python
# In vertical_differentiation/config.py
RESTAURANT_A_REVIEW_POLICY = "highest_rating"  # Show best reviews first
RESTAURANT_B_REVIEW_POLICY = "latest"          # Show recent reviews first
```

#### Customizing Menus
```python
# In reviews_orientation/config.py
RESTAURANT_MENU = {
    "Custom Item 1": 15,
    "Custom Item 2": 20,
    # ... add your items
}

# In vertical_differentiation/config.py
RESTAURANT_A_MENU = {
    "Luxury Item 1": 100,
    "Luxury Item 2": 150,
    # ... high-end items
}

RESTAURANT_B_MENU = {
    "Budget Item 1": 5,
    "Budget Item 2": 8,
    # ... affordable items
}
```

### 📁 File Structure Impact

Each simulation now generates:
```
data/outputs/[test_name]/
├── customers.json
├── restaurants.json
├── simulation_metadata.json  # ← NEW
└── logs/
    ├── decision_details.json
    ├── review_exposure.json
    └── simulation_logs.json
```

### 🔄 Migration Notes

- **No breaking changes** to existing functionality
- **Backward compatible** with existing simulation runs
- **New simulations** will automatically include metadata
- **Configuration-driven** approach allows easy customization without code changes
