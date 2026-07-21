import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy import stats
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "processed_data" / "master.csv"

# ----Load master dataset----
df = pd.read_csv(DATA_PATH)
print(f"Loaded {len(df)} rows")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print(f"Tickers: {df['ticker'].nunique()}")
print(f"net_sentiment mean: {df['net_sentiment'].mean():.4f}")
print()

# ----Define return variables to test----
return_vars = {
    "abnormal_return": "Abnormal Return (overnight gap minus XLK)",
    "overnight_gap":   "Overnight Gap (raw)",
    "next_day_return": "Next Day Return (full day)",
}

def run_ols(x: pd.Series, y: pd.Series, label: str):
    """Run OLS regression of y on x and print results."""
    X = sm.add_constant(x)
    model = sm.OLS(y, X).fit()

    print(f"  Coefficient:  {model.params['net_sentiment']:.6f}")
    print(f"  P-value:      {model.pvalues['net_sentiment']:.4f}", end=" ")
    if model.pvalues['net_sentiment'] < 0.05:
        print("*** SIGNIFICANT")
    elif model.pvalues['net_sentiment'] < 0.10:
        print("*   MARGINAL")
    else:
        print("    not significant")
    print(f"  R-squared:    {model.rsquared:.6f}")
    print(f"  Observations: {int(model.nobs)}")
    return model

def run_ttest(x: pd.Series, y: pd.Series):
    """Split into high/low sentiment groups and run t-test."""
    median = x.median()
    high = y[x >  median]
    low  = y[x <= median]

    t_stat, p_value = stats.ttest_ind(high, low)

    print(f"  High sentiment mean return: {high.mean():+.6f}  (n={len(high)})")
    print(f"  Low  sentiment mean return: {low.mean():+.6f}  (n={len(low)})")
    print(f"  Difference:                 {high.mean() - low.mean():+.6f}")
    print(f"  T-statistic:                {t_stat:.4f}")
    print(f"  P-value:                    {p_value:.4f}", end=" ")
    if p_value < 0.05:
        print("*** SIGNIFICANT")
    elif p_value < 0.10:
        print("*   MARGINAL")
    else:
        print("    not significant")

# ----Drop rows with any nulls in key columns----
cols_needed = ["net_sentiment"] + list(return_vars.keys())
df_clean = df.dropna(subset=cols_needed).copy()
print(f"Rows after dropping nulls: {len(df_clean)}")
print()

# ----Run tests for each return variable----
results = {}
for var, description in return_vars.items():
    print("=" * 60)
    print(f"DEPENDENT VARIABLE: {description}")
    print("=" * 60)

    x = df_clean["net_sentiment"]
    y = df_clean[var]

    print("\n--- OLS Regression ---")
    model = run_ols(x, y, var)
    results[var] = model

    print("\n--- T-Test (high vs low sentiment) ---")
    run_ttest(x, y)
    print()

# ----Summary table----
print("=" * 60)
print("SUMMARY TABLE")
print("=" * 60)
print(f"{'Variable':<25} {'Coefficient':>12} {'P-value':>10} {'R-squared':>10} {'Significant':>12}")
print("-" * 60)
for var, model in results.items():
    coef  = model.params['net_sentiment']
    pval  = model.pvalues['net_sentiment']
    rsq   = model.rsquared
    sig   = "YES ***" if pval < 0.05 else ("MARGINAL *" if pval < 0.10 else "no")
    print(f"{var:<25} {coef:>12.6f} {pval:>10.4f} {rsq:>10.6f} {sig:>12}")

print()
print("Note: P-value < 0.05 = statistically significant at 95% confidence level")
print("Note: R-squared measures proportion of return variance explained by sentiment")