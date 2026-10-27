package main

import (
	"math"
	"testing"
)

func TestShockFraction(t *testing.T) {
	p := MacroParams{ShockHalfLifeDays: 7, ShockRampDays: 30}
	for _, tc := range []struct {
		day, want float64
	}{
		{-1, 0}, {0, 0}, {7, 0.5}, {14, 0.75}, {28, 0.9375},
	} {
		if got := shockFraction(tc.day, p); math.Abs(got-tc.want) > 1e-12 {
			t.Errorf("day %g: got %g, want %g", tc.day, got, tc.want)
		}
	}
	if got := shockFraction(30, p); got < 0.94 || got > 0.96 {
		t.Errorf("day 30 adjustment = %g, want about 95%%", got)
	}
	previousStep := 1.0
	for day := 1; day <= Days; day++ {
		value := shockFraction(float64(day), p)
		step := value - shockFraction(float64(day-1), p)
		if value <= 0 || value > 1 || step <= 0 || step >= previousStep {
			t.Fatalf("day %d: adjustment %g, increment %g, previous increment %g",
				day, value, step, previousStep)
		}
		previousStep = step
	}
}

func TestLegacyShockResponse(t *testing.T) {
	for _, tc := range []struct {
		day, ramp, want float64
	}{
		{0, 0, 0}, {1, 0, 1}, {15, 30, 0.5}, {30, 30, 1}, {60, 30, 1},
	} {
		p := MacroParams{ShockRampDays: tc.ramp}
		if got := shockFraction(tc.day, p); got != tc.want {
			t.Errorf("day %g, ramp %g: got %g, want %g", tc.day, tc.ramp, got, tc.want)
		}
	}
}

func TestShockAnchors(t *testing.T) {
	base := applyDefaults(MacroParams{
		S0: 100, CrackGas0: 20, CrackDiesel0: 30,
		CurveCrude:       []CurvePoint{{0, 100}, {180, 90}},
		CurveCrackGas:    []CurvePoint{{0, 20}, {180, 25}},
		CurveCrackDiesel: []CurvePoint{{0, 30}, {180, 35}},
	})
	baseCrude, baseGas, baseDiesel := buildAnchors(base)
	for _, shock := range []float64{-0.2, 0, 0.6} {
		p := base
		p.ShockPct = shock
		p.ShockHalfLifeDays = 7
		crude, gas, diesel := buildAnchors(p)
		if crude[0] != base.S0 {
			t.Errorf("shock %g changed day 0 to %g", shock, crude[0])
		}
		for day := 0; day <= Days; day++ {
			want := baseCrude[day] * (1 + shock*(1-math.Exp2(-float64(day)/7)))
			if math.Abs(crude[day]-want) > 1e-10 {
				t.Errorf("shock %g day %d: got %g, want %g", shock, day, crude[day], want)
			}
			if day < Days && (gas[day] != baseGas[day] || diesel[day] != baseDiesel[day]) {
				t.Fatalf("shock changed crack anchors at day %d", day)
			}
		}
		if math.Abs(crude[Days]/baseCrude[Days]-(1+shock)) > 1e-7 {
			t.Errorf("shock %g did not persist at day %d", shock, Days)
		}
	}
}
