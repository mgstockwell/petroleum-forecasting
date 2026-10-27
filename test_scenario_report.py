import unittest
from unittest.mock import patch

import numpy as np

import scenario_report as report


class ScenarioResponseTests(unittest.TestCase):
    def test_supply_scenarios_use_half_life(self):
        base = {
            "saudi_prod": 9.0, "saudi_cap": 12.0,
            "russia_prod": 9.0, "iran_prod": 3.3, "iran_cap": 3.4,
            "us_prod": 13.2, "us_cap": 13.8, "other_prod": 67.0,
            "hormuz_rate": 20.0, "sigma_crude": 0.4,
        }
        scenarios = report.build_scenarios(base)
        self.assertEqual(len(scenarios), 7)
        self.assertEqual(scenarios[0]["overrides"], {})
        for scenario in scenarios:
            overrides = scenario["overrides"]
            if scenario["supply_shock_pct"]:
                self.assertEqual(overrides["shock_half_life_days"], 7)
                self.assertNotIn("shock_ramp_days", overrides)
                self.assertNotIn("s0", overrides)
                self.assertEqual(overrides["shock_pct"], scenario["supply_shock_pct"])

    def test_rebuilds_stale_simulator(self):
        for exists, source_time, binary_time, should_build in (
            (False, 2, 1, True),
            (True, 2, 1, True),
            (True, 1, 2, False),
        ):
            with self.subTest(exists=exists, source_time=source_time):
                with patch.object(report.os.path, "exists", return_value=exists), \
                        patch.object(report.os.path, "getmtime",
                                     side_effect=lambda path: source_time if path == "simulate.go" else binary_time), \
                        patch.object(report.subprocess, "run") as run:
                    report.ensure_simulator_built()
                    self.assertEqual(run.called, should_build)
                    if should_build:
                        run.assert_called_once_with(
                            ["go", "build", "-o", report.SIM_BINARY, "simulate.go"],
                            check=True,
                        )

    def test_chart_uses_explicit_day_zero(self):
        bands = {key: np.array([4.5, 4.6]) for key in ("p10", "p25", "p50", "p75", "p90")}
        with patch.object(report.plt.Figure, "savefig"), \
                patch.object(report.plt.Axes, "plot") as plot:
            report.plot_scenario_paths(
                [{"id": "base", "label": "Base Case"}],
                {"base": bands}, "Gasoline", "unused.png", 4.25,
            )
        days, values = plot.call_args.args
        np.testing.assert_array_equal(days, [0, 1, 2])
        np.testing.assert_array_equal(values, [4.25, 4.5, 4.6])


if __name__ == "__main__":
    unittest.main()
