import numpy as np

from shopmetrics import experiment


def test_cuped_keeps_mean_and_cuts_variance():
    rng = np.random.default_rng(0)
    x = rng.poisson(3, 20000).astype(float)
    y = 0.8 * x + rng.normal(0, 1, 20000)
    y_adj, theta = experiment.cuped_adjust(y, x)
    assert abs(y_adj.mean() - y.mean()) < 1e-9
    assert abs(theta - 0.8) < 0.02
    rho2 = np.corrcoef(x, y)[0, 1] ** 2
    assert abs((1 - y_adj.var() / y.var()) - rho2) < 1e-9


def test_cuped_with_constant_covariate_changes_nothing():
    y = np.array([1.0, 2.0, 3.0])
    y_adj, theta = experiment.cuped_adjust(y, np.zeros(3))
    assert theta == 0.0 and np.allclose(y_adj, y)


def test_aa_false_positive_rate_is_nominal():
    rng = np.random.default_rng(1)
    x = rng.poisson(2, 5000).astype(float)
    y = x + rng.exponential(2, 5000)
    sim = experiment.simulate_aa(y, x, n_splits=2000, seed=2)
    for key in ("false_positive_raw", "false_positive_adjusted"):
        assert 0.035 < sim[key] < 0.065
    assert sim["sd_diff_adjusted"] < sim["sd_diff_raw"]


def test_welch_finds_a_real_difference():
    rng = np.random.default_rng(3)
    in_b = rng.random(20000) < 0.5
    y = rng.normal(0, 1, 20000) + 0.1 * in_b
    diff, se, p = experiment.welch(y, in_b)
    assert abs(diff - 0.1) < 4 * se and p < 0.001


def test_srm_and_mde():
    assert experiment.srm_pvalue(5000, 5000) == 1.0
    assert experiment.srm_pvalue(5000, 5600) < 0.001
    assert abs(experiment.mde(1.0, 1570) - 0.1) < 0.001
