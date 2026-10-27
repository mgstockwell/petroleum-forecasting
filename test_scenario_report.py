import unittest
from datetime import date, timedelta
from unittest.mock import mock_open, patch

import numpy as np
import requests

import scenario_report as report


class HormuzTrafficTests(unittest.TestCase):
    as_of = date(2026, 10, 27)

    def rows(self):
        counts = [(2, 4), (0, 0), (1, 7), (1, 2), (0, 3), (0, 7), (0, 3)]
        return [
            {"attributes": {
                "date": (date(2026, 10, 18) - timedelta(days=i)).isoformat(),
                "n_tanker": tanker, "n_total": total,
            }}
            for i, (tanker, total) in enumerate(counts)
        ]

    def fetch(self, features):
        with patch.object(report.requests, "get") as get:
            get.return_value.json.return_value = {"features": features}
            result = report.fetch_hormuz_traffic(self.as_of)
            get.return_value.raise_for_status.assert_called_once()
            self.assertEqual(get.call_args.kwargs["params"]["resultRecordCount"], 7)
            self.assertEqual(get.call_args.kwargs["timeout"], 20)
            return result

    def test_exact_calendar_week_average_and_staleness(self):
        with patch("builtins.open") as open_file:
            traffic = self.fetch(self.rows())
            open_file.assert_not_called()
        self.assertEqual(traffic["start"], "2026-10-12")
        self.assertEqual(traffic["end"], "2026-10-18")
        self.assertEqual(traffic["observed_days"], 7)
        self.assertEqual(traffic["lag_days"], 9)
        self.assertAlmostEqual(traffic["tanker_average"], 4 / 7)
        self.assertAlmostEqual(traffic["total_average"], 26 / 7)
        self.assertIn("STALE", traffic["warnings"][0])
        text = report.render_hormuz_traffic(traffic)
        for expected in ("0.57/day", "3.71/day", "2026-10-12 to 2026-10-18",
                         "not traffic for the current trailing week", "No spoofing correction",
                         "does not change the manually reviewed"):
            self.assertIn(expected, text)

    def test_missing_day_is_not_replaced_by_older_observation(self):
        rows = self.rows()
        rows[3]["attributes"]["date"] = "2026-10-11"
        traffic = self.fetch(rows)
        self.assertEqual(traffic["observed_days"], 6)
        self.assertIsNone(traffic["tanker_average"])
        self.assertIsNone(traffic["total_average"])
        self.assertIn("2026-10-15", " ".join(traffic["warnings"]))
        self.assertIn("averages unavailable", report.render_hormuz_traffic(traffic))

    def test_reported_zeros_are_valid_observations(self):
        rows = self.rows()
        for row in rows:
            row["attributes"].update(n_tanker=0, n_total=0)
        traffic = self.fetch(rows)
        self.assertEqual(traffic["observed_days"], 7)
        self.assertEqual(traffic["tanker_average"], 0)
        self.assertIn("0.00/day", report.render_hormuz_traffic(traffic))

    def test_freshness_threshold(self):
        for lag, stale in ((7, False), (8, True)):
            with self.subTest(lag=lag), patch.object(report.requests, "get") as get:
                get.return_value.json.return_value = {"features": self.rows()}
                traffic = report.fetch_hormuz_traffic(date(2026, 10, 18) + timedelta(days=lag))
                self.assertEqual(bool(traffic["warnings"]), stale)

    def test_invalid_records_are_rejected(self):
        for field, value in (
            ("date", "2026-10-28"), ("date", "2026-10-17"),
            ("date", "invalid"), ("n_tanker", -1), ("n_tanker", None),
            ("n_tanker", True), ("n_tanker", 1.5), ("n_tanker", 5),
            ("n_total", -1),
        ):
            with self.subTest(field=field, value=value):
                rows = self.rows()
                rows[0]["attributes"][field] = value
                with self.assertRaises(ValueError):
                    self.fetch(rows)

    def test_api_errors_and_empty_data_are_not_successful(self):
        for payload in ({"error": {"message": "Query failed"}}, {"features": []}, {}):
            with self.subTest(payload=payload), patch.object(report.requests, "get") as get:
                get.return_value.json.return_value = payload
                with self.assertRaises(ValueError):
                    report.fetch_hormuz_traffic(self.as_of)

    def test_network_failure_is_not_silently_ignored(self):
        with patch.object(report.requests, "get", side_effect=requests.Timeout("PortWatch timeout")):
            with self.assertRaises(requests.Timeout):
                report.fetch_hormuz_traffic(self.as_of)

    def test_traffic_failure_stops_before_simulation_or_report_writes(self):
        with patch.object(report, "ensure_simulator_built"), \
                patch.object(report, "load_base_params", return_value=({}, "{}")), \
                patch.object(report, "fetch_aaa_prices", return_value={}), \
                patch.object(report, "fetch_hormuz_traffic", side_effect=ValueError("API error")), \
                patch.object(report, "run_scenario") as simulate, \
                patch("builtins.open") as open_file:
            with self.assertRaisesRegex(ValueError, "API error"):
                report.main()
            simulate.assert_not_called()
            open_file.assert_not_called()

    def test_report_contains_monitor_and_preserves_manual_severity(self):
        traffic = self.fetch(self.rows())
        scenarios = [
            {"id": sid, "label": sid, "summary": "Test scenario", "supply_shock_pct": 0}
            for sid in ("base", "stress")
        ]
        bands = {
            sid: {key: np.full(180, 4.0) for key in ("p10", "p25", "p50", "p75", "p90")}
            for sid in ("base", "stress")
        }
        rows = report.build_summary_rows(scenarios, bands, bands)
        severity = {"severity": 0.4, "as_of": "2026-09-30", "source": "Manual review"}
        with patch("builtins.open", mock_open()) as output, \
                patch.object(report, "load_disruption_severity", return_value=severity):
            report.render_report(
                scenarios, rows, "2026-10-27", {},
                {"Regular": 4.0, "Diesel": 6.0}, traffic,
            )
        text = output.return_value.write.call_args.args[0]
        self.assertIn(report.render_hormuz_traffic(traffic), text)
        self.assertIn("40% of the way", text)
        self.assertEqual(severity["severity"], 0.4)
        output.assert_called_once_with("oil_market_outlook.md", "w", encoding="utf-8")


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
