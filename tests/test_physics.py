"""Physics limits: the circular truth model, the linear fit that inverts it,
and the retained eccentric Kepler machinery (spec section 3)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from aliasbreaker.world import truth_rv
from aliasbreaker.fitting import fit_circular, predict_circular, chi2_constant
from aliasbreaker import kepler

from helpers import angle_diff


class TestTruthRV(unittest.TestCase):
    """truth_rv must be exactly the declared circular-orbit sinusoid."""

    PARAMS = {"P": 7.3, "K": 15.0, "phi": 1.1, "gamma": 2.0}

    def test_matches_closed_form(self):
        t = np.linspace(0.0, 60.0, 601)
        expected = (self.PARAMS["gamma"] + self.PARAMS["K"] * np.cos(
            2.0 * np.pi * t / self.PARAMS["P"] + self.PARAMS["phi"]))
        np.testing.assert_allclose(truth_rv(self.PARAMS, t), expected,
                                   rtol=0.0, atol=1e-12)

    def test_periodic_and_bounded(self):
        t = np.linspace(0.0, 40.0, 401)
        y = truth_rv(self.PARAMS, t)
        y_shift = truth_rv(self.PARAMS, t + self.PARAMS["P"])
        np.testing.assert_allclose(y, y_shift, atol=1e-9)
        self.assertLessEqual(float(y.max()),
                             self.PARAMS["gamma"] + self.PARAMS["K"] + 1e-9)
        self.assertGreaterEqual(float(y.min()),
                                self.PARAMS["gamma"] - self.PARAMS["K"] - 1e-9)

    def test_scalar_and_vector_agree(self):
        self.assertAlmostEqual(float(truth_rv(self.PARAMS, 3.25)),
                               float(truth_rv(self.PARAMS, [3.25])[0]),
                               places=12)

    def test_amplitude_and_offset_recovered_from_extremes(self):
        # Dense sampling over many periods: peak-to-peak -> 2K, mean -> gamma.
        # A finite grid never lands exactly on the extremum, so the tolerance
        # here is set by the sampling step, not by the model.
        t = np.linspace(0.0, 730.0, 200001)
        y = truth_rv(self.PARAMS, t)
        self.assertAlmostEqual(0.5 * (y.max() - y.min()), self.PARAMS["K"],
                               places=4)
        self.assertAlmostEqual(float(y.mean()), self.PARAMS["gamma"], places=4)


class TestFitCircular(unittest.TestCase):
    """The linear fit must invert truth_rv exactly on noise-free dense data."""

    def _check_recovery(self, params, t):
        y = truth_rv(params, t)
        fit = fit_circular(t, y, 1.0, params["P"])
        self.assertAlmostEqual(fit["K"], params["K"], places=8)
        self.assertAlmostEqual(fit["gamma"], params["gamma"], places=8)
        # gamma + A cos(w) + B sin(w) == gamma + K cos(w + phi)
        # => A = K cos(phi), B = -K sin(phi) => phi = atan2(-B, A).
        phi_hat = np.arctan2(-fit["B"], fit["A"])
        self.assertLess(angle_diff(phi_hat, params["phi"]), 1e-8)
        self.assertLess(fit["chi2"], 1e-16)
        return fit

    def test_recovers_reference_signal(self):
        t = np.linspace(0.0, 40.0, 400)
        self._check_recovery(
            {"P": 7.3, "K": 15.0, "phi": 1.1, "gamma": 2.0}, t)

    def test_recovers_across_parameter_grid(self):
        t = np.linspace(0.0, 90.0, 900)
        for P in (3.5, 11.0, 19.5):
            for phi in (0.0, 2.0, 4.5, 6.1):
                with self.subTest(P=P, phi=phi):
                    self._check_recovery(
                        {"P": P, "K": 12.5, "phi": phi, "gamma": -4.0}, t)

    def test_predict_circular_reproduces_the_fit(self):
        params = {"P": 9.0, "K": 20.0, "phi": 3.0, "gamma": 1.0}
        t = np.linspace(0.0, 50.0, 500)
        y = truth_rv(params, t)
        fit = fit_circular(t, y, 2.0, params["P"])
        np.testing.assert_allclose(predict_circular(fit, t), y, atol=1e-8)

    def test_chi2_scales_with_sigma(self):
        # Residuals are divided by sigma, so chi2 scales as 1/sigma^2.
        params = {"P": 6.0, "K": 10.0, "phi": 0.4, "gamma": 0.0}
        t = np.linspace(0.0, 30.0, 120)
        y = truth_rv(params, t) + np.cos(37.0 * t)  # deterministic misfit
        c1 = fit_circular(t, y, 1.0, params["P"])["chi2"]
        c2 = fit_circular(t, y, 2.0, params["P"])["chi2"]
        self.assertAlmostEqual(c1 / 4.0, c2, places=9)

    def test_signal_fit_beats_constant_model(self):
        params = {"P": 6.0, "K": 10.0, "phi": 0.4, "gamma": 3.0}
        t = np.linspace(0.0, 30.0, 120)
        y = truth_rv(params, t)
        self.assertLess(fit_circular(t, y, 1.0, params["P"])["chi2"],
                        chi2_constant(y, 1.0))

    def test_chi2_constant_is_zero_for_flat_data(self):
        y = np.full(20, 4.2)
        self.assertAlmostEqual(chi2_constant(y, 1.5), 0.0, places=12)


class TestKepler(unittest.TestCase):
    """Retained eccentric machinery (documented removed experiment) must still
    be numerically correct."""

    def test_kepler_equation_residuals(self):
        M = np.linspace(0.0, 2.0 * np.pi, 2001)
        for e in (0.1, 0.4, 0.7):
            with self.subTest(e=e):
                E = kepler.solve_kepler(M, e)
                resid = np.abs(E - e * np.sin(E) - M)
                self.assertLess(float(resid.max()), 1e-8)

    def test_kepler_equation_residuals_negative_and_wrapped_M(self):
        M = np.linspace(-4.0 * np.pi, 4.0 * np.pi, 1501)
        for e in (0.1, 0.4, 0.7):
            with self.subTest(e=e):
                E = kepler.solve_kepler(M, e)
                resid = np.abs(E - e * np.sin(E) - M)
                self.assertLess(float(resid.max()), 1e-8)

    def test_zero_eccentricity_is_identity(self):
        M = np.linspace(0.0, 2.0 * np.pi, 501)
        np.testing.assert_allclose(kepler.solve_kepler(M, 0.0), M, atol=1e-12)

    def test_true_anomaly_equals_mean_anomaly_at_e_zero(self):
        t = np.linspace(0.0, 30.0, 601)
        P, T0 = 8.0, 1.25
        nu = kepler.true_anomaly(t, P, T0, 0.0)
        M = np.mod(2.0 * np.pi * (t - T0) / P, 2.0 * np.pi)
        # nu comes back on (-pi, pi]; compare as angles.
        for a, b in zip(nu, M):
            self.assertLess(angle_diff(a, b), 1e-9)

    def test_rv_reduces_to_sinusoid_at_e_zero(self):
        t = np.linspace(0.0, 45.0, 901)
        P, T0, K, omega, gamma = 8.0, 1.25, 14.0, 0.7, -3.0
        got = kepler.rv(t, P, T0, 0.0, K, omega, gamma)
        expected = gamma + K * np.cos(2.0 * np.pi * (t - T0) / P + omega)
        np.testing.assert_allclose(got, expected, atol=1e-9)

    def test_rv_params_matches_rv(self):
        params = {"P": 8.0, "T0": 1.25, "e": 0.3, "K": 14.0,
                  "omega": 0.7, "gamma": -3.0}
        t = np.linspace(0.0, 20.0, 101)
        np.testing.assert_allclose(
            kepler.rv_params(params, t),
            kepler.rv(t, params["P"], params["T0"], params["e"], params["K"],
                      params["omega"], params["gamma"]),
            atol=1e-12)

    def test_eccentric_rv_is_periodic(self):
        t = np.linspace(0.0, 20.0, 401)
        P = 8.0
        a = kepler.rv(t, P, 1.25, 0.5, 14.0, 0.7, -3.0)
        b = kepler.rv(t + P, P, 1.25, 0.5, 14.0, 0.7, -3.0)
        np.testing.assert_allclose(a, b, atol=1e-8)


if __name__ == "__main__":
    unittest.main()
