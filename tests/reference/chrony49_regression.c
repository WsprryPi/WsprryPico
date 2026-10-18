// SPDX-License-Identifier: MIT
// Original public-API probe, linked only to the private external reference.
#include "regress.h"

#include <stdio.h>

int main(void) {
    int n, m, minimum;
    while (scanf("%d %d %d", &n, &m, &minimum) == 3) {
        double x[256], y[256], w[256], intercept, slope, variance, sd, slope_sd;
        int start, runs, freedom;
        if (n < 3 || m < 0 || n + m > 256)
            return 2;
        for (int i = 0; i < n + m; ++i)
            if (scanf("%lf %lf %lf", &x[i], &y[i], &w[i]) != 3)
                return 3;
        if (!RGR_FindBestRegression(x + m, y + m, w + m, n, m, minimum, &intercept, &slope,
                                    &variance, &sd, &slope_sd, &start, &runs, &freedom))
            return 4;
        printf("%.15g %.15g %.15g %.15g %.15g %d %d %d\n", intercept, slope, variance, sd, slope_sd,
               start, runs, freedom);
    }
    return 0;
}
