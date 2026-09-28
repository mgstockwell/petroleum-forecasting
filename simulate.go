package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"math/rand"
	"os"
	"strconv"
	"sync"
	"time"
)

// CurvePoint is a single forward-curve quote, decoded from a [days, value]
// JSON pair.
type CurvePoint struct {
	Days  float64
	Value float64
}

func (c *CurvePoint) UnmarshalJSON(data []byte) error {
	var pair []float64
	if err := json.Unmarshal(data, &pair); err != nil {
		return err
	}
	if len(pair) != 2 {
		return fmt.Errorf("curve point needs [days, value], got %d values", len(pair))
	}
	c.Days, c.Value = pair[0], pair[1]
	return nil
}

type MacroParams struct {
	S0         float64 `json:"s0"`
	SigmaCrude float64 `json:"sigma_crude"`
	JumpLambda float64 `json:"jump_lambda"`
	JumpMu     float64 `json:"jump_mu"`
	JumpSigma  float64 `json:"jump_sigma"`

	CrackGas0           float64 `json:"crack_gas_0"`
	CrackDiesel0        float64 `json:"crack_diesel_0"`
	CrackGasKappa       float64 `json:"crack_gas_kappa"`
	CrackGasTheta       float64 `json:"crack_gas_theta"`
	CrackDieselKappa    float64 `json:"crack_diesel_kappa"`
	CrackDieselTheta    float64 `json:"crack_diesel_theta"`
	SigmaCrackGasBbl    float64 `json:"sigma_crack_gas_bbl"`
	SigmaCrackDieselBbl float64 `json:"sigma_crack_diesel_bbl"`
	CrackGasAmp         float64 `json:"crack_gas_seasonal_amp"`
	CrackGasPhase       float64 `json:"crack_gas_seasonal_phase"`
	CrackDieselAmp      float64 `json:"crack_diesel_seasonal_amp"`
	CrackDieselPhase    float64 `json:"crack_diesel_seasonal_phase"`

	DayOfYear        int          `json:"day_of_year"`
	CurveDriftWeight *float64     `json:"curve_drift_weight"`
	CurveCrude       []CurvePoint `json:"curve_crude"`
	CurveCrackGas    []CurvePoint `json:"curve_crack_gas"`
	CurveCrackDiesel []CurvePoint `json:"curve_crack_diesel"`

	Freight0         float64 `json:"freight_0"`
	ChokepointLambda float64 `json:"chokepoint_lambda"`
	ChokepointJumpMu float64 `json:"chokepoint_jump_mu"`
	ChokepointDecay  float64 `json:"chokepoint_decay"`
	HormuzRate       float64 `json:"hormuz_rate"`
	BabRate          float64 `json:"bab_rate"`
	ShippingCost0    float64 `json:"shipping_cost_0"`

	SprTriggerRatio float64 `json:"spr_trigger_ratio"`
	SprFloorRatio   float64 `json:"spr_floor_ratio"`
	SprMaxDraw      float64 `json:"spr_max_draw_mbpd"`
	SprLevelMbbl    float64 `json:"spr_level_mbbl"`
	SprCapacityMbbl float64 `json:"spr_capacity_mbbl"`

	SaudiProd     float64 `json:"saudi_prod"`
	SaudiCap      float64 `json:"saudi_cap"`
	SaudiFloor    float64 `json:"saudi_floor"`
	SaudiResponse float64 `json:"saudi_response"`
	RussiaProd    float64 `json:"russia_prod"`
	RussiaDecay   float64 `json:"russia_decay"`
	IranProd      float64 `json:"iran_prod"`
	IranCap       float64 `json:"iran_cap"`
	IranFloor     float64 `json:"iran_floor"`
	IranDriftRate float64 `json:"iran_drift_rate"`
	UsProd        float64 `json:"us_prod"`
	UsCap         float64 `json:"us_cap"`
	UsFloor       float64 `json:"us_floor"`
	UsResponse    float64 `json:"us_response"`
	OtherProd     float64 `json:"other_prod"`
	OtherCap      float64 `json:"other_cap"`
	OtherResponse float64 `json:"other_response"`

	Sims int `json:"sims"`
}

const (
	Days        = 180
	DefaultSims = 2000
	Dt          = 1.0 / 365.0
	TaxG        = 0.57
	DistG       = 0.65
	TaxD        = 0.65
	DistD       = 0.85
	// Hormuz baseline; disruption severity scales relative to this.
	ChokeRefRateMbpd = 20.0
	// Price impact of a 1 mb/d supply imbalance, expressed as annualized drift.
	SupplyPriceImpact = 0.1
)

func main() {
	macroFile, err := os.Open("params_macro.json")
	if err != nil {
		legacyFile, legacyErr := os.Open("params.json")
		if legacyErr != nil {
			log.Fatalf("failed to open params_macro.json or params.json: %v / %v", err, legacyErr)
		}
		defer legacyFile.Close()
		var legacy MacroParams
		if err := json.NewDecoder(legacyFile).Decode(&legacy); err != nil {
			log.Fatalf("failed to decode legacy params.json: %v", err)
		}
		legacy.DayOfYear = time.Now().YearDay()
		runSimulation(applyDefaults(legacy))
		return
	}
	defer macroFile.Close()

	var p MacroParams
	if err := json.NewDecoder(macroFile).Decode(&p); err != nil {
		log.Fatalf("failed to decode params_macro.json: %v", err)
	}
	if p.DayOfYear == 0 {
		p.DayOfYear = time.Now().YearDay()
	}

	runSimulation(applyDefaults(p))
}

// applyDefaults fills in parameters that an older or partial params file may
// not carry, so a missing field degrades to sensible behaviour instead of
// silently zeroing out a whole mechanism (a zero crack kappa, for instance,
// would freeze crack spreads for the entire horizon).
func applyDefaults(p MacroParams) MacroParams {
	if p.Sims <= 0 {
		p.Sims = DefaultSims
	}
	// A pointer distinguishes "absent from the params file" from a deliberate
	// 0.0. Defaulting an absent weight to zero would silently discard the
	// curve drift and leave the model with no directional view at all.
	if p.CurveDriftWeight == nil {
		full := 1.0
		p.CurveDriftWeight = &full
	}
	if p.SaudiCap == 0 {
		p.SaudiCap = math.Max(p.SaudiProd*1.3, 12.0)
	}
	if p.UsCap == 0 {
		p.UsCap = math.Max(p.UsProd*1.05, 13.8)
	}
	if p.OtherCap == 0 {
		p.OtherCap = math.Max(p.OtherProd*1.03, 69.0)
	}
	if p.IranCap == 0 {
		p.IranCap = math.Max(p.IranProd, 3.4)
	}
	if p.SaudiFloor == 0 {
		p.SaudiFloor = 0.78 * p.SaudiProd
	}
	if p.UsFloor == 0 {
		p.UsFloor = 0.83 * p.UsProd
	}
	if p.IranFloor == 0 {
		p.IranFloor = 0.76 * p.IranProd
	}
	if p.SaudiResponse == 0 {
		p.SaudiResponse = 0.05
	}
	if p.UsResponse == 0 {
		p.UsResponse = 0.06
	}
	if p.OtherResponse == 0 {
		p.OtherResponse = 0.02
	}
	if p.SprTriggerRatio == 0 {
		p.SprTriggerRatio = 1.25
	}
	if p.SprFloorRatio == 0 {
		p.SprFloorRatio = 0.75
	}
	if p.ChokepointDecay == 0 {
		p.ChokepointDecay = 12.0
	}
	if p.CrackGasKappa == 0 {
		p.CrackGasKappa = 2.5
	}
	if p.CrackDieselKappa == 0 {
		p.CrackDieselKappa = 1.5
	}
	if p.CrackGasTheta == 0 {
		p.CrackGasTheta = p.CrackGas0
	}
	if p.CrackDieselTheta == 0 {
		p.CrackDieselTheta = p.CrackDiesel0
	}
	if p.SigmaCrackGasBbl == 0 {
		p.SigmaCrackGasBbl = 25.0
	}
	if p.SigmaCrackDieselBbl == 0 {
		p.SigmaCrackDieselBbl = 34.0
	}
	return p
}

// interpCurve linearly interpolates a forward curve at t days, holding the
// endpoints flat outside the quoted range. Flat extrapolation matters at the
// short end: the front contract is typically a few weeks out, and inventing a
// steeper near-term slope by extrapolating would be a fabricated forecast.
func interpCurve(curve []CurvePoint, t float64) float64 {
	if len(curve) == 0 {
		return math.NaN()
	}
	if t <= curve[0].Days {
		return curve[0].Value
	}
	last := len(curve) - 1
	if t >= curve[last].Days {
		return curve[last].Value
	}
	for i := 0; i < last; i++ {
		a, b := curve[i], curve[i+1]
		if t <= b.Days {
			span := b.Days - a.Days
			if span <= 0 {
				return b.Value
			}
			return a.Value + (b.Value-a.Value)*(t-a.Days)/span
		}
	}
	return curve[last].Value
}

// buildAnchors produces the deterministic path the market implies for crude
// and the two crack spreads over the horizon.
//
// Crude is anchored multiplicatively (the curve's *shape* is applied to spot)
// and the cracks additively, because a spread's level is a difference rather
// than a scale and can sit near zero. Both are pinned to today's observed
// value at t=0, so the anchor starts exactly where the market is.
//
// curve_drift_weight scales the anchor path itself rather than just the drift
// derived from it, so the whole model stays self-consistent when the curve is
// discounted: producers and the SPR measure deviation against the same
// discounted path the price is drifting along. At weight 0 the anchor is flat
// and the curve has no influence anywhere.
//
// If no curve is available the model falls back to mean reversion toward the
// long-run crack level plus its fitted seasonal cycle, and to a flat crude
// anchor - i.e. no directional view on crude at all, which is the honest
// answer when there is no forward data to read one from.
func buildAnchors(p MacroParams) (crude, crackGas, crackDiesel []float64) {
	crude = make([]float64, Days+1)
	crackGas = make([]float64, Days)
	crackDiesel = make([]float64, Days)
	weight := *p.CurveDriftWeight

	useCrude := len(p.CurveCrude) >= 2
	crudeBase := 0.0
	if useCrude {
		crudeBase = interpCurve(p.CurveCrude, 0)
	}
	for t := 0; t <= Days; t++ {
		crude[t] = p.S0
		if useCrude && crudeBase > 0 {
			crude[t] *= math.Pow(interpCurve(p.CurveCrude, float64(t))/crudeBase, weight)
		}
	}

	omega := 2.0 * math.Pi / 365.25
	seasonal := func(amp, phase float64, t int) float64 {
		return amp * math.Sin(omega*float64((p.DayOfYear+t)%365)+phase)
	}

	fill := func(dest []float64, curve []CurvePoint, spot, theta, amp, phase float64) {
		if len(curve) >= 2 {
			base := interpCurve(curve, 0)
			for t := 0; t < Days; t++ {
				dest[t] = spot + weight*(interpCurve(curve, float64(t))-base)
			}
			return
		}
		for t := 0; t < Days; t++ {
			dest[t] = theta + seasonal(amp, phase, t)
		}
	}
	fill(crackGas, p.CurveCrackGas, p.CrackGas0, p.CrackGasTheta, p.CrackGasAmp, p.CrackGasPhase)
	fill(crackDiesel, p.CurveCrackDiesel, p.CrackDiesel0, p.CrackDieselTheta, p.CrackDieselAmp, p.CrackDieselPhase)
	return crude, crackGas, crackDiesel
}

func runSimulation(p MacroParams) {
	sims := p.Sims
	crudeAnchor, crackGasAnchor, crackDieselAnchor := buildAnchors(p)

	// Annualized drift implied by the crude anchor path, one value per step.
	// The curve weight is already baked into the anchor, so it is not reapplied.
	curveMu := make([]float64, Days)
	for t := 0; t < Days; t++ {
		if crudeAnchor[t] > 0 && crudeAnchor[t+1] > 0 {
			curveMu[t] = math.Log(crudeAnchor[t+1]/crudeAnchor[t]) / Dt
		}
	}

	// Merton compensator. Jumps have a non-zero mean effect on the price, so
	// without subtracting E[e^J - 1] the jump component would quietly shift
	// the whole forecast off the curve it is supposed to be anchored to.
	jumpDrift := 0.0
	if p.JumpLambda > 0 {
		jumpDrift = p.JumpLambda * (math.Exp(p.JumpMu+0.5*p.JumpSigma*p.JumpSigma) - 1.0)
	}

	baselineSupply := p.SaudiProd + p.RussiaProd + p.UsProd + p.IranProd + p.OtherProd
	otherFloor := 0.9 * p.OtherProd
	sqrtDt := math.Sqrt(Dt)
	seed := time.Now().UnixNano()

	var wg sync.WaitGroup
	gasResults := make([][]string, sims)
	dieselResults := make([][]string, sims)

	fmt.Printf("Running %d multi-factor macro paths...\n", sims)
	if len(p.CurveCrude) >= 2 {
		fmt.Printf("Curve-anchored: crude $%.2f -> $%.2f, diesel crack $%.1f -> $%.1f, gas crack $%.1f -> $%.1f over %d days\n",
			crudeAnchor[0], crudeAnchor[Days], crackDieselAnchor[0], crackDieselAnchor[Days-1],
			crackGasAnchor[0], crackGasAnchor[Days-1], Days)
	} else {
		fmt.Println("No forward curve in params: falling back to mean-reversion drift.")
	}

	for i := 0; i < sims; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			// Per-path generator: avoids lock contention on the global source
			// and keeps a run reproducible for a given seed.
			// Multiplying the index decorrelates neighbouring path seeds.
			rng := rand.New(rand.NewSource(seed + int64(idx)*0x27bb2ee687b0b0fd))

			st := p.S0
			// Crack spreads are carried as a deterministic anchor plus a
			// mean-reverting deviation, so the simulated spread tracks the
			// anchor exactly in expectation instead of lagging behind it.
			// Seeding the deviation with today's gap to the anchor makes both
			// modes fall out of the same expression: under a forward curve the
			// gap is zero, and in fallback mode it decays from today's level
			// toward the long-run one at the fitted speed.
			devGas := p.CrackGas0 - crackGasAnchor[0]
			devDiesel := p.CrackDiesel0 - crackDieselAnchor[0]
			cGas := p.CrackGas0
			cDies := p.CrackDiesel0
			freight := p.Freight0
			shippingCost := p.ShippingCost0
			saudiQ := p.SaudiProd
			russiaQ := p.RussiaProd
			usQ := p.UsProd
			iranQ := p.IranProd
			otherQ := p.OtherProd
			sprLevel := p.SprLevelMbbl
			disruption := 0.0

			gasPath := make([]string, Days)
			dieselPath := make([]string, Days)

			for t := 0; t < Days; t++ {
				// Producers respond to how far price has strayed from the
				// market-implied path, not to its absolute level. The forward
				// curve already prices in the supply response the market
				// expects; charging for it again here is what previously
				// manufactured a downward drift out of a high spot price.
				deviation := st - crudeAnchor[t]

				russiaQ -= russiaQ * p.RussiaDecay * Dt
				saudiQ = clamp(saudiQ+p.SaudiResponse*deviation*Dt, p.SaudiFloor, p.SaudiCap)
				usQ = clamp(usQ+p.UsResponse*deviation*Dt, p.UsFloor, p.UsCap)
				otherQ = clamp(otherQ+p.OtherResponse*deviation*Dt, otherFloor, p.OtherCap)
				// Sanctions: drift to cap only if a scenario sets a nonzero
				// rate; the base case holds flat.
				iranQ = clamp(iranQ+p.IranDriftRate*(p.IranCap-iranQ)*Dt, p.IranFloor, p.IranCap)

				sprFlow := 0.0
				if st > p.SprTriggerRatio*crudeAnchor[t] && sprLevel > 0 {
					sprFlow = math.Min(p.SprMaxDraw, sprLevel) // can't release more than remains
				} else if st < p.SprFloorRatio*crudeAnchor[t] {
					sprFlow = -0.1
				}
				sprLevel -= sprFlow
				if sprLevel < 0 {
					sprLevel = 0
				}
				if p.SprCapacityMbbl > 0 && sprLevel > p.SprCapacityMbbl {
					sprLevel = p.SprCapacityMbbl
				}

				// Chokepoint disruptions persist and decay rather than lasting
				// a single step, so an event actually restricts supply for a
				// meaningful stretch of the horizon.
				disruption -= p.ChokepointDecay * disruption * Dt
				if rng.Float64() < (p.ChokepointLambda * Dt) {
					severity := 1.0
					if totalChoke := p.HormuzRate + p.BabRate; totalChoke > 0 {
						chokeRate := p.BabRate
						if rng.Float64() < p.HormuzRate/totalChoke {
							chokeRate = p.HormuzRate
						}
						severity = chokeRate / ChokeRefRateMbpd
					}
					baseJump := math.Abs(rng.NormFloat64()*2.0 + p.ChokepointJumpMu)
					freight += baseJump * severity
					shippingCost += baseJump * severity * 0.5
					disruption += 0.05 * severity * ChokeRefRateMbpd
				}
				freight += 5.0 * (p.Freight0 - freight) * Dt
				shippingCost += 8.0 * (p.ShippingCost0 - shippingCost) * Dt

				// Crack spreads: the deviation from the anchor reverts at the
				// fitted speed, with volatility in $/bbl scaled by sqrt(dt).
				devGas += -p.CrackGasKappa*devGas*Dt + p.SigmaCrackGasBbl*sqrtDt*rng.NormFloat64()
				devDiesel += -p.CrackDieselKappa*devDiesel*Dt + p.SigmaCrackDieselBbl*sqrtDt*rng.NormFloat64()
				cGas = crackGasAnchor[t] + devGas
				cDies = crackDieselAnchor[t] + devDiesel

				supplyImbalance := (saudiQ + russiaQ + usQ + iranQ + otherQ + sprFlow - disruption) -
					baselineSupply
				mu := curveMu[t] - SupplyPriceImpact*supplyImbalance - jumpDrift
				st += mu*st*Dt + p.SigmaCrude*st*sqrtDt*rng.NormFloat64()
				if p.JumpLambda > 0 && rng.Float64() < p.JumpLambda*Dt {
					st *= math.Exp(p.JumpMu + p.JumpSigma*rng.NormFloat64())
				}
				st = math.Max(st, 0.01)

				perBarrel := (st + freight + shippingCost) / 42.0
				gasPath[t] = strconv.FormatFloat(perBarrel+(cGas/42.0)+TaxG+DistG, 'f', 2, 64)
				dieselPath[t] = strconv.FormatFloat(perBarrel+(cDies/42.0)+TaxD+DistD, 'f', 2, 64)
			}

			gasResults[idx] = gasPath
			dieselResults[idx] = dieselPath
		}(i)
	}
	wg.Wait()

	for _, out := range []struct {
		name string
		data [][]string
	}{
		{"results_macro_gas.csv", gasResults},
		{"results_macro_diesel.csv", dieselResults},
		{"results_gas.csv", gasResults},
		{"results_diesel.csv", dieselResults},
	} {
		if err := writeCSV(out.name, out.data); err != nil {
			log.Fatalf("failed to write %s: %v", out.name, err)
		}
	}
	if err := writeAnchorPath(p, crudeAnchor, crackGasAnchor, crackDieselAnchor); err != nil {
		log.Fatalf("failed to write anchor_path.csv: %v", err)
	}
	fmt.Println("Simulation complete. Output saved to macro and legacy CSVs.")
}

// writeAnchorPath publishes the deterministic anchor the simulation is built
// around, in both crude/crack and retail terms, so the charts can plot what
// the forecast is anchored to without re-deriving the interpolation.
// Freight and shipping sit at their reversion targets here; the anchor is the
// expected path, not a simulated one.
func writeAnchorPath(p MacroParams, crude, crackGas, crackDiesel []float64) error {
	rows := [][]string{{"day", "crude", "crack_gas", "crack_diesel", "gas_retail", "diesel_retail"}}
	for t := 0; t < Days; t++ {
		perBarrel := (crude[t] + p.Freight0 + p.ShippingCost0) / 42.0
		rows = append(rows, []string{
			strconv.Itoa(t + 1),
			strconv.FormatFloat(crude[t], 'f', 4, 64),
			strconv.FormatFloat(crackGas[t], 'f', 4, 64),
			strconv.FormatFloat(crackDiesel[t], 'f', 4, 64),
			strconv.FormatFloat(perBarrel+crackGas[t]/42.0+TaxG+DistG, 'f', 4, 64),
			strconv.FormatFloat(perBarrel+crackDiesel[t]/42.0+TaxD+DistD, 'f', 4, 64),
		})
	}
	return writeCSV("anchor_path.csv", rows)
}

func clamp(value, low, high float64) float64 {
	if high < low {
		return low
	}
	return math.Min(math.Max(value, low), high)
}

func writeCSV(filename string, data [][]string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()
	writer := csv.NewWriter(file)
	defer writer.Flush()
	writer.WriteAll(data)
	return writer.Error()
}
