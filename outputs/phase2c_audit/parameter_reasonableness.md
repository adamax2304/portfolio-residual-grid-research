# Parameter reasonableness diagnostics

These are one-at-a-time mechanical diagnostics around the original settings, not a Cartesian optimization and not a selection exercise. No favorable variant is promoted. Sign instability is labelled fragility.

```text
                   run             dimension  original_expectancy_usd  positive_variant_share campaign_range                            mechanical_diagnosis
natural_long_grid:CSCO           grid_levels                 7.138210                    1.00          15-15        consistent sign across diagnostic values
natural_long_grid:CSCO         grid_step_atr                 7.138210                    0.80          15-15 sign-sensitive; requires independent validation
natural_long_grid:CSCO        max_grid_depth                 7.138210                    1.00          15-15        consistent sign across diagnostic values
natural_long_grid:CSCO          stop_variant                 7.138210                    0.75          15-16 sign-sensitive; requires independent validation
natural_long_grid:CSCO               tp_mode                 7.138210                    1.00          16-21        consistent sign across diagnostic values
 residual_grid:JPM/XLF           beta_window                29.351400                    1.00          15-19        consistent sign across diagnostic values
 residual_grid:JPM/XLF           hedge_ratio                29.351400                    1.00          19-19        consistent sign across diagnostic values
 residual_grid:JPM/XLF               z_entry                29.351400                    1.00           6-24        consistent sign across diagnostic values
 residual_grid:JPM/XLF                z_exit                29.351400                    1.00          19-19        consistent sign across diagnostic values
 residual_grid:JPM/XLF                z_kill                29.351400                    1.00          19-20        consistent sign across diagnostic values
  stock_pair_grid:MA/V correlation_threshold               -75.958542                    0.00          10-14        consistent sign across diagnostic values
  stock_pair_grid:MA/V    stationarity_proxy               -75.958542                    0.00          14-14        consistent sign across diagnostic values
  stock_pair_grid:MA/V               z_entry               -75.958542                    0.25           8-22 sign-sensitive; requires independent validation
  stock_pair_grid:MA/V                z_exit               -75.958542                    0.00          14-14        consistent sign across diagnostic values
  stock_pair_grid:MA/V                z_kill               -75.958542                    0.00          14-14        consistent sign across diagnostic values
```

## All diagnostic runs

```text
                   run   family             dimension             value  diagnostic_only  oos_return  profit_factor  expectancy_usd  max_drawdown  campaigns  stopped_campaigns  cost_drag_usd
natural_long_grid:CSCO  natural              original          original             True    0.001071       1.067651        7.138210     -0.013268         15                 15     108.893228
natural_long_grid:CSCO  natural           grid_levels                 3             True    0.000573       1.028496        3.817931     -0.016684         15                 15     133.232042
natural_long_grid:CSCO  natural           grid_levels                 5             True    0.000482       1.038227        3.212543     -0.010682         15                 15      91.548853
natural_long_grid:CSCO  natural           grid_levels                 7             True    0.000324       1.036784        2.161415     -0.007482         15                 15      70.936756
natural_long_grid:CSCO  natural           grid_levels                 9             True    0.000220       1.032318        1.463390     -0.005774         15                 15      59.830119
natural_long_grid:CSCO  natural         grid_step_atr               0.4             True    0.000828       1.037734        5.523034     -0.020334         15                 15     142.926756
natural_long_grid:CSCO  natural         grid_step_atr               0.6             True   -0.000281       0.981464       -1.873362     -0.013943         15                 15     103.528376
natural_long_grid:CSCO  natural         grid_step_atr               0.8             True    0.000360       1.026668        2.401476     -0.012313         15                 15      96.845843
natural_long_grid:CSCO  natural         grid_step_atr               1.0             True    0.002285       1.185223       15.231862     -0.011137         15                 15      91.574849
natural_long_grid:CSCO  natural         grid_step_atr               1.2             True    0.001490       1.146620        9.933186     -0.009007         15                 15      83.017960
natural_long_grid:CSCO  natural               tp_mode          0.5_step             True    0.005088       1.368409       24.227442     -0.013741         21                  3     130.376289
natural_long_grid:CSCO  natural               tp_mode          1.0_step             True    0.001201       1.051254        6.004193     -0.018487         20                  6     134.496300
natural_long_grid:CSCO  natural               tp_mode          1.5_step             True    0.001118       1.047064        5.884297     -0.018493         19                  9     120.908261
natural_long_grid:CSCO  natural               tp_mode          midpoint             True    0.003151       1.207801       19.691580     -0.010973         16                 14     102.294615
natural_long_grid:CSCO  natural          stop_variant           current             True    0.001071       1.067651        7.138210     -0.013268         15                 15     108.893228
natural_long_grid:CSCO  natural          stop_variant range_low_0.5_atr             True    0.001228       1.073114        8.187694     -0.014172         15                 15     114.463690
natural_long_grid:CSCO  natural          stop_variant range_low_1.0_atr             True    0.000160       1.011780        1.063383     -0.011273         15                 15      92.630086
natural_long_grid:CSCO  natural          stop_variant   structure_close             True   -0.015274       0.551203      -95.463040     -0.030025         16                 16     156.019683
natural_long_grid:CSCO  natural        max_grid_depth                 2             True    0.001122       1.083875        7.481120     -0.010862         15                 15      96.022201
natural_long_grid:CSCO  natural        max_grid_depth                 3             True    0.000507       1.034249        3.382457     -0.012282         15                 15     103.949497
natural_long_grid:CSCO  natural        max_grid_depth                 4             True    0.001071       1.067651        7.138210     -0.013268         15                 15     108.893228
natural_long_grid:CSCO  natural        max_grid_depth                 5             True    0.001071       1.067651        7.138210     -0.013268         15                 15     108.893228
 residual_grid:JPM/XLF residual              original          original             True    0.005577       1.360842       29.351400     -0.010685         19                 19     683.557187
 residual_grid:JPM/XLF residual               z_entry               1.2             True    0.003244       1.176332       13.518441     -0.009559         24                 23     918.577097
 residual_grid:JPM/XLF residual               z_entry               1.5             True    0.008045       1.560012       42.343035     -0.010180         19                 19     748.819908
 residual_grid:JPM/XLF residual               z_entry               1.8             True    0.008000       2.009221       79.998306     -0.010581         10                 10     526.975171
 residual_grid:JPM/XLF residual               z_entry               2.0             True    0.017777      16.494271      296.277993     -0.004511          6                  6     392.518963
 residual_grid:JPM/XLF residual                z_exit               0.8             True    0.005577       1.360842       29.351400     -0.010685         19                 19     683.557187
 residual_grid:JPM/XLF residual                z_exit               0.5             True    0.005287       1.342091       27.825953     -0.010686         19                 19     680.503284
 residual_grid:JPM/XLF residual                z_exit               0.2             True    0.005914       1.382671       31.126777     -0.010686         19                 19     679.641636
 residual_grid:JPM/XLF residual                z_exit               0.0             True    0.005914       1.382671       31.126777     -0.010686         19                 19     679.641636
 residual_grid:JPM/XLF residual                z_kill               2.5             True    0.009395       1.308710       46.975177     -0.017355         20                 20    1202.881336
 residual_grid:JPM/XLF residual                z_kill               3.0             True    0.005577       1.360842       29.351400     -0.010685         19                 19     683.557187
 residual_grid:JPM/XLF residual                z_kill               3.5             True    0.002382       1.208712       12.537338     -0.007162         19                 19     493.139148
 residual_grid:JPM/XLF residual           beta_window                60             True    0.005577       1.360842       29.351400     -0.010685         19                 19     683.557187
 residual_grid:JPM/XLF residual           beta_window                90             True    0.014926       3.180456       99.505623     -0.006484         15                 13     538.813138
 residual_grid:JPM/XLF residual           beta_window               120             True    0.013417       1.937009       83.858680     -0.011917         16                 16     678.404577
 residual_grid:JPM/XLF residual           hedge_ratio      beta_neutral             True    0.005577       1.360842       29.351400     -0.010685         19                 19     683.557187
 residual_grid:JPM/XLF residual           hedge_ratio    dollar_neutral             True    0.008491       1.697330       44.688624     -0.008748         19                 19     611.321481
  stock_pair_grid:MA/V     pair              original          original             True   -0.010634       0.426536      -75.958542     -0.013998         14                 12     396.723388
  stock_pair_grid:MA/V     pair               z_entry               1.2             True   -0.007553       0.696329      -34.329712     -0.015008         22                 21     650.149897
  stock_pair_grid:MA/V     pair               z_entry               1.5             True   -0.000844       0.935622       -6.493087     -0.011536         13                 12     452.166626
  stock_pair_grid:MA/V     pair               z_entry               1.8             True   -0.001144       0.917671      -12.707765     -0.013504          9                  8     393.515568
  stock_pair_grid:MA/V     pair               z_entry               2.0             True    0.003822       1.345876       47.776053     -0.010590          8                  7     309.572909
  stock_pair_grid:MA/V     pair                z_exit               0.8             True   -0.010634       0.426536      -75.958542     -0.013998         14                 12     396.723388
  stock_pair_grid:MA/V     pair                z_exit               0.5             True   -0.010634       0.426536      -75.958542     -0.013998         14                 12     396.723388
  stock_pair_grid:MA/V     pair                z_exit               0.2             True   -0.010634       0.426536      -75.958542     -0.013998         14                 12     396.723388
  stock_pair_grid:MA/V     pair                z_exit               0.0             True   -0.009552       0.485189      -68.228061     -0.013998         14                 13     396.922542
  stock_pair_grid:MA/V     pair                z_kill               2.5             True   -0.014472       0.522682     -103.368806     -0.022625         14                 13     718.401917
  stock_pair_grid:MA/V     pair                z_kill               3.0             True   -0.010634       0.426536      -75.958542     -0.013998         14                 12     396.723388
  stock_pair_grid:MA/V     pair                z_kill               3.5             True   -0.007202       0.420092      -51.441803     -0.009389         14                 12     276.667958
  stock_pair_grid:MA/V     pair correlation_threshold              0.65             True   -0.010634       0.426536      -75.958542     -0.013998         14                 12     396.723388
  stock_pair_grid:MA/V     pair correlation_threshold              0.75             True   -0.010634       0.426536      -75.958542     -0.013998         14                 12     396.723388
  stock_pair_grid:MA/V     pair correlation_threshold              0.85             True   -0.009805       0.446665      -98.045180     -0.013766         10                  8     309.189608
  stock_pair_grid:MA/V     pair    stationarity_proxy              True             True   -0.010634       0.426536      -75.958542     -0.013998         14                 12     396.723388
  stock_pair_grid:MA/V     pair    stationarity_proxy             False             True   -0.010634       0.426536      -75.958542     -0.013998         14                 12     396.723388
```
