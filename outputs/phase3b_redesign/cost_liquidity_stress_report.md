# Phase 3B cost and liquidity stress

Cost and spread stresses hold observed fills fixed and apply incremental friction to campaign P&L; this isolates economics and does not invent new fills. ADV threshold stresses are full state-machine reruns at $10M, $25M, $50M, $100M, and no gate for H1/H5 logic only. No stress result changes frozen settings.

| stress_type | stress_value | strategy_family | campaign_count | net_pnl | profit_factor | expectancy | rejection_rate |
|---|---|---|---|---|---|---|---|
| ADV_THRESHOLD_USD | 10,000,000.0000 | natural_long_grid | 108.0000 | 8,247.4256 | 1.1746 | 76.3651 | 0.0666 |
| ADV_THRESHOLD_USD | 10,000,000.0000 | stock_pair_grid | 1,622.0000 | -126,373.9333 | 0.3922 | -77.9124 | 0.0373 |
| ADV_THRESHOLD_USD | 25,000,000.0000 | natural_long_grid | 105.0000 | 8,833.7387 | 1.1911 | 84.1308 | 0.3343 |
| ADV_THRESHOLD_USD | 25,000,000.0000 | stock_pair_grid | 1,104.0000 | -82,493.1951 | 0.4299 | -74.7221 | 0.3011 |
| ADV_THRESHOLD_USD | 100,000,000.0000 | natural_long_grid | 42.0000 | -12,605.9235 | 0.5278 | -300.1410 | 0.7116 |
| ADV_THRESHOLD_USD | 100,000,000.0000 | stock_pair_grid | 44.0000 | -1,303.4403 | 0.7501 | -29.6236 | 0.8844 |
| SPREAD | 2.0000 | natural_long_grid | 506.5000 | -463.7997 | 0.9835 | -3.9173 | nan |
| SPREAD | 2.0000 | residual_grid | 2,945.0000 | -320,926.8874 | 0.3220 | -108.9735 | nan |
| SPREAD | 2.0000 | stock_pair_grid | 360.2857 | -35,134.6256 | 0.3611 | -97.5364 | nan |
| TOTAL_COST | 1.0000 | natural_long_grid | 506.5000 | 2,638.4654 | 1.0022 | 0.9268 | nan |
| TOTAL_COST | 1.0000 | residual_grid | 2,945.0000 | -252,760.2438 | 0.4038 | -85.8269 | nan |
| TOTAL_COST | 1.0000 | stock_pair_grid | 360.2857 | -26,491.1169 | 0.4643 | -73.5425 | nan |
| TOTAL_COST | 2.0000 | natural_long_grid | 506.5000 | -10,678.1950 | 0.9221 | -20.3509 | nan |
| TOTAL_COST | 2.0000 | residual_grid | 2,945.0000 | -541,218.3595 | 0.1653 | -183.7753 | nan |
| TOTAL_COST | 2.0000 | stock_pair_grid | 360.2857 | -63,006.3096 | 0.1614 | -174.9118 | nan |
| TOTAL_COST | 3.0000 | natural_long_grid | 506.5000 | -23,994.8553 | 0.8487 | -41.6286 | nan |
| TOTAL_COST | 3.0000 | residual_grid | 2,945.0000 | -829,676.4751 | 0.0798 | -281.7238 | nan |
| TOTAL_COST | 3.0000 | stock_pair_grid | 360.2857 | -99,521.5023 | 0.0650 | -276.2810 | nan |
