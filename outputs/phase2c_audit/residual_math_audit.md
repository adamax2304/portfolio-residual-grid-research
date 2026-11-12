# Residual / z-score / beta audit

## Verdict: PASS

The implementation is `ln(A) - alpha - beta*ln(B)`. Beta/alpha use exactly the prior `60` aligned bars. Residual mean/std are rolling and shifted one bar. Current prices are evaluated only after those parameters exist, and orders execute no earlier than next bar. Long residual is long A/short beta-notional B; short residual is the inverse; leg P&L is independent before aggregation.

## Audited entries

```text
                  run  timestamp  stock_price_adjusted  hedge_price_adjusted    alpha     beta  correlation  residual  rolling_residual_mean  rolling_residual_std   z_score  entry_threshold  exit_threshold  kill_threshold      direction  stock_notional  hedge_notional_expected
residual_grid:JPM/XLF 2021-04-21            132.076370             32.077030 1.517298 0.981920     0.890795 -0.039353              -0.004737              0.017929 -1.930754              1.5             0.8             3.0  long residual    10993.615447             10794.846517
residual_grid:JPM/XLF 2021-04-22            129.295181             31.720829 1.594811 0.959072     0.888985 -0.048201              -0.005006              0.018265 -2.364897              1.5             0.8             3.0  long residual    13742.019309             13179.590161
residual_grid:JPM/XLF 2021-04-23            131.769272             32.314518 1.674426 0.935574     0.890628 -0.044977              -0.005285              0.018731 -2.119062              1.5             0.8             3.0  long residual    13742.019309             12856.676776
residual_grid:JPM/XLF 2021-05-17            144.473358             34.661831 3.285129 0.467142     0.885648  0.031648              -0.006788              0.021012  1.829233              1.5             0.8             3.0 short residual     9340.959526              4363.557342
residual_grid:JPM/XLF 2021-09-27            147.344238             35.677345 1.676557 0.919302     0.962396  0.030155              -0.008270              0.017630  2.179461              1.5             0.8             3.0 short residual    11155.619089             10255.382336
 stock_pair_grid:MA/V 2021-05-06            364.107971            222.094879 0.103777 1.079035     0.832517 -0.036464               0.009556              0.019613 -2.346451              1.5             0.8             3.0  long residual    10040.254087             10833.782843
 stock_pair_grid:MA/V 2021-05-27            351.036255            218.129105 2.587606 0.614993     0.803175 -0.038507               0.002589              0.025370 -1.619832              1.5             0.8             3.0  long residual     7734.547204              4756.691004
 stock_pair_grid:MA/V 2021-11-05            339.052612            208.615295 1.565633 0.791750     0.917074  0.032187              -0.002511              0.014019  2.475015              1.5             0.8             3.0 short residual    14070.311674             11140.170164
 stock_pair_grid:MA/V 2021-11-09            335.028198            205.457245 1.808206 0.746751     0.919061  0.029380              -0.001625              0.014514  2.136170              1.5             0.8             3.0 short residual    17587.889592             13133.781680
 stock_pair_grid:MA/V 2021-11-17            349.142883            197.784485 3.512354 0.430727     0.896540  0.065799               0.002456              0.021628  2.928757              1.5             0.8             3.0 short residual     9008.373131              3880.146163
```

## Independent scalar verification (at least five)

```text
                  run  timestamp  engine_beta  manual_beta  beta_difference  engine_alpha  manual_alpha  alpha_difference  engine_residual  manual_residual  residual_difference  prior_only  timestamp_aligned
residual_grid:JPM/XLF 2021-04-21     0.981920     0.981920     1.135092e-12      1.517298      1.517298     -3.863576e-12        -0.039353        -0.039353        -7.327472e-14        True               True
residual_grid:JPM/XLF 2021-04-22     0.959072     0.959072    -1.076805e-12      1.594811      1.594811      3.670841e-12        -0.048201        -0.048201         5.195844e-14        True               True
residual_grid:JPM/XLF 2021-04-23     0.935574     0.935574    -8.171241e-13      1.674426      1.674426      2.787548e-12        -0.044977        -0.044977         5.240253e-14        True               True
residual_grid:JPM/XLF 2021-05-17     0.467142     0.467142     9.048318e-13      3.285129      3.285129     -3.129941e-12         0.031648         0.031648        -7.838175e-14        True               True
residual_grid:JPM/XLF 2021-09-27     0.919302     0.919302    -2.580380e-12      1.676557      1.676557      9.120704e-12         0.030155         0.030155         1.025846e-13        True               True
 stock_pair_grid:MA/V 2021-05-06     1.079035     1.079035    -8.315570e-13      0.103777      0.103777      4.441780e-12        -0.036464        -0.036464         5.062617e-14        True               True
 stock_pair_grid:MA/V 2021-05-27     0.614993     0.614993     4.753975e-13      2.587606      2.587606     -2.549072e-12        -0.038507        -0.038507        -1.110223e-14        True               True
 stock_pair_grid:MA/V 2021-11-05     0.791750     0.791750     1.525891e-12      1.565633      1.565633     -8.215650e-12         0.032187         0.032187         6.661338e-14        True               True
 stock_pair_grid:MA/V 2021-11-09     0.746751     0.746751     9.752199e-13      1.808206      1.808206     -5.247358e-12         0.029380         0.029380         5.417888e-14        True               True
 stock_pair_grid:MA/V 2021-11-17     0.430727     0.430727     1.745049e-12      3.512354      3.512354     -9.377388e-12         0.065799         0.065799         1.509903e-13        True               True
```
