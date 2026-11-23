"""A/A test on historical traffic, with and without a pre-period covariate.

No real treatment exists in this data. Splitting visitors at random and testing
for a difference checks the test itself: the false positive rate should match the
nominal level, and the covariate adjustment should shrink the standard error.
"""
import numpy as np
from scipy import stats


def cuped_adjust(y, x):
    """Return y minus the part explained by the pre-period covariate x."""
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    var_x = x.var()
    if var_x == 0:
        return y.copy(), 0.0
    theta = np.cov(x, y, bias=True)[0, 1] / var_x
    return y - theta * (x - x.mean()), theta


def welch(y, in_b):
    """Difference in means (B minus A), its standard error and two-sided p-value."""
    a, b = y[~in_b], y[in_b]
    diff = b.mean() - a.mean()
    se = np.sqrt(a.var(ddof=1) / a.size + b.var(ddof=1) / b.size)
    z = diff / se
    return diff, se, 2 * stats.norm.sf(abs(z))


def srm_pvalue(n_a, n_b):
    """Chi-square test of a 50/50 split."""
    expected = (n_a + n_b) / 2
    chi2 = (n_a - expected) ** 2 / expected + (n_b - expected) ** 2 / expected
    return stats.chi2.sf(chi2, df=1)


def mde(sd, n_per_arm, alpha=0.05, power=0.8):
    """Smallest absolute difference in means detectable with the given power."""
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    return z * sd * np.sqrt(2 / n_per_arm)


def simulate_aa(y, x, n_splits=2000, alpha=0.05, seed=0):
    """Repeat a random 50/50 split and count how often each test rejects."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y, dtype=float)
    y_adj, theta = cuped_adjust(y, x)
    reject_raw = reject_adj = 0
    diffs_raw = np.empty(n_splits)
    diffs_adj = np.empty(n_splits)
    for i in range(n_splits):
        in_b = rng.random(y.size) < 0.5
        d, _, p = welch(y, in_b)
        diffs_raw[i] = d
        reject_raw += p < alpha
        d, _, p = welch(y_adj, in_b)
        diffs_adj[i] = d
        reject_adj += p < alpha
    return {
        "n_splits": n_splits,
        "theta": theta,
        "correlation": float(np.corrcoef(x, y)[0, 1]) if np.std(x) > 0 else 0.0,
        "false_positive_raw": reject_raw / n_splits,
        "false_positive_adjusted": reject_adj / n_splits,
        "sd_diff_raw": diffs_raw.std(ddof=1),
        "sd_diff_adjusted": diffs_adj.std(ddof=1),
        "variance_reduction": 1 - y_adj.var() / y.var(),
    }
