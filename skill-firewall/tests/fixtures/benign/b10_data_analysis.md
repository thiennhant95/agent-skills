---
name: data-analysis
description: Pandas-based data analysis. Use when the user needs statistics, charts or dataframe work.
---

# Data Analysis

Load and explore a dataset:

```python
import pandas as pd

df = pd.read_csv("sales.csv")
df["revenue"] = df["price"] * df["qty"]
summary = df.groupby("region")["revenue"].sum()

# filter with query (safe string expressions)
north = df.query("region == 'North' and revenue > 100")
mean_price = df.eval("price * 1.1").mean()
```

Example: `df.describe()` gives count, mean, std, min, max per column.
